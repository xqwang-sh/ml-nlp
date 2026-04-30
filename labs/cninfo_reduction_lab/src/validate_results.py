from __future__ import annotations

import argparse
import json

from common import read_jsonl, read_yaml, write_csv, write_jsonl
from schemas import ShareholderReductionExtract


def validate_results(config_path: str) -> tuple[list[dict], list[dict]]:
    config = read_yaml(config_path)
    rows = read_jsonl(config["paths"]["extract_results"])
    valid = []
    errors = []
    for row in rows:
        try:
            model = ShareholderReductionExtract.model_validate(row)
            valid.append(model.model_dump(mode="json"))
        except Exception as exc:
            errors.append({"doc_id": row.get("doc_id"), "error": str(exc), "raw": row})

    flat_rows = []
    for row in valid:
        evidence = row.pop("evidence")
        row["evidence_text"] = evidence.get("text")
        row["page_no"] = evidence.get("page_no")
        flat_rows.append(row)

    write_csv(config["paths"]["validated_results"], flat_rows)
    write_jsonl(config["paths"]["validation_errors"], errors)
    return flat_rows, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate extraction results with Pydantic.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    args = parser.parse_args()
    valid, errors = validate_results(args.config)
    print(f"Valid records={len(valid)}; errors={len(errors)}")


if __name__ == "__main__":
    main()

