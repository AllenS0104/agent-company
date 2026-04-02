"""命令执行器 — 安全地运行外部命令"""

from __future__ import annotations

import asyncio
import os
import shlex
from typing import Any

from .base import BaseTool, ToolResult

ALLOWED_COMMANDS: frozenset[str] = frozenset({
    "python", "python3", "node", "npm", "npx",
    "pytest", "ruff", "mypy", "black", "isort", "flake8",
    "git", "make", "cargo", "go", "javac", "java",
    "pip", "pip3", "poetry", "uv", "dotnet",
})


class CommandExecutor(BaseTool):
    """在子进程中执行外部命令（白名单校验 + exec 模式）"""

    def __init__(self, cwd: str | None = None, timeout: int = 60):
        self.cwd = cwd
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "executor"

    @property
    def description(self) -> str:
        return "执行外部命令（构建、测试、基准等）"

    async def execute(self, command: str = "", **kwargs: Any) -> ToolResult:
        if not command:
            return ToolResult(success=False, error="No command provided")

        try:
            args = shlex.split(command)
        except ValueError as e:
            return ToolResult(success=False, error=f"Invalid command syntax: {e}")

        if not args:
            return ToolResult(success=False, error="Empty command after parsing")

        # 白名单校验：只允许预定义的基础命令
        base_cmd = os.path.splitext(os.path.basename(args[0]))[0]
        if base_cmd not in ALLOWED_COMMANDS:
            return ToolResult(
                success=False,
                error=f"Command '{base_cmd}' is not in the allowed list",
            )

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.cwd,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
            success = proc.returncode == 0
            return ToolResult(
                success=success,
                output=stdout.decode("utf-8", errors="replace"),
                error=stderr.decode("utf-8", errors="replace"),
            )
        except asyncio.TimeoutError:
            return ToolResult(success=False, error=f"Command timed out after {self.timeout}s")
        except Exception as e:
            return ToolResult(success=False, error=str(e))
