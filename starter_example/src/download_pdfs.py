"""Offline starter download step.

No network request is made here. The runnable lab contains the real CNINFO PDF
download example; this file only marks local sample rows as ready for parsing.
"""

from __future__ import annotations

import argparse

try:
    from .common import apply_limit, read_csv, read_yaml, write_csv
except ImportError:
    from common import apply_limit, read_csv, read_yaml, write_csv


def prepare_sample_pdfs(config_path: str, limit: int | None = None) -> tuple[list[dict], list[dict]]:
    config = read_yaml(config_path)
    metadata_path = config["paths"]["metadata"]
    all_rows = read_csv(metadata_path)
    rows = apply_limit(all_rows, limit)
    failures: list[dict] = []
    for row in rows:
        if row.get("pdf_url", "").startswith("sample://"):
            row["download_status"] = "sample"
            row["error_message"] = ""
        else:
            row["download_status"] = "skipped"
            row["error_message"] = "starter_example does not perform live downloads"
            failures.append(row.copy())
    write_csv(metadata_path, all_rows)
    write_csv(config["paths"]["failed_downloads"], failures)
    return rows, failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare offline starter PDF sample state.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    rows, failures = prepare_sample_pdfs(args.config, args.limit)
    print(f"Prepared sample rows={len(rows)}; failures={len(failures)}.")


if __name__ == "__main__":
    main()
