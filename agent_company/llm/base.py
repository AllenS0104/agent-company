"""LLM Provider 抽象基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """LLM 服务提供者抽象基类 — 所有 Provider 必须实现此接口"""

    def __init__(self, model: str | None = None, **kwargs: Any):
        self.model = model
        self.config = kwargs

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs: Any,
    ) -> str:
        """发送聊天消息，返回模型回复文本"""
        ...

    @abstractmethod
    async def check_health(self) -> bool:
        """检查 Provider 是否可用"""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 名称标识"""
        ...

    def __repr__(self) -> str:
        return f"<{self.provider_name}(model={self.model})>"
