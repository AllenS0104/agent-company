"""Linter 工具 — 运行 ruff 静态检查"""

from __future__ import annotations

from typing import Any

from .base import BaseTool, ToolResult
from .executor import CommandExecutor


class Linter(BaseTool):
    """使用 ruff 进行代码静态检查"""

    def __init__(self, cwd: str | None = None, timeout: int = 30):
        self._executor = CommandExecutor(cwd=cwd, timeout=timeout)

    @property
    def name(self) -> str:
        return "linter"

    @property
    def description(self) -> str:
        return "运行 ruff 代码静态检查，报告风格和质量问题"

    async def execute(self, path: str = ".", fix: bool = False, **kwargs: Any) -> ToolResult:
        cmd_parts = ["python", "-m", "ruff", "check"]
        if fix:
            cmd_parts.append("--fix")
        cmd_parts.append(path)
        command = " ".join(cmd_parts)
        return await self._executor.execute(command=command)
