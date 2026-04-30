from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .common import read_csv, read_jsonl, read_yaml
except ImportError:
    from common import read_csv, read_jsonl, read_yaml


REQUIRED_COLUMNS = [
    "doc_id",
    "stock_code",
    "stock_name",
    "announcement_title",
    "publish_date",
    "url",
    "pdf_url",
    "local_pdf_path",
    "download_status",
    "source",
]


def check_dataset(config_path: str) -> str:
    config = read_yaml(config_path)
    paths = config["paths"]
    rows = read_csv(paths["metadata"])
    parsed_docs = read_jsonl(paths["parsed_sample"])
    parsed_ids = {doc["doc_id"] for doc in parsed_docs}
    seen = set()
    duplicates = []
    missing_columns = [column for column in REQUIRED_COLUMNS if rows and column not in rows[0]]
    missing_parsed = []
    keyword_miss = []

    for row in rows:
        doc_id = row["doc_id"]
        if doc_id in seen:
            duplicates.append(doc_id)
        seen.add(doc_id)
        if doc_id not in parsed_ids:
            missing_parsed.append(doc_id)
        if "减持" not in row.get("announcement_title", ""):
            keyword_miss.append(doc_id)

    report_path = Path(paths["dataset_report"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Dataset Check Report",
        "",
        "## Summary",
        "",
        f"- Total metadata records: {len(rows)}",
        f"- Missing required columns: {len(missing_columns)}",
        f"- Duplicate doc_id: {len(duplicates)}",
        f"- Missing parsed sample: {len(missing_parsed)}",
        f"- Keyword mismatch: {len(keyword_miss)}",
        "",
        "## Notes",
        "",
        "- This starter uses offline sample parsed text, not real PDFs.",
        "- In the formal project, `source`, `url`, `pdf_url`, and local PDF files must point back to CNINFO.",
        "",
        "## Sample Rows",
        "",
        "| doc_id | stock | title | status | parsed_sample |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {doc_id} | {stock_code} {stock_name} | {title} | {status} | {parsed} |".format(
                doc_id=row["doc_id"],
                stock_code=row.get("stock_code", ""),
                stock_name=row.get("stock_name", ""),
                title=row.get("announcement_title", ""),
                status=row.get("download_status", ""),
                parsed="yes" if row["doc_id"] in parsed_ids else "no",
            )
        )
    if missing_columns:
        lines.extend(["", "## Missing Columns", "", ", ".join(missing_columns)])
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(report_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check starter metadata and parsed samples.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    args = parser.parse_args()
    report = check_dataset(args.config)
    print(f"Wrote {report}")


if __name__ == "__main__":
    main()

