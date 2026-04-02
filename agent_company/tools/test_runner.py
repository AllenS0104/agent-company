"""测试运行器 — 运行 pytest 并解析结果"""

from __future__ import annotations

from typing import Any

from .base import BaseTool, ToolResult
from .executor import CommandExecutor


class TestRunner(BaseTool):
    """运行 pytest 测试并收集结果"""

    def __init__(self, cwd: str | None = None, timeout: int = 120):
        self._executor = CommandExecutor(cwd=cwd, timeout=timeout)

    @property
    def name(self) -> str:
        return "test_runner"

    @property
    def description(self) -> str:
        return "运行 pytest 测试，返回测试结果和覆盖率"

    async def execute(
        self,
        test_path: str = "",
        coverage: bool = False,
        verbose: bool = True,
        **kwargs: Any,
    ) -> ToolResult:
        cmd_parts = ["python", "-m", "pytest"]
        if verbose:
            cmd_parts.append("-v")
        if coverage:
            cmd_parts.extend(["--cov", "--cov-report=term-missing"])
        if test_path:
            cmd_parts.append(test_path)

        command = " ".join(cmd_parts)
        return await self._executor.execute(command=command)
