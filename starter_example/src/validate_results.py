from __future__ import annotations

import argparse

try:
    from .common import read_jsonl, read_yaml, write_csv, write_jsonl
    from .schemas import AnnualReportRiskExtract
except ImportError:
    from common import read_jsonl, read_yaml, write_csv, write_jsonl
    from schemas import AnnualReportRiskExtract


def validate_results(config_path: str) -> tuple[list[dict], list[dict]]:
    config = read_yaml(config_path)
    paths = config["paths"]
    valid = []
    errors = []
    for row in read_jsonl(paths["extract_results"]):
        try:
            model = AnnualReportRiskExtract.model_validate(row)
            valid.append(model.model_dump(mode="json"))
        except Exception as exc:
            errors.append({"doc_id": row.get("doc_id"), "error": str(exc), "raw": row})

    flat_rows = []
    for row in valid:
        categories = row.pop("risk_categories")
        row["risk_category_names"] = ";".join(item["category"] for item in categories)
        row["risk_evidence_text"] = " || ".join(item["evidence"]["text"] for item in categories)
        row["page_no"] = ";".join(str(item["evidence"].get("page_no") or "") for item in categories)
        flat_rows.append(row)

    write_csv(paths["validated_csv"], flat_rows)
    write_jsonl(paths["validation_errors"], errors)
    return flat_rows, errors


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate extracted JSONL results with Pydantic.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    args = parser.parse_args()
    valid, errors = validate_results(args.config)
    print(f"Valid records={len(valid)}; errors={len(errors)}.")


if __name__ == "__main__":
    main()
