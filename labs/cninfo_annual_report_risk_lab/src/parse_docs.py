from __future__ import annotations

import argparse
import io
import json
import os
import time
import zipfile
from pathlib import Path

import requests
from dotenv import load_dotenv

from common import read_csv, read_yaml, write_jsonl


def require_success_payload(response: requests.Response, context: str) -> dict:
    response.raise_for_status()
    data = response.json()
    if data.get("code") != 0:
        raise RuntimeError(f"{context} failed: {json.dumps(data, ensure_ascii=False)}")
    return data


def submit_mineru_url(row: dict, config: dict, api_key: str) -> str:
    mineru = config["parse"]["mineru"]
    api_base_url = mineru["api_base_url"].rstrip("/")
    response = requests.post(
        f"{api_base_url}/api/v4/extract/task",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "url": row["pdf_url"],
            "model_version": mineru.get("model_version", "vlm"),
            "language": mineru.get("language", "ch"),
            "is_ocr": True,
        },
        timeout=int(mineru.get("timeout_seconds", 600)),
    )
    data = require_success_payload(response, f"MinerU submit doc_id={row['doc_id']}")
    task_id = data.get("data", {}).get("task_id") or data.get("task_id")
    if not task_id:
        raise RuntimeError(f"MinerU did not return task_id: {data}")
    return task_id


def poll_mineru_task(task_id: str, config: dict, api_key: str) -> dict:
    mineru = config["parse"]["mineru"]
    api_base_url = mineru["api_base_url"].rstrip("/")
    timeout_seconds = int(mineru.get("timeout_seconds", 600))
    poll_interval = float(mineru.get("poll_interval_seconds", 3))
    deadline = time.time() + timeout_seconds

    while time.time() < deadline:
        response = requests.get(
            f"{api_base_url}/api/v4/extract/task/{task_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
        )
        data = require_success_payload(response, f"MinerU poll task_id={task_id}")
        task = data.get("data", data)
        state = str(task.get("state") or task.get("status") or "").lower()
        if state in {"done", "success", "finished"}:
            return task
        if state in {"failed", "error"}:
            raise RuntimeError(json.dumps(task, ensure_ascii=False))
        if state not in {"pending", "running", "converting"}:
            raise RuntimeError(f"MinerU returned unknown state for task_id={task_id}: {state}")
        time.sleep(poll_interval)
    raise TimeoutError(f"MinerU task timed out: {task_id}")


def read_markdown_from_zip(zip_url: str) -> str:
    response = requests.get(zip_url, timeout=120)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        markdown_names = [name for name in archive.namelist() if name.lower().endswith(".md")]
        if not markdown_names:
            raise RuntimeError("MinerU result zip does not contain a markdown file.")
        preferred = sorted(markdown_names, key=lambda name: (Path(name).name != "full.md", name))[0]
        return archive.read(preferred).decode("utf-8", errors="replace")


def collect_mineru_result(task_id: str, config: dict, api_key: str) -> tuple[str, dict]:
    task = poll_mineru_task(task_id, config, api_key)
    extract_result = task.get("extract_result") or {}
    zip_url = task.get("full_zip_url") or extract_result.get("full_zip_url")
    if not zip_url:
        raise RuntimeError(f"MinerU task has no result zip URL: {task}")
    markdown = read_markdown_from_zip(zip_url)
    return markdown, {"task_id": task_id, "task": task}


def markdown_to_pages(markdown: str) -> list[dict]:
    return [{"page_no": 1, "text": markdown.strip()}] if markdown.strip() else []


def parse_docs(config_path: str) -> list[dict]:
    load_dotenv()
    config = read_yaml(config_path)
    metadata_path = config["paths"]["metadata"]
    parsed_dir = Path(config["paths"]["parsed_dir"])
    markdown_dir = Path(config["paths"].get("markdown_dir", parsed_dir / "markdown"))
    parsed_dir.mkdir(parents=True, exist_ok=True)
    markdown_dir.mkdir(parents=True, exist_ok=True)
    records = []
    provider = config.get("parse", {}).get("provider")
    if provider != "mineru":
        raise RuntimeError(f"Unsupported parse provider: {provider}. This lab requires MinerU API.")
    api_key_env = config.get("parse", {}).get("mineru", {}).get("api_key_env", "MINERU_API_KEY")
    mineru_api_key = os.getenv(api_key_env, "")
    if not mineru_api_key or mineru_api_key == "your_key_here":
        raise RuntimeError(f"Missing real {api_key_env}. MinerU parsing stops here.")

    candidates = []
    for row in read_csv(metadata_path):
        pdf_path = Path(row["local_pdf_path"])
        if row.get("download_status") not in {"success", "skipped"}:
            raise RuntimeError(f"Cannot parse doc_id={row['doc_id']} because download_status={row.get('download_status')}")
        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            raise FileNotFoundError(f"Missing PDF for doc_id={row['doc_id']}: {pdf_path}")
        candidates.append((row, pdf_path))

    if not candidates:
        raise RuntimeError("No downloaded PDFs were ready for MinerU parsing.")

    submitted = []
    for row, pdf_path in candidates:
        task_id = submit_mineru_url(row, config, mineru_api_key)
        submitted.append((row, pdf_path, task_id))

    for row, pdf_path, task_id in submitted:
        markdown_path = markdown_dir / f"{row['doc_id']}.md"
        markdown, mineru_meta = collect_mineru_result(task_id, config, mineru_api_key)
        pages = markdown_to_pages(markdown)
        if not pages:
            raise RuntimeError(f"MinerU returned empty markdown for doc_id={row['doc_id']}")
        markdown_path.write_text(markdown, encoding="utf-8")
        record = {
            "doc_id": row["doc_id"],
            "stock_code": row["stock_code"],
            "stock_name": row["stock_name"],
            "title": row["announcement_title"],
            "pdf_path": str(pdf_path),
            "markdown_path": str(markdown_path),
            "parser": "mineru",
            "pages": pages,
            "mineru_task_id": mineru_meta["task_id"],
        }
        records.append(record)

    if not records:
        raise RuntimeError("No documents were parsed.")
    output_path = parsed_dir / "parsed_docs.jsonl"
    write_jsonl(output_path, records)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse downloaded CNINFO PDF text.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    args = parser.parse_args()
    records = parse_docs(args.config)
    print(f"Parsed {len(records)} docs.")


if __name__ == "__main__":
    main()
