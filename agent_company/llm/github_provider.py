"""GitHub Models LLM Provider — 通过 GitHub 账号认证访问多种模型"""

from __future__ import annotations

import os
import subprocess
from typing import Any

from .base import LLMProvider


class GitHubModelsProvider(LLMProvider):
    """GitHub Models API 适配器

    认证方式（按优先级）：
    1. 构造函数传入 token
    2. GITHUB_TOKEN 环境变量
    3. 自动从 `gh auth token` 获取（推荐，无需手动配置）

    使用 OpenAI 兼容接口，支持 GPT-4o、Gemini、Claude 等模型。
    """

    BASE_URL = "https://models.github.ai/inference"

    def __init__(
        self,
        model: str | None = None,
        token: str | None = None,
        **kwargs: Any,
    ):
        super().__init__(
            model=model or os.getenv("GITHUB_MODELS_MODEL", "openai/gpt-4.1"),
            **kwargs,
        )
        self._token = token
        self._client = None

    def _resolve_token(self) -> str:
        """按优先级获取 GitHub Token"""
        # 1. 构造函数传入
        if self._token:
            return self._token

        # 2. 环境变量
        env_token = os.getenv("GITHUB_TOKEN", "")
        if env_token:
            return env_token

        # 3. 自动从 gh CLI 获取
        return self._get_token_from_gh_cli()

    @staticmethod
    def _get_token_from_gh_cli() -> str:
        """从 gh auth token 命令获取当前登录的 Token"""
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        raise RuntimeError(
            "无法获取 GitHub Token。请确保：\n"
            "  1. 已安装 gh CLI (https://cli.github.com)\n"
            "  2. 已运行 `gh auth login` 完成登录\n"
            "  或设置 GITHUB_TOKEN 环境变量"
        )

    def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            token = self._resolve_token()
            self._client = AsyncOpenAI(
                base_url=self.BASE_URL,
                api_key=token,
            )
        return self._client

    # Reasoning 模型不支持 temperature/max_tokens
    REASONING_MODELS = {
        "openai/o3", "openai/o4-mini", "openai/o3-mini", "openai/o1",
        "openai/gpt-5-mini", "openai/gpt-5.1", "openai/gpt-5.2",
        "openai/gpt-5.2-codex", "openai/gpt-5.3-codex",
        "openai/gpt-5.4", "openai/gpt-5.4-mini",
    }

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        client = self._get_client()
        params: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }
        if self.model in self.REASONING_MODELS:
            # reasoning 模型不接受 temperature 和 max_tokens
            pass
        else:
            params["temperature"] = temperature
            params["max_tokens"] = max_tokens
        params.update(kwargs)
        response = await client.chat.completions.create(**params)  # type: ignore
        return response.choices[0].message.content or ""

    async def check_health(self) -> bool:
        try:
            client = self._get_client()
            # 发一个简单请求测试连通性
            await client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return "github"
