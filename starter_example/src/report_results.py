from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .common import read_csv, read_jsonl, read_yaml
except ImportError:
    from common import read_csv, read_jsonl, read_yaml


def generate_report(config_path: str) -> str:
    config = read_yaml(config_path)
    paths = config["paths"]
    rows = read_csv(paths["validated_csv"])
    errors = read_jsonl(paths["validation_errors"])
    report_path = Path(paths["summary_report"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Starter Summary Report",
        "",
        "## Run Summary",
        "",
        f"- Valid records: {len(rows)}",
        f"- Validation errors: {len(errors)}",
        "",
        "## Output Preview",
        "",
        "| doc_id | company_name | shareholder_name | amount | ratio | evidence_page |",
        "|---|---|---|---|---|---:|",
    ]
    for row in rows:
        lines.append(
            "| {doc_id} | {company_name} | {shareholder_name} | {amount} | {ratio} | {page} |".format(
                doc_id=row.get("doc_id", ""),
                company_name=row.get("company_name", ""),
                shareholder_name=row.get("shareholder_name", ""),
                amount=row.get("reduction_amount_text", ""),
                ratio=row.get("reduction_ratio_text", ""),
                page=row.get("page_no", ""),
            )
        )
    lines.extend(
        [
            "",
            "## Next Steps",
            "",
            "- Replace offline sample text with real CNINFO PDFs or MinerU parsed outputs.",
            "- Replace rule-based extraction with LLM extraction if your project requires it.",
            "- Keep evidence_text and Pydantic validation in the final project.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(report_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate starter summary report.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    args = parser.parse_args()
    report = generate_report(args.config)
    print(f"Wrote {report}")


if __name__ == "__main__":
    main()

