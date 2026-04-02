"""Red Team / Blue Team 工作流 — 攻防模式

流程：
1. Blue Team（Idea + Architect + Coder）提出方案并实现
2. Red Team（Reviewer + Security + QA）专门找漏洞、破坏性测试
3. Blue Team 修复
4. 迭代直到 Red Team 无法找到新问题
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
from ..orchestration.judge import Judge
from ..orchestration.moderator import Moderator
from ..orchestration.state_machine import Phase, StateMachine
from .base import BaseWorkflow, WorkflowResult

logger = logging.getLogger(__name__)

BLUE_ROLES = [Role.IDEA, Role.ARCHITECT, Role.CODER]
RED_ROLES = [Role.REVIEWER, Role.SECURITY, Role.QA]


class RedBlueTeamWorkflow(BaseWorkflow):
    """Red Team / Blue Team 工作流"""

    def __init__(self, agents: list[BaseAgent], llm: LLMProvider,
                 bus: MessageBus, storage: Storage):
        self.agents = {a.role: a for a in agents}
        self.llm = llm
        self.bus = bus
        self.storage = storage
        self.thread_mgr = ThreadManager(bus, storage)
        self.moderator = Moderator(bus)
        self.judge = Judge(llm)
        self.state_machine = StateMachine()

    @property
    def name(self) -> str:
        return "red_blue_team"

    async def run(
        self, thread: Thread | None = None, topic: str = "", **kwargs: Any,
    ) -> WorkflowResult:
        max_rounds = kwargs.get("max_rounds", 2)

        if thread is None:
            thread = await self.thread_mgr.create_thread(
                topic=topic, mode=WorkflowMode.RED_BLUE_TEAM,
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

                # Blue Team 提方案/修复
                blue_instruction = (
                    f"[Blue Team 第{round_num}轮] "
                    "请提出方案并实现。如果是后续轮次，请修复 Red Team 发现的问题。"
                    if round_num == 1 else
                    f"[Blue Team 第{round_num}轮] "
                    "请针对 Red Team 发现的问题进行修复和加固。"
                )
                for role in BLUE_ROLES:
                    agent = self.agents.get(role)
                    if agent:
                        msg = self._ensure_content(await agent.respond(
                            thread.id, all_messages,
                            extra_instruction=blue_instruction,
                        ))
                        all_messages.append(msg)
                        await self.storage.save_message(msg)

                # Red Team 攻击
                red_instruction = (
                    f"[Red Team 第{round_num}轮] "
                    "请从你的专业角度尽全力找出 Blue Team 方案的漏洞、"
                    "边界问题和安全风险。给出具体的攻击场景。"
                )
                for role in RED_ROLES:
                    agent = self.agents.get(role)
                    if agent:
                        msg = self._ensure_content(await agent.respond(
                            thread.id, all_messages,
                            extra_instruction=red_instruction,
                        ))
                        all_messages.append(msg)
                        await self.storage.save_message(msg)

            # 仲裁
            self.state_machine.transition(Phase.CHALLENGING)
            self.state_machine.transition(Phase.DECIDING)
            conclude_msg = await self.moderator.conclude_discussion(thread)
            all_messages.append(conclude_msg)
            await self.storage.save_message(conclude_msg)

            weights = {a.id: a.config.weight for a in self.agents.values()}
            decision = await self.judge.arbitrate(
                thread.id, all_messages, weights,
            )
            await self.storage.save_decision(decision)

            self.state_machine.transition(Phase.PLANNING)
            self.state_machine.transition(Phase.EXECUTING)
            self.state_machine.transition(Phase.REVIEWING)
            self.state_machine.transition(Phase.COMPLETED)
            await self.thread_mgr.update_status(thread.id, ThreadStatus.CLOSED)

            return WorkflowResult(
                thread=thread, messages=all_messages,
                decision=decision, success=True,
            )

        except Exception as e:
            logger.error(f"[RedBlueTeam] Failed: {e}", exc_info=True)
            return WorkflowResult(
                thread=thread, messages=all_messages,
                success=False, error=str(e),
            )
