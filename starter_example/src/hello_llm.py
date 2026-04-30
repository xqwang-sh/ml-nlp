from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv

try:
    from .common import read_yaml
    from .llm_client import LLMClient
except ImportError:
    from common import read_yaml
    from llm_client import LLMClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a minimal LLM API smoke test.")
    parser.add_argument("--config", default="configs/model_config.yaml")
    args = parser.parse_args()

    load_dotenv()
    config = read_yaml(args.config)
    model = os.getenv("LLM_MODEL") or config.get("model")
    try:
        client = LLMClient(
            base_url_env=config.get("base_url_env", "LLM_BASE_URL"),
            api_key_env=config.get("api_key_env", "LLM_API_KEY"),
            timeout_seconds=int(config.get("timeout_seconds", 60)),
        )
        content = client.chat(
            messages=[
                {"role": "system", "content": "你是一个简洁的课程 API 连通性检查助手。"},
                {"role": "user", "content": "请只回复：LLM API connected"},
            ],
            model=model,
            temperature=float(config.get("temperature", 0)),
            max_tokens=int(config.get("max_tokens", 512)),
        )
    except Exception as exc:
        raise SystemExit(
            "LLM API check failed. 请确认已复制 .env.example 为 .env，"
            f"并填写真实 base URL、API key 和 model。\n原因：{exc}"
        ) from None
    print(content)


if __name__ == "__main__":
    main()
