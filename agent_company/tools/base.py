"""工具基类 — 所有可供 Agent 调用的工具的抽象接口"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool
    output: str = ""
    error: str = ""
    artifacts: list[str] = Field(default_factory=list)  # 产出物路径


class BaseTool(ABC):
    """工具抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述（用于 Agent 理解该工具的能力）"""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """执行工具，返回结果"""
        ...

    def __repr__(self) -> str:
        return f"<Tool:{self.name}>"
