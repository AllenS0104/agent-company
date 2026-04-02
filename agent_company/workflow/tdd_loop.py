"""TDD Loop 工作流 — 测试驱动闭环

流程：
1. QA 先给出失败测试
2. Coder 让测试通过
3. Reviewer 重构
4. 迭代直到全部通过 + 代码质量达标
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


class TDDLoopWorkflow(BaseWorkflow):
    """TDD Loop 工作流"""

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
        return "tdd_loop"

    async def run(
        self, thread: Thread | None = None, topic: str = "", **kwargs: Any,
    ) -> WorkflowResult:
        max_rounds = kwargs.get("max_rounds", 3)

        if thread is None:
            thread = await self.thread_mgr.create_thread(
                topic=topic, mode=WorkflowMode.TDD_LOOP,
                max_rounds=max_rounds,
            )

        all_messages: list[Message] = []

        try:
            self.state_machine.transition(Phase.COLLECTING_VIEWS)
            await self.thread_mgr.update_status(thread.id, ThreadStatus.DISCUSSING)
            opening = await self.moderator.open_discussion(thread)
            all_messages.append(opening)
            await self.storage.save_message(opening)

            for round_num in range(1, max_rounds + 1):
                thread.current_round = round_num
                round_msg = await self.moderator.announce_round(
                    thread, round_num,
                )
                all_messages.append(round_msg)
                await self.storage.save_message(round_msg)

                # Red: QA 写失败测试
                qa = self.agents.get(Role.QA)
                if qa:
                    msg = self._ensure_content(await qa.respond(
                        thread.id, all_messages,
                        extra_instruction=(
                            f"[TDD 第{round_num}轮 - Red] "
                            f"请为以下需求编写测试用例（应当当前失败）：\n{topic}"
                            if round_num == 1 else
                            f"[TDD 第{round_num}轮 - Red] "
                            "请根据上一轮的实现，补充更多边界和异常测试。"
                        ),
                    ))
                    all_messages.append(msg)
                    await self.storage.save_message(msg)

                # Green: Coder 让测试通过
                coder = self.agents.get(Role.CODER)
                if coder:
                    msg = self._ensure_content(await coder.respond(
                        thread.id, all_messages,
                        extra_instruction=(
                            f"[TDD 第{round_num}轮 - Green] "
                            "请编写最小实现让上述测试全部通过。"
                        ),
                    ))
                    all_messages.append(msg)
                    await self.storage.save_message(msg)

                # Refactor: Reviewer 重构
                reviewer = self.agents.get(Role.REVIEWER)
                if reviewer:
                    msg = self._ensure_content(await reviewer.respond(
                        thread.id, all_messages,
                        extra_instruction=(
                            f"[TDD 第{round_num}轮 - Refactor] "
                            "请审查代码并提出重构建议，确保可读性和可维护性。"
                        ),
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
            logger.error(f"[TDDLoop] Failed: {e}", exc_info=True)
            return WorkflowResult(
                thread=thread, messages=all_messages,
                success=False, error=str(e),
            )
