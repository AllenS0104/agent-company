"""OpenAI LLM Provider"""

from __future__ import annotations

import os
from typing import Any

from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    """OpenAI API 适配器"""

    def __init__(self, model: str | None = None, api_key: str | None = None, **kwargs: Any):
        super().__init__(model=model or os.getenv("OPENAI_MODEL", "gpt-4.1"), **kwargs)
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._base_url = os.getenv("OPENAI_BASE_URL", "")
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            kwargs: dict[str, Any] = {"api_key": self._api_key}
            if self._base_url:
                kwargs["base_url"] = self._base_url
            self._client = AsyncOpenAI(**kwargs)
        return self._client

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    async def check_health(self) -> bool:
        try:
            client = self._get_client()
            await client.models.list()
            return True
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "openai"
