from __future__ import annotations

import argparse
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from pypdf import PdfReader

from common import read_csv, read_yaml, write_csv


ALLOWED_HOSTS = {"static.cninfo.com.cn", "www.cninfo.com.cn"}


def is_allowed_pdf_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.hostname in ALLOWED_HOSTS and parsed.path.lower().endswith(".pdf")


def count_pdf_pages(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


def download_pdfs(config_path: str) -> tuple[list[dict], list[dict]]:
    config = read_yaml(config_path)
    metadata_path = config["output"]["metadata"]
    failed_path = config["output"]["failed_downloads"]
    sleep_seconds = float(config["request"]["sleep_seconds"])
    timeout = int(config["request"]["timeout_seconds"])
    target_records = int(config["query"].get("target_records", config["query"]["max_records"]))
    max_pages = int(config.get("pdf", {}).get("max_pages_for_mineru", 200))
    headers = {
        "User-Agent": config["request"]["user_agent"],
        "Referer": "https://www.cninfo.com.cn/new/fulltextSearch",
    }
    rows = read_csv(metadata_path)
    if not rows:
        raise RuntimeError(f"No metadata rows found: {metadata_path}")
    failures: list[dict] = []
    accepted: list[dict] = []
    session = requests.Session()

    for row in rows:
        if len(accepted) >= target_records:
            break
        url = row["pdf_url"]
        dst = Path(row["local_pdf_path"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.stat().st_size > 0:
            row["download_status"] = "skipped"
            row["error_message"] = ""
        else:
            if not is_allowed_pdf_url(url):
                row["download_status"] = "failed"
                row["error_message"] = f"blocked non-CNINFO PDF URL: {url}"
                write_csv(metadata_path, rows)
                write_csv(failed_path, [row.copy()])
                raise RuntimeError(row["error_message"])
            response = session.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and not response.content.startswith(b"%PDF"):
                row["download_status"] = "failed"
                row["error_message"] = f"response does not look like PDF: {content_type}"
                write_csv(metadata_path, rows)
                write_csv(failed_path, [row.copy()])
                raise RuntimeError(row["error_message"])
            dst.write_bytes(response.content)
            row["download_status"] = "success"
            row["error_message"] = ""
        page_count = count_pdf_pages(dst)
        row["pdf_pages"] = str(page_count)
        if page_count > max_pages:
            row["download_status"] = "rejected_page_limit"
            row["error_message"] = f"PDF has {page_count} pages; MinerU limit is {max_pages}"
            failures.append(row.copy())
        else:
            accepted.append(row)
        time.sleep(sleep_seconds)

    if len(accepted) != target_records:
        write_csv(metadata_path, accepted)
        write_csv(failed_path, failures)
        raise RuntimeError(f"Only {len(accepted)} MinerU-eligible annual reports found; expected {target_records}.")

    write_csv(metadata_path, accepted)
    write_csv(failed_path, failures)
    return accepted, failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Download real CNINFO PDFs listed in metadata.csv.")
    parser.add_argument("--config", default="configs/crawl.yaml")
    args = parser.parse_args()
    rows, failures = download_pdfs(args.config)
    print(f"Processed {len(rows)} rows; failures={len(failures)}.")


if __name__ == "__main__":
    main()
