from __future__ import annotations

import argparse
import re

try:
    from .common import read_jsonl, read_yaml, write_jsonl
except ImportError:
    from common import read_jsonl, read_yaml, write_jsonl


RISK_RULES = [
    ("市场风险", ["市场需求", "市场波动", "宏观经济"]),
    ("行业竞争风险", ["行业竞争", "竞争加剧", "市场竞争"]),
    ("经营风险", ["经营风险", "客户集中", "业务拓展"]),
    ("财务风险", ["应收账款", "现金流", "资产减值"]),
    ("政策与合规风险", ["政策风险", "监管", "合规"]),
    ("管理与内控风险", ["管理风险", "内部控制", "人才"]),
]


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def evidence_for_keywords(text: str, keywords: list[str]) -> str | None:
    normalized = normalize_space(text)
    for keyword in keywords:
        index = normalized.find(keyword)
        if index >= 0:
            return normalized[max(0, index - 60) : index + 160]
    return None


def extract_one(section: dict) -> dict:
    text = section["section_text"]
    categories = []
    for category, keywords in RISK_RULES:
        evidence = evidence_for_keywords(text, keywords)
        if evidence:
            categories.append({"category": category, "evidence": {"text": evidence, "page_no": section.get("page_no")}})
    if not categories:
        categories.append({"category": "其他风险", "evidence": {"text": normalize_space(text)[:180], "page_no": section.get("page_no")}})
    return {
        "doc_id": section["doc_id"],
        "stock_code": section.get("stock_code"),
        "company_name": section.get("stock_name") or "",
        "report_year": "2024",
        "event_type": "年报风险披露",
        "risk_categories": categories,
    }


def extract_fields(config_path: str) -> list[dict]:
    config = read_yaml(config_path)
    paths = config["paths"]
    results = [extract_one(section) for section in read_jsonl(paths["sections_jsonl"]) if section["found"]]
    write_jsonl(paths["extract_results"], results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract starter annual-report risk categories.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    args = parser.parse_args()
    results = extract_fields(args.config)
    print(f"Extracted records={len(results)}.")


if __name__ == "__main__":
    main()
