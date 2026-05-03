from __future__ import annotations

import argparse
import re
import time
from datetime import datetime
from html import unescape
from pathlib import Path
from urllib.parse import urljoin

import requests

from common import read_yaml, write_csv


FIELDS = [
    "doc_id",
    "stock_code",
    "stock_name",
    "market",
    "announcement_title",
    "announcement_type",
    "publish_date",
    "url",
    "pdf_url",
    "local_pdf_path",
    "source",
    "crawl_time",
    "download_status",
    "error_message",
]


def clean_title(title: str) -> str:
    title = re.sub(r"</?em>", "", title)
    title = re.sub(r"<[^>]+>", "", title)
    return unescape(title).strip()


def format_date(ms: int | None) -> str:
    if not ms:
        return ""
    return datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d")


def page_column_to_market(page_column: str | None) -> str:
    if not page_column:
        return ""
    if page_column.startswith("SZ"):
        return "sz"
    if page_column.startswith("SH"):
        return "sh"
    if page_column.startswith("BJ"):
        return "bj"
    return page_column.lower()


def query_cninfo(config: dict) -> list[dict]:
    session = requests.Session()
    headers = {
        "User-Agent": config["request"]["user_agent"],
        "Referer": "https://www.cninfo.com.cn/new/fulltextSearch",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    session.get("https://www.cninfo.com.cn/new/index", headers=headers, timeout=config["request"]["timeout_seconds"])

    endpoint = config["endpoint"]
    keyword = " ".join(config["keywords"])
    page_size = int(config["query"]["page_size"])
    max_records = int(config["query"]["max_records"])
    sleep_seconds = float(config["request"]["sleep_seconds"])
    timeout = int(config["request"]["timeout_seconds"])
    se_date = f"{config['date_range']['start']}~{config['date_range']['end']}"
    pdf_base_url = config["pdf_base_url"]
    pdf_dir = Path(config["output"]["pdf_dir"])

    rows: list[dict] = []
    page_num = 1
    while len(rows) < max_records:
        payload = {
            "pageNum": page_num,
            "pageSize": page_size,
            "column": config["query"].get("column", "szse"),
            "tabName": config["query"].get("tab_name", "fulltext"),
            "plate": "",
            "stock": "",
            "searchkey": keyword,
            "secid": "",
            "category": "",
            "trade": "",
            "seDate": se_date,
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        response = session.post(endpoint, headers=headers, data=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        announcements = data.get("announcements") or []
        if not announcements:
            break

        for item in announcements:
            if len(rows) >= max_records:
                break
            adjunct_url = item.get("adjunctUrl") or ""
            if not adjunct_url.lower().endswith(".pdf"):
                continue
            doc_id = item.get("announcementId") or f"{item.get('secCode', 'unknown')}_{len(rows) + 1}"
            title = clean_title(item.get("announcementTitle") or "")
            pdf_url = urljoin(pdf_base_url, adjunct_url)
            rows.append(
                {
                    "doc_id": doc_id,
                    "stock_code": item.get("secCode") or "",
                    "stock_name": item.get("secName") or item.get("tileSecName") or "",
                    "market": page_column_to_market(item.get("pageColumn")),
                    "announcement_title": title,
                    "announcement_type": "股东减持",
                    "publish_date": format_date(item.get("announcementTime")),
                    "url": f"https://www.cninfo.com.cn/new/disclosure/detail?stockCode={item.get('secCode') or ''}&announcementId={doc_id}",
                    "pdf_url": pdf_url,
                    "local_pdf_path": str(pdf_dir / f"{doc_id}.pdf"),
                    "source": "cninfo",
                    "crawl_time": datetime.now().isoformat(timespec="seconds"),
                    "download_status": "pending",
                    "error_message": "",
                }
            )
        if not data.get("hasMore"):
            break
        page_num += 1
        time.sleep(sleep_seconds)
    return rows


def crawl(config_path: str) -> list[dict]:
    config = read_yaml(config_path)
    rows = query_cninfo(config)
    if not rows:
        raise RuntimeError("CNINFO query returned 0 PDF announcements.")
    write_csv(config["output"]["metadata"], rows, FIELDS)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Query real CNINFO announcements and write metadata.csv.")
    parser.add_argument("--config", default="configs/crawl.yaml")
    args = parser.parse_args()
    rows = crawl(args.config)
    print(f"Wrote {len(rows)} rows to metadata.")


if __name__ == "__main__":
    main()
