"""Spec-first 工作流 — 契约优先模式

流程：
1. Architect 输出接口契约（API 定义/类型/Proto）
2. QA 根据契约生成测试用例和验收标准
3. Coder 实现，直到测试全绿
4. Reviewer 审查实现是否符合契约
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


class SpecFirstWorkflow(BaseWorkflow):
    """Spec-first 工作流"""

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
        return "spec_first"

    async def run(
        self, thread: Thread | None = None, topic: str = "", **kwargs: Any,
    ) -> WorkflowResult:
        max_rounds = kwargs.get("max_rounds", 3)

        if thread is None:
            thread = await self.thread_mgr.create_thread(
                topic=topic, mode=WorkflowMode.SPEC_FIRST,
                max_rounds=max_rounds,
            )

        all_messages: list[Message] = []

        try:
            self.state_machine.transition(Phase.COLLECTING_VIEWS)
            await self.thread_mgr.update_status(thread.id, ThreadStatus.DISCUSSING)
            opening = await self.moderator.open_discussion(thread)
            all_messages.append(opening)
            await self.storage.save_message(opening)

            # Step 1: Architect 定义契约
            architect = self.agents.get(Role.ARCHITECT)
            if architect:
                msg = self._ensure_content(await architect.respond(
                    thread.id, all_messages,
                    extra_instruction=(
                        f"请为以下需求定义接口契约（API/类型/数据结构）：\n{topic}\n\n"
                        "输出格式：函数签名、输入输出类型、错误码、约束条件。"
                    ),
                ))
                all_messages.append(msg)
                await self.storage.save_message(msg)

            # Step 2: QA 根据契约生成测试
            qa = self.agents.get(Role.QA)
            if qa:
                msg = self._ensure_content(await qa.respond(
                    thread.id, all_messages,
                    extra_instruction=(
                        "请根据上述接口契约生成测试用例（pytest 格式）。\n"
                        "包括：正向测试、边界测试、异常测试。"
                    ),
                ))
                all_messages.append(msg)
                await self.storage.save_message(msg)

            # Step 3: Coder 实现 + Reviewer 审查 迭代
            for round_num in range(1, max_rounds + 1):
                thread.current_round = round_num
                round_msg = await self.moderator.announce_round(
                    thread, round_num,
                )
                all_messages.append(round_msg)
                await self.storage.save_message(round_msg)

                coder = self.agents.get(Role.CODER)
                if coder:
                    msg = self._ensure_content(await coder.respond(
                        thread.id, all_messages,
                        extra_instruction=(
                            "请根据接口契约和测试用例编写实现。\n"
                            "目标：让所有测试通过。"
                        ),
                    ))
                    all_messages.append(msg)
                    await self.storage.save_message(msg)

                reviewer = self.agents.get(Role.REVIEWER)
                if reviewer:
                    msg = self._ensure_content(await reviewer.respond(
                        thread.id, all_messages,
                        extra_instruction=(
                            "请审查实现是否符合接口契约，"
                            "代码质量是否达标。"
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
            logger.error(f"[SpecFirst] Failed: {e}", exc_info=True)
            return WorkflowResult(
                thread=thread, messages=all_messages,
                success=False, error=str(e),
            )
