"""Debate → Synthesize 工作流 — MVP 默认协作模式

流程：
1. Moderator 开场，宣布主题和规则
2. Idea Agent 提出需求分析
3. Architect Agent 提出架构方案
4. Reviewer Agent 质疑和审查
5. 多轮讨论（最多 max_rounds 轮）
6. Judge 仲裁决策
7. Planner 拆解任务
8. Coder 执行实现
"""

from __future__ import annotations

import logging
from typing import Any

from ..agents.base import BaseAgent
from ..core.message_bus import MessageBus
from ..core.models import (
    Message,
    Role,
    Thread,
    ThreadStatus,
    WorkflowMode,
)
from ..core.storage import Storage
from ..core.thread import ThreadManager
from ..llm.base import LLMProvider
from ..orchestration.judge import Judge
from ..orchestration.moderator import Moderator
from ..orchestration.planner import Planner
from ..orchestration.state_machine import Phase, StateMachine
from .base import BaseWorkflow, WorkflowResult

logger = logging.getLogger(__name__)


class DebateWorkflow(BaseWorkflow):
    """Debate → Synthesize 工作流"""

    def __init__(
        self,
        agents: list[BaseAgent],
        llm: LLMProvider,
        bus: MessageBus,
        storage: Storage,
    ):
        self.agents = {a.role: a for a in agents}
        self.llm = llm
        self.bus = bus
        self.storage = storage
        self.thread_mgr = ThreadManager(bus, storage)
        self.moderator = Moderator(bus)
        self.judge = Judge(llm)
        self.planner = Planner(llm)
        self.state_machine = StateMachine()

    @property
    def name(self) -> str:
        return "debate"

    async def run(
        self, thread: Thread | None = None, topic: str = "", **kwargs: Any,
    ) -> WorkflowResult:
        """执行完整的 Debate → Synthesize 工作流"""
        max_rounds = kwargs.get("max_rounds", 3)

        # 创建线程
        if thread is None:
            thread = await self.thread_mgr.create_thread(
                topic=topic, mode=WorkflowMode.DEBATE, max_rounds=max_rounds,
            )

        all_messages: list[Message] = []

        try:
            # Phase 1: 开场
            self.state_machine.transition(Phase.COLLECTING_VIEWS)
            await self.thread_mgr.update_status(thread.id, ThreadStatus.DISCUSSING)
            opening = await self.moderator.open_discussion(thread)
            all_messages.append(opening)
            await self.storage.save_message(opening)

            # Phase 2: 收集初始观点
            initial_instruction = f"请针对以下主题发表你的观点：\n{topic}"
            for role in [Role.IDEA, Role.ARCHITECT, Role.CODER]:
                agent = self.agents.get(role)
                if agent:
                    msg = self._ensure_content(await agent.respond(
                        thread.id, all_messages, extra_instruction=initial_instruction,
                    ))
                    all_messages.append(msg)
                    await self.storage.save_message(msg)

            # Phase 3: 多轮质疑
            self.state_machine.transition(Phase.CHALLENGING)
            for round_num in range(1, max_rounds + 1):
                thread.current_round = round_num
                round_msg = await self.moderator.announce_round(thread, round_num)
                all_messages.append(round_msg)
                await self.storage.save_message(round_msg)

                challenge_instruction = (
                    "请针对其他角色的观点进行质疑或补充。\n"
                    "必须回答：1) 我解决了什么？ 2) 还缺什么证据？"
                )

                # Reviewer 质疑
                reviewer = self.agents.get(Role.REVIEWER)
                if reviewer:
                    msg = self._ensure_content(await reviewer.respond(
                        thread.id, all_messages, extra_instruction=challenge_instruction,
                    ))
                    all_messages.append(msg)
                    await self.storage.save_message(msg)

                # 其他角色回应
                for role in [Role.ARCHITECT, Role.CODER]:
                    agent = self.agents.get(role)
                    if agent:
                        msg = self._ensure_content(await agent.respond(
                            thread.id, all_messages, extra_instruction="请回应质疑并补充证据。",
                        ))
                        all_messages.append(msg)
                        await self.storage.save_message(msg)

            # Phase 4: 决策
            self.state_machine.transition(Phase.DECIDING)
            conclude_msg = await self.moderator.conclude_discussion(thread)
            all_messages.append(conclude_msg)
            await self.storage.save_message(conclude_msg)

            await self.thread_mgr.update_status(thread.id, ThreadStatus.DECIDING)
            agent_weights = {a.id: a.config.weight for a in self.agents.values()}
            decision = await self.judge.arbitrate(thread.id, all_messages, agent_weights)
            await self.storage.save_decision(decision)

            # Phase 5: 任务拆解
            self.state_machine.transition(Phase.PLANNING)
            tasks = await self.planner.decompose(
                thread.id, all_messages, decision.summary,
            )
            for task in tasks:
                await self.storage.save_task(task)

            # Phase 6: 完成
            self.state_machine.transition(Phase.EXECUTING)
            self.state_machine.transition(Phase.REVIEWING)
            self.state_machine.transition(Phase.COMPLETED)
            await self.thread_mgr.update_status(thread.id, ThreadStatus.CLOSED)

            return WorkflowResult(
                thread=thread,
                messages=all_messages,
                decision=decision,
                tasks=tasks,
                success=True,
            )

        except Exception as e:
            logger.error(f"[DebateWorkflow] Failed: {e}", exc_info=True)
            return WorkflowResult(
                thread=thread,
                messages=all_messages,
                success=False,
                error=str(e),
            )
