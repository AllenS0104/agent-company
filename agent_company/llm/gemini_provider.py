"""Gemini LLM Provider"""

from __future__ import annotations

import os
from typing import Any

from .base import LLMProvider


class GeminiProvider(LLMProvider):
    """Google Gemini API 适配器"""

    def __init__(self, model: str | None = None, api_key: str | None = None, **kwargs: Any):
        super().__init__(model=model or os.getenv("GEMINI_MODEL", "gemini-3.1-flash"), **kwargs)
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self._client = None

    def _get_client(self):
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)
            self._client = genai.GenerativeModel(self.model)
        return self._client

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        client = self._get_client()
        # 将 OpenAI 格式转为 Gemini 格式
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            if msg["role"] == "system":
                # Gemini 不支持 system role，合并到第一条 user 消息
                contents.append({"role": "user", "parts": [msg["content"]]})
                contents.append({"role": "model", "parts": ["understood."]})
            else:
                contents.append({"role": role, "parts": [msg["content"]]})

        response = await client.generate_content_async(
            contents,
            generation_config={"temperature": temperature, "max_output_tokens": max_tokens},
        )
        return response.text or ""

    async def check_health(self) -> bool:
        try:
            self._get_client()
            return True
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "gemini"
