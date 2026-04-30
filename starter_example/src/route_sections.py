from __future__ import annotations

import argparse
import csv
from pathlib import Path

try:
    from .common import read_jsonl, read_yaml, write_jsonl
except ImportError:
    from common import read_jsonl, read_yaml, write_jsonl


def find_section(text: str, include_keywords: list[str], exclude_keywords: list[str], min_chars: int) -> tuple[bool, str, str]:
    positions = [text.find(keyword) for keyword in include_keywords if text.find(keyword) >= 0]
    if not positions:
        return False, "", "not_found"
    start = min(positions)
    section = text[start:].strip()
    if any(section.startswith(keyword) for keyword in exclude_keywords):
        return False, section[:200], "wrong_section"
    if len(section) < min_chars:
        return False, section, "too_short"
    return True, section, "ok"


def route_sections(config_path: str) -> list[dict]:
    config = read_yaml(config_path)
    paths = config["paths"]
    parsed_docs = read_jsonl(paths["parsed_docs"])
    rules = read_yaml(paths["section_rules"])
    rule_name, rule = next(iter(rules["target_sections"].items()))
    sections = []
    report_rows = []

    for doc in parsed_docs:
        full_text = "\n".join(page["text"] for page in doc["pages"])
        found, section_text, issue = find_section(
            full_text,
            rule["include_keywords"],
            rule["exclude_keywords"],
            int(rule["min_chars"]),
        )
        page_no = None
        if found:
            for page in doc["pages"]:
                if any(keyword in page["text"] for keyword in rule["include_keywords"]):
                    page_no = page["page_no"]
                    break
        sections.append(
            {
                "doc_id": doc["doc_id"],
                "stock_code": doc.get("stock_code"),
                "stock_name": doc.get("stock_name"),
                "title": doc["title"],
                "target_section": rule_name,
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
                "target_section": rule_name,
                "found": str(found).lower(),
                "section_title": rule_name,
                "page_start": page_no or "",
                "page_end": page_no or "",
                "quality_issue": issue,
                "notes": section_text[:50].replace("\n", " "),
            }
        )

    write_jsonl(paths["sections_jsonl"], sections)
    report_path = Path(paths["section_report"])
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
    return sections


def main() -> None:
    parser = argparse.ArgumentParser(description="Route target sections from parsed documents.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    args = parser.parse_args()
    sections = route_sections(args.config)
    print(f"Routed sections={len(sections)}.")


if __name__ == "__main__":
    main()

