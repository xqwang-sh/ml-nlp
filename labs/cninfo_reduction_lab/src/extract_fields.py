from __future__ import annotations

import argparse
import json
import os
import re

import requests
from dotenv import load_dotenv

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


def extract_one_rule(section: dict) -> dict:
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


def strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.I).strip()
        text = re.sub(r"```$", "", text).strip()
    return text


def call_llm(messages: list[dict], config: dict) -> str:
    load_dotenv()
    llm = config.get("extract", {}).get("llm", {})
    base_url = os.getenv(llm.get("base_url_env", "LLM_BASE_URL"), "").rstrip("/")
    api_key = os.getenv(llm.get("api_key_env", "LLM_API_KEY"), "")
    model = os.getenv(llm.get("model_env", "LLM_MODEL"), "")
    if not base_url:
        raise RuntimeError("Missing LLM_BASE_URL. For SiliconFlow use https://api.siliconflow.cn/v1")
    if not api_key or api_key == "your_key_here":
        raise RuntimeError("Missing real LLM_API_KEY.")
    if not model or model == "your_model_here":
        raise RuntimeError("Missing real LLM_MODEL.")

    response = requests.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": float(llm.get("temperature", 0)),
            "max_tokens": int(llm.get("max_tokens", 2048)),
        },
        timeout=int(llm.get("timeout_seconds", 60)),
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def extract_one_llm(section: dict, config: dict) -> dict:
    schema_hint = {
        "doc_id": section["doc_id"],
        "stock_code": section.get("stock_code"),
        "company_name": section.get("stock_name"),
        "event_type": "股东减持",
        "shareholder_name": None,
        "reduction_method": None,
        "reduction_amount_text": None,
        "reduction_ratio_text": None,
        "reduction_period": None,
        "reason": None,
        "evidence": {"text": "", "page_no": section.get("page_no")},
    }
    prompt = f"""你是金融公告结构化抽取助手。请只根据输入文本抽取字段。

规则：
1. 只输出合法 JSON，不要输出解释。
2. 不确定或原文不存在的字段输出 null。
3. 字段值必须来自输入文本或题头元数据，不得根据常识补全。
4. evidence.text 必须是输入文本中的连续原文片段。
5. 输出字段必须与 JSON 模板一致。

JSON 模板：
{json.dumps(schema_hint, ensure_ascii=False)}

题头元数据：
doc_id={section["doc_id"]}
stock_code={section.get("stock_code")}
company_name={section.get("stock_name")}
title={section["title"]}
page_no={section.get("page_no")}

输入文本：
{section["section_text"][:12000]}
"""
    content = call_llm(
        [
            {"role": "system", "content": "你只输出合法 JSON。"},
            {"role": "user", "content": prompt},
        ],
        config,
    )
    result = json.loads(strip_json_fence(content))
    result.setdefault("doc_id", section["doc_id"])
    result.setdefault("stock_code", section.get("stock_code"))
    result.setdefault("company_name", section.get("stock_name"))
    result.setdefault("event_type", "股东减持")
    result.setdefault("evidence", {"text": section["section_text"][:80], "page_no": section.get("page_no")})
    return result


def extract_fields(config_path: str, method: str | None = None) -> list[dict]:
    config = read_yaml(config_path)
    sections_path = config["paths"].get("sections_jsonl", "data/parsed/sections.jsonl")
    output_path = config["paths"]["extract_results"]
    method = method or config.get("extract", {}).get("provider", "rule")
    results = []
    for section in read_jsonl(sections_path):
        if section["found"]:
            if method == "rule":
                results.append(extract_one_rule(section))
            elif method == "llm":
                results.append(extract_one_llm(section, config))
            else:
                raise ValueError(f"Unknown extraction method: {method}")
    write_jsonl(output_path, results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract demo fields with simple rules.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    parser.add_argument("--method", choices=["rule", "llm"], default=None)
    args = parser.parse_args()
    results = extract_fields(args.config, args.method)
    print(f"Extracted {len(results)} records.")


if __name__ == "__main__":
    main()
