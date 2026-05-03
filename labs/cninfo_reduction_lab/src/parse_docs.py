from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import time
import zipfile
from pathlib import Path

import requests
from dotenv import load_dotenv

from common import read_csv, read_yaml, write_jsonl


def local_pdf_to_markdown(pdf_path: Path) -> tuple[str, list[dict]]:
    pages = extract_pdf_pages(pdf_path)
    markdown = "\n\n".join(f"<!-- page: {page['page_no']} -->\n\n{page['text']}" for page in pages)
    return markdown, pages


def extract_pdf_pages(pdf_path: Path) -> list[dict]:
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            check=True,
            capture_output=True,
            text=True,
        )
        raw_pages = result.stdout.split("\f")
        return [
            {"page_no": index + 1, "text": page.strip()}
            for index, page in enumerate(raw_pages)
            if page.strip()
        ]
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "PDF text extraction needs either the pdftotext command or pypdf. "
            "Install pypdf with: python3 -m pip install pypdf"
        ) from exc

    reader = PdfReader(str(pdf_path))
    pages = []
    for index, page in enumerate(reader.pages):
        pages.append({"page_no": index + 1, "text": page.extract_text() or ""})
    return [page for page in pages if page["text"].strip()]


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
    response.raise_for_status()
    data = response.json()
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
        response.raise_for_status()
        data = response.json()
        task = data.get("data", data)
        state = str(task.get("state") or task.get("status") or "").lower()
        if state in {"done", "success", "finished"}:
            return task
        if state in {"failed", "error"}:
            raise RuntimeError(json.dumps(task, ensure_ascii=False))
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


def parse_with_mineru(row: dict, config: dict, api_key: str) -> tuple[str, dict]:
    task_id = submit_mineru_url(row, config, api_key)
    task = poll_mineru_task(task_id, config, api_key)
    zip_url = task.get("full_zip_url") or task.get("zip_url") or task.get("result_url")
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
    provider = config.get("parse", {}).get("provider", "mineru")
    allow_local_fallback = bool(config.get("parse", {}).get("allow_local_fallback", False))
    api_key_env = config.get("parse", {}).get("mineru", {}).get("api_key_env", "MINERU_API_KEY")
    mineru_api_key = os.getenv(api_key_env, "")

    for row in read_csv(metadata_path):
        pdf_path = Path(row["local_pdf_path"])
        if row.get("download_status") not in {"success", "skipped"}:
            continue
        markdown_path = markdown_dir / f"{row['doc_id']}.md"
        parser = provider
        mineru_meta = None
        if provider == "mineru" and mineru_api_key and mineru_api_key != "your_key_here":
            markdown, mineru_meta = parse_with_mineru(row, config, mineru_api_key)
            pages = markdown_to_pages(markdown)
        elif provider == "mineru" and allow_local_fallback:
            markdown, pages = local_pdf_to_markdown(pdf_path)
            parser = "local_fallback"
        elif provider == "local":
            markdown, pages = local_pdf_to_markdown(pdf_path)
            parser = "local"
        else:
            raise RuntimeError(
                f"MinerU parsing needs a real {api_key_env}. "
                "Set parse.allow_local_fallback=true only for classroom smoke tests."
            )
        markdown_path.write_text(markdown, encoding="utf-8")
        record = {
            "doc_id": row["doc_id"],
            "stock_code": row["stock_code"],
            "stock_name": row["stock_name"],
            "title": row["announcement_title"],
            "pdf_path": str(pdf_path),
            "markdown_path": str(markdown_path),
            "parser": parser,
            "pages": pages,
        }
        if mineru_meta:
            record["mineru_task_id"] = mineru_meta["task_id"]
        records.append(record)

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
