from __future__ import annotations

import argparse
import re

from common import read_jsonl, read_yaml, write_jsonl


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_regex(text: str) -> str:
    text = normalize_space(text)
    # PDF text extraction often inserts spaces between Chinese characters.
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[：:，,；;（）()])", "", text)
    text = re.sub(r"(?<=[：:，,；;（）()])\s+(?=[\u4e00-\u9fff])", "", text)
    return text


def search(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.S)
    if not match:
        return None
    return normalize_space(match.group(1)).strip(" 。；;，,")


def first_match(patterns: list[str], text: str) -> str | None:
    for pattern in patterns:
        value = search(pattern, text)
        if value:
            return value
    return None


def extract_one(section: dict) -> dict:
    text = section["section_text"]
    compact = normalize_for_regex(text)
    company_name = section.get("stock_name") or section["title"].split("关于")[0]
    shareholder_name = first_match(
        [
            r"股东名称[:：]\s*([^。\n]+)",
            r"股东([\u4e00-\u9fa5A-Za-z0-9（）()、·]+?)保证",
            r"实际控制人([\u4e00-\u9fa5A-Za-z0-9（）()、·]+?)先生保证",
            r"的([\u4e00-\u9fa5A-Za-z0-9（）()、·]+?)（以下简称",
        ],
        compact,
    )
    if shareholder_name:
        shareholder_name = re.sub(r"^(、|及)?(控股股东|实际控制人|董事长|总经理|股东)", "", shareholder_name)
        shareholder_name = re.sub(r"(先生|女士)$", "", shareholder_name)

    reduction_method = None
    if "集中竞价" in text:
        reduction_method = "集中竞价交易"
    elif "大宗交易" in text:
        reduction_method = "大宗交易"

    evidence_sentence = None
    for sentence in re.split(r"[。\n]", text):
        normalized_sentence = normalize_for_regex(sentence)
        if "减持" in normalized_sentence and ("不超过" in normalized_sentence or "减持期间" in normalized_sentence):
            evidence_sentence = normalized_sentence.strip() + "。"
            break

    evidence_scope = evidence_sentence or compact

    amount = first_match(
        [
            r"减持(?:其所持有的)?(?:本公司|我公司|公司)?股份不超过[:：]?\s*([0-9,]+ 股)",
            r"减持不超过[:：]?\s*([0-9,]+ 股)(?:公司)?股份",
            r"不超过[:：]?\s*([0-9,]+ 股)(?:公司|我公司)?股份",
            r"不超过[:：]?\s*([0-9,]+ 股)",
            r"计划减持数量(?:（股）)?\s*([0-9,]+ 股)",
        ],
        compact,
    )
    ratio_scope = evidence_scope
    if amount:
        amount_index_for_ratio = compact.find(amount)
        if amount_index_for_ratio >= 0:
            ratio_scope = compact[amount_index_for_ratio : amount_index_for_ratio + 220]

    ratio = first_match(
        [
            r"占(?:公司|本公司)?(?:当前)?总股本(?:的|比例不超过)?\s*([0-9.]+%)",
            r"即不超过(?:公司|本公司)?(?:当前)?总股本(?:的)?\s*([0-9.]+%)",
            r"计划减持比例\s*([0-9.]+%)",
            r"减持占总股本\s*的比例.*?([0-9.]+%)",
        ],
        ratio_scope,
    )
    period = first_match(
        [
            r"减持期间为([^。]+)",
            r"三个月内（([^）]+)）",
            r"减持期间\s*([0-9]{4}[^。]+)",
        ],
        compact,
    )
    reason = first_match([r"减持原因(?:为|：)\s*([^。]+)", r"减持原因为([^。]+)"], compact)
    if (not evidence_sentence or "不超过" not in evidence_sentence) and amount:
        amount_index = compact.find(amount)
        if amount_index >= 0:
            evidence_sentence = compact[max(0, amount_index - 70) : amount_index + 90] + "..."

    return {
        "doc_id": section["doc_id"],
        "stock_code": section.get("stock_code"),
        "company_name": company_name,
        "event_type": "股东减持",
        "shareholder_name": shareholder_name,
        "reduction_method": reduction_method,
        "reduction_amount_text": amount,
        "reduction_ratio_text": ratio,
        "reduction_period": period,
        "reason": reason,
        "evidence": {
            "text": evidence_sentence or text[:80],
            "page_no": section.get("page_no"),
        },
    }


def extract_fields(config_path: str) -> list[dict]:
    config = read_yaml(config_path)
    sections_path = config["paths"].get("sections_jsonl", "data/parsed/sections.jsonl")
    output_path = config["paths"]["extract_results"]
    results = []
    for section in read_jsonl(sections_path):
        if section["found"]:
            results.append(extract_one(section))
    write_jsonl(output_path, results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract demo fields with simple rules.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    args = parser.parse_args()
    results = extract_fields(args.config)
    print(f"Extracted {len(results)} records.")


if __name__ == "__main__":
    main()
