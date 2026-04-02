"""Pair Programming 工作流 — 结对编码模式

流程：
1. Idea/Architect 提出需求和设计
2. Coder 编写实现
3. Reviewer 实时审查、找 bug、提重构
4. QA 提供测试用例
5. 迭代直到通过审查
"""

from __future__ import annotations

import logging
from typing import Any

from ..agents.base import BaseAgent
from ..core.message_bus import MessageBus
from ..core.models import Message, Role, Thread, ThreadStatus, WorkflowMode
from ..core.storage import Storage
from ..core.thread import ThreadManager
from ..llm.base import LLMProvider
from ..orchestration.moderator import Moderator
from ..orchestration.state_machine import Phase, StateMachine
from .base import BaseWorkflow, WorkflowResult

logger = logging.getLogger(__name__)


class PairProgrammingWorkflow(BaseWorkflow):
    """Pair Programming 工作流"""

    def __init__(self, agents: list[BaseAgent], llm: LLMProvider,
                 bus: MessageBus, storage: Storage):
        self.agents = {a.role: a for a in agents}
        self.llm = llm
        self.bus = bus
        self.storage = storage
        self.thread_mgr = ThreadManager(bus, storage)
        self.moderator = Moderator(bus)
        self.state_machine = StateMachine()

    @property
    def name(self) -> str:
        return "pair_programming"

    async def run(
        self, thread: Thread | None = None, topic: str = "", **kwargs: Any,
    ) -> WorkflowResult:
        max_rounds = kwargs.get("max_rounds", 3)

        if thread is None:
            thread = await self.thread_mgr.create_thread(
                topic=topic, mode=WorkflowMode.PAIR_PROGRAMMING,
                max_rounds=max_rounds,
            )

        all_messages: list[Message] = []

        try:
            self.state_machine.transition(Phase.COLLECTING_VIEWS)
            await self.thread_mgr.update_status(thread.id, ThreadStatus.DISCUSSING)
            opening = await self.moderator.open_discussion(thread)
            all_messages.append(opening)
            await self.storage.save_message(opening)

            # Architect 给出设计
            architect = self.agents.get(Role.ARCHITECT)
            if architect:
                msg = self._ensure_content(await architect.respond(
                    thread.id, all_messages,
                    extra_instruction=f"请为以下需求给出简洁的技术设计：\n{topic}",
                ))
                all_messages.append(msg)
                await self.storage.save_message(msg)

            # 结对迭代
            for round_num in range(1, max_rounds + 1):
                thread.current_round = round_num
                round_msg = await self.moderator.announce_round(
                    thread, round_num,
                )
                all_messages.append(round_msg)
                await self.storage.save_message(round_msg)

                # Coder 实现
                coder = self.agents.get(Role.CODER)
                if coder:
                    msg = self._ensure_content(await coder.respond(
                        thread.id, all_messages,
                        extra_instruction="请根据设计编写代码实现。",
                    ))
                    all_messages.append(msg)
                    await self.storage.save_message(msg)

                # Reviewer 审查
                reviewer = self.agents.get(Role.REVIEWER)
                if reviewer:
                    msg = self._ensure_content(await reviewer.respond(
                        thread.id, all_messages,
                        extra_instruction="请审查代码，指出问题并给出修改建议。",
                    ))
                    all_messages.append(msg)
                    await self.storage.save_message(msg)

                # QA 测试（如果有）
                qa = self.agents.get(Role.QA)
                if qa:
                    msg = self._ensure_content(await qa.respond(
                        thread.id, all_messages,
                        extra_instruction="请为上述代码编写测试用例。",
                    ))
                    all_messages.append(msg)
                    await self.storage.save_message(msg)

            self.state_machine.transition(Phase.CHALLENGING)
            self.state_machine.transition(Phase.DECIDING)
            conclude_msg = await self.moderator.conclude_discussion(thread)
            all_messages.append(conclude_msg)
            await self.storage.save_message(conclude_msg)

            self.state_machine.transition(Phase.PLANNING)
            self.state_machine.transition(Phase.EXECUTING)
            self.state_machine.transition(Phase.REVIEWING)
            self.state_machine.transition(Phase.COMPLETED)
            await self.thread_mgr.update_status(thread.id, ThreadStatus.CLOSED)

            return WorkflowResult(
                thread=thread, messages=all_messages, success=True,
            )

        except Exception as e:
            logger.error(f"[PairProgramming] Failed: {e}", exc_info=True)
            return WorkflowResult(
                thread=thread, messages=all_messages,
                success=False, error=str(e),
            )
