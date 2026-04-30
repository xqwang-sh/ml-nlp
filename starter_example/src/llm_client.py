from __future__ import annotations

import os

import requests
from dotenv import load_dotenv


class LLMClient:
    """Minimal OpenAI-compatible chat client for Week 13 smoke tests."""

    def __init__(
        self,
        base_url_env: str = "LLM_BASE_URL",
        api_key_env: str = "LLM_API_KEY",
        timeout_seconds: int = 60,
    ) -> None:
        load_dotenv()
        self.base_url = os.getenv(base_url_env, "").rstrip("/")
        self.api_key = os.getenv(api_key_env)
        self.timeout_seconds = timeout_seconds
        if not self.base_url:
            raise RuntimeError(f"Missing base URL environment variable: {base_url_env}")
        if not self.api_key or self.api_key == "your_key_here":
            raise RuntimeError(f"Missing real API key environment variable: {api_key_env}")

    def chat(
        self,
        messages: list[dict],
        model: str,
        temperature: float = 0,
        max_tokens: int = 512,
    ) -> str:
        if not model or model == "your_model_here":
            raise RuntimeError("Please set a real model name in .env or configs/model_config.yaml.")
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

