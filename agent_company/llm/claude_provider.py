"""Claude LLM Provider"""

from __future__ import annotations

import os
from typing import Any

from .base import LLMProvider


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API 适配器"""

    def __init__(self, model: str | None = None, api_key: str | None = None, **kwargs: Any):
        super().__init__(
            model=model or os.getenv("CLAUDE_MODEL", "claude-sonnet-4.6"), **kwargs
        )
        self._api_key = api_key or os.getenv("CLAUDE_API_KEY", "")
        self._client = None

    def _get_client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic
            self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        client = self._get_client()
        # 提取 system prompt
        system_prompt = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt += msg["content"] + "\n"
            else:
                chat_messages.append({"role": msg["role"], "content": msg["content"]})

        response = await client.messages.create(
            model=self.model,
            system=system_prompt.strip(),
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.content[0].text if response.content else ""

    async def check_health(self) -> bool:
        try:
            self._get_client()
            return True
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "claude"
