from __future__ import annotations

import argparse
import re

try:
    from .common import read_jsonl, read_yaml, write_jsonl
except ImportError:
    from common import read_jsonl, read_yaml, write_jsonl


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def first_match(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(1) if match.groups() else match.group(0)
            return normalize_space(value).strip(" 。；;，,")
    return None


def extract_one(section: dict) -> dict:
    text = normalize_space(section["section_text"])
    shareholder_name = first_match(
        [
            r"股东([\u4e00-\u9fa5A-Za-z0-9（）()、·]+?)计划",
            r"实际控制人([\u4e00-\u9fa5A-Za-z0-9（）()、·]+?)先生",
        ],
        text,
    )
    amount = first_match([r"不超过\s*([0-9,]+ 股)", r"减持公司股份不超过\s*([0-9,]+ 股)"], text)
    ratio = first_match([r"总股本(?:的)?\s*([0-9.]+%)", r"总股本的\s*([0-9.]+%)"], text)
    period = first_match([r"减持期间为([^。]+)", r"三个月内"], text)
    reason = first_match([r"减持原因为([^。]+)"], text)
    evidence = ""
    for sentence in re.split(r"[。\n]", section["section_text"]):
        if "减持" in sentence and ("不超过" in sentence or "减持期间" in sentence):
            evidence = normalize_space(sentence) + "。"
            break

    return {
        "doc_id": section["doc_id"],
        "stock_code": section.get("stock_code"),
        "company_name": section.get("stock_name") or "",
        "event_type": "股东减持",
        "shareholder_name": shareholder_name,
        "reduction_method": "集中竞价交易" if "集中竞价" in text else None,
        "reduction_amount_text": amount,
        "reduction_ratio_text": ratio,
        "reduction_period": period,
        "reason": reason,
        "evidence": {
            "text": evidence or section["section_text"][:100],
            "page_no": section.get("page_no"),
        },
    }


def extract_fields(config_path: str) -> list[dict]:
    config = read_yaml(config_path)
    paths = config["paths"]
    results = [extract_one(section) for section in read_jsonl(paths["sections_jsonl"]) if section["found"]]
    write_jsonl(paths["extract_results"], results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract starter fields with simple rules.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    args = parser.parse_args()
    results = extract_fields(args.config)
    print(f"Extracted records={len(results)}.")


if __name__ == "__main__":
    main()
