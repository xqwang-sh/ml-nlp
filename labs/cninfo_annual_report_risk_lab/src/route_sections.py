from __future__ import annotations

import argparse
import csv
from pathlib import Path

from common import read_jsonl, read_yaml, write_jsonl


def find_section(text: str, rule: dict) -> tuple[bool, str, str]:
    include_keywords = rule["include_keywords"]
    min_chars = int(rule["min_chars"])
    start = -1
    for keyword in include_keywords:
        start = text.find(keyword)
        if start >= 0:
            break
    if start < 0:
        return False, "", "not_found"
    section = text[start:]
    end_positions = [section.find(marker) for marker in rule.get("end_markers", []) if section.find(marker) > min_chars]
    if end_positions:
        section = section[: min(end_positions)]
    section = section.strip()
    if len(section) < min_chars:
        return False, section, "too_short"
    return True, section, "ok"


def route_sections(config_path: str) -> list[dict]:
    config = read_yaml(config_path)
    parsed_path = Path(config["paths"]["parsed_dir"]) / "parsed_docs.jsonl"
    rules = read_yaml(config["paths"]["section_rules"])
    rule = rules["target_sections"]["annual_report_risk"]
    sections = []
    report_rows = []

    docs = read_jsonl(parsed_path)
    if not docs:
        raise RuntimeError(f"No parsed docs found: {parsed_path}")

    for doc in docs:
        full_text = "\n".join(page["text"] for page in doc["pages"])
        found, section_text, issue = find_section(full_text, rule)
        page_no = None
        if found:
            for page in doc["pages"]:
                if section_text[:20] in page["text"] or any(keyword in page["text"] for keyword in rule["include_keywords"]):
                    page_no = page["page_no"]
                    break
        sections.append(
            {
                "doc_id": doc["doc_id"],
                "stock_code": doc.get("stock_code"),
                "stock_name": doc.get("stock_name"),
                "title": doc["title"],
                "target_section": "annual_report_risk",
                "found": found,
                "page_no": page_no,
                "section_text": section_text,
                "quality_issue": issue,
            }
        )
        report_rows.append(
            {
                "doc_id": doc["doc_id"],
                "title": doc["title"],
                "target_section": "annual_report_risk",
                "found": str(found).lower(),
                "section_title": "可能面对的风险",
                "page_start": page_no or "",
                "page_end": page_no or "",
                "quality_issue": issue,
                "notes": section_text[:40].replace("\n", " "),
            }
        )

    sections_path = Path(config["paths"].get("sections_jsonl", "data/parsed/sections.jsonl"))
    write_jsonl(sections_path, sections)

    report_path = Path(config["paths"]["section_report"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "doc_id",
            "title",
            "target_section",
            "found",
            "section_title",
            "page_start",
            "page_end",
            "quality_issue",
            "notes",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)
    bad_sections = [row for row in report_rows if row["found"] != "true" or row["quality_issue"] != "ok"]
    if bad_sections:
        doc_ids = ", ".join(row["doc_id"] for row in bad_sections)
        raise RuntimeError(f"Section routing failed for doc_id(s): {doc_ids}. See {report_path}")
    return sections


def main() -> None:
    parser = argparse.ArgumentParser(description="Route annual-report risk sections.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    args = parser.parse_args()
    sections = route_sections(args.config)
    print(f"Routed {len(sections)} sections.")


if __name__ == "__main__":
    main()
