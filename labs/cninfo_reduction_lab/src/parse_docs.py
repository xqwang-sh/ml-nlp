from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from common import read_csv, read_yaml, write_jsonl


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


def parse_docs(config_path: str) -> list[dict]:
    config = read_yaml(config_path)
    metadata_path = config["paths"]["metadata"]
    parsed_dir = Path(config["paths"]["parsed_dir"])
    parsed_dir.mkdir(parents=True, exist_ok=True)
    records = []

    for row in read_csv(metadata_path):
        pdf_path = Path(row["local_pdf_path"])
        if row.get("download_status") not in {"success", "skipped"}:
            continue
        pages = extract_pdf_pages(pdf_path)
        record = {
            "doc_id": row["doc_id"],
            "stock_code": row["stock_code"],
            "stock_name": row["stock_name"],
            "title": row["announcement_title"],
            "pdf_path": str(pdf_path),
            "pages": pages,
        }
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
