from __future__ import annotations

import argparse
from pathlib import Path

from common import read_csv, read_yaml


def check_dataset(config_path: str) -> str:
    config = read_yaml(config_path)
    metadata_path = config["paths"]["metadata"]
    report_path = Path(config["paths"]["dataset_report"])
    rows = read_csv(metadata_path)
    if not rows:
        raise RuntimeError(f"No metadata rows found: {metadata_path}")
    seen = set()
    duplicates = []
    missing_pdf = []
    keyword_miss = []
    keywords = ["2024年年度报告"]

    for row in rows:
        doc_id = row["doc_id"]
        if doc_id in seen:
            duplicates.append(row)
        seen.add(doc_id)
        pdf_path = Path(row["local_pdf_path"])
        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            missing_pdf.append(row)
        if not any(keyword in row["announcement_title"] for keyword in keywords):
            keyword_miss.append(row)
        if row.get("market") != "sh" or row.get("announcement_type") != "年度报告":
            keyword_miss.append(row)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Dataset Check Report

## Summary

- Total records: {len(rows)}
- Missing PDFs: {len(missing_pdf)}
- Duplicate doc_id: {len(duplicates)}
- Keyword mismatch: {len(keyword_miss)}

## Sample

| doc_id | stock | title | download_status | pdf_size |
|---|---|---|---|---:|
"""
    for row in rows:
        pdf_path = Path(row["local_pdf_path"])
        size = pdf_path.stat().st_size if pdf_path.exists() else 0
        text += f"| {row['doc_id']} | {row['stock_code']} {row['stock_name']} | {row['announcement_title']} | {row.get('download_status', '')} | {size} |\n"

    report_path.write_text(text, encoding="utf-8")
    if missing_pdf or duplicates or keyword_miss:
        raise RuntimeError(
            "Dataset check failed: "
            f"missing_pdf={len(missing_pdf)}, duplicates={len(duplicates)}, keyword_miss={len(keyword_miss)}. "
            f"See {report_path}"
        )
    return str(report_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Check real CNINFO metadata and downloaded PDFs.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    args = parser.parse_args()
    report = check_dataset(args.config)
    print(f"Wrote {report}")


if __name__ == "__main__":
    main()
