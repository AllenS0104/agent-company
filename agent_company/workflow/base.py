"""工作流基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..core.models import Decision, Message, TaskCard, Thread

_EMPTY_RESPONSE_FALLBACK = "（本轮暂无额外补充）"


class BaseWorkflow(ABC):
    """工作流抽象基类 — 定义协作模式的标准接口"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工作流名称"""
        ...

    @abstractmethod
    async def run(
        self, thread: Thread | None = None, topic: str = "", **kwargs: Any,
    ) -> WorkflowResult:
        """执行工作流"""
        ...

    @staticmethod
    def _ensure_content(msg: Message) -> Message:
        """确保消息内容不为空，空内容时用默认提示替代"""
        if not msg.content or not msg.content.strip():
            msg.content = f"[{msg.agent_role.value}] {_EMPTY_RESPONSE_FALLBACK}"
        return msg


class WorkflowResult:
    """工作流执行结果"""

    def __init__(
        self,
        thread: Thread,
        messages: list[Message] | None = None,
        decision: Decision | None = None,
        tasks: list[TaskCard] | None = None,
        artifacts: list[str] | None = None,
        success: bool = True,
        error: str = "",
    ):
        self.thread = thread
        self.messages = messages or []
        self.decision = decision
        self.tasks = tasks or []
        self.artifacts = artifacts or []
        self.success = success
        self.error = error
