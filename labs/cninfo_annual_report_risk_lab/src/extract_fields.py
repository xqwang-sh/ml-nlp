from __future__ import annotations

import argparse
import json
import os
import re

import requests
from dotenv import load_dotenv

from common import read_jsonl, read_yaml, write_jsonl


RISK_RULES = [
    ("市场风险", ["市场需求", "市场波动", "价格波动", "宏观经济", "房地产市场", "资本市场"]),
    ("行业竞争风险", ["竞争加剧", "行业竞争", "市场竞争", "竞争风险"]),
    ("经营风险", ["经营风险", "业务风险", "销售风险", "客户集中", "项目风险", "业绩下滑"]),
    ("财务风险", ["财务风险", "应收账款", "坏账", "现金流", "偿债", "资产减值", "存货跌价"]),
    ("政策与合规风险", ["政策风险", "法律风险", "合规风险", "监管", "税收政策", "产业政策"]),
    ("技术与研发风险", ["技术风险", "研发风险", "技术迭代", "知识产权", "核心技术"]),
    ("供应链与原材料风险", ["原材料", "供应链", "采购", "能源价格", "供应商"]),
    ("汇率与利率风险", ["汇率", "利率", "外汇", "汇兑"]),
    ("环境与安全风险", ["环保", "环境保护", "安全生产", "生产安全", "排放"]),
    ("管理与内控风险", ["管理风险", "内部控制", "内控", "人才流失", "人力资源"]),
]


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def evidence_for_keywords(text: str, keywords: list[str]) -> str | None:
    normalized = normalize_space(text)
    for keyword in keywords:
        index = normalized.find(keyword)
        if index >= 0:
            return normalized[max(0, index - 80) : index + 180]
    return None


def extract_one_rule(section: dict) -> dict:
    text = section["section_text"]
    categories = []
    for category, keywords in RISK_RULES:
        evidence = evidence_for_keywords(text, keywords)
        if evidence:
            categories.append(
                {
                    "category": category,
                    "evidence": {
                        "text": evidence,
                        "page_no": section.get("page_no"),
                    },
                }
            )
    if not categories:
        categories.append(
            {
                "category": "其他风险",
                "evidence": {
                    "text": normalize_space(text)[:240],
                    "page_no": section.get("page_no"),
                },
            }
        )
    return {
        "doc_id": section["doc_id"],
        "stock_code": section.get("stock_code"),
        "company_name": section.get("stock_name"),
        "report_year": "2024",
        "event_type": "年报风险披露",
        "risk_categories": categories,
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
        "report_year": "2024",
        "event_type": "年报风险披露",
        "risk_categories": [
            {
                "category": "市场风险",
                "evidence": {"text": "必须是输入文本中的原文片段", "page_no": section.get("page_no")},
            }
        ],
    }
    prompt = f"""你是上市公司年报风险披露分类助手。请只根据输入的风险披露章节抽取风险类别。

可选类别：
市场风险、行业竞争风险、经营风险、财务风险、政策与合规风险、技术与研发风险、供应链与原材料风险、汇率与利率风险、环境与安全风险、管理与内控风险、其他风险。

规则：
1. 只输出合法 JSON，不要输出解释。
2. risk_categories 可以有多个类别，但不要重复。
3. 每个类别必须给出 evidence.text，且必须是输入文本中的连续原文片段。
4. 不确定时不要猜；无法归入具体类别但原文确有风险披露时，使用“其他风险”。
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
{section["section_text"][:16000]}
"""
    content = call_llm(
        [
            {"role": "system", "content": "你只输出合法 JSON。"},
            {"role": "user", "content": prompt},
        ],
        config,
    )
    return json.loads(strip_json_fence(content))


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
    if not results:
        raise RuntimeError("No extraction results were produced.")
    write_jsonl(output_path, results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract annual-report risk categories.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    parser.add_argument("--method", choices=["rule", "llm"], default=None)
    args = parser.parse_args()
    results = extract_fields(args.config, args.method)
    print(f"Extracted {len(results)} records.")


if __name__ == "__main__":
    main()
