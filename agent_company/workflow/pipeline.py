"""Pipeline — 完整工作流串联"""

from __future__ import annotations

import logging
from typing import Any

from ..agents.architect import create_architect_agent
from ..agents.coder import create_coder_agent
from ..agents.devops import create_devops_agent
from ..agents.docs import create_docs_agent
from ..agents.idea import create_idea_agent
from ..agents.perf import create_perf_agent
from ..agents.qa import create_qa_agent
from ..agents.reviewer import create_reviewer_agent
from ..agents.security import create_security_agent
from ..config import config
from ..core.message_bus import MessageBus
from ..core.models import WorkflowMode
from ..core.storage import Storage
from ..llm.factory import create_provider
from ..memory.project_memory import MemoryType, ProjectMemory
from .base import WorkflowResult
from .debate import DebateWorkflow

logger = logging.getLogger(__name__)


class Pipeline:
    """工作流 Pipeline — 管理完整的讨论→决策→执行流程"""

    def __init__(
        self,
        llm_provider: str | None = None,
        llm_model: str | None = None,
        db_path: str | None = None,
        enable_memory: bool = True,
    ):
        self.provider_name = llm_provider or config.DEFAULT_LLM_PROVIDER
        self.llm_model = llm_model
        self.db_path = db_path or config.DB_PATH
        self.enable_memory = enable_memory
        self._storage: Storage | None = None
        self._bus: MessageBus | None = None
        self._memory: ProjectMemory | None = None

    async def setup(self) -> None:
        """初始化存储、消息总线和记忆系统"""
        self._storage = Storage(self.db_path)
        await self._storage.connect()
        self._bus = MessageBus()

        if self.enable_memory:
            self._memory = ProjectMemory(self.db_path)
            await self._memory.connect()

    async def teardown(self) -> None:
        """清理资源"""
        if self._storage:
            await self._storage.close()
        if self._memory:
            await self._memory.close()

    @property
    def storage(self) -> Storage:
        if not self._storage:
            raise RuntimeError("Pipeline not set up. Call setup() first.")
        return self._storage

    @property
    def bus(self) -> MessageBus:
        if not self._bus:
            raise RuntimeError("Pipeline not set up. Call setup() first.")
        return self._bus

    @property
    def memory(self) -> ProjectMemory | None:
        return self._memory

    def _create_llm(self):
        kwargs: dict[str, Any] = {}
        if self.llm_model:
            kwargs["model"] = self.llm_model
        return create_provider(self.provider_name, **kwargs)

    def _create_agents(self, llm, extended: bool = False):
        """创建 Agent 列表

        Args:
            extended: True 时包含 QA 和 Security Agent
        """
        agents = [
            create_idea_agent(llm, self.bus),
            create_architect_agent(llm, self.bus),
            create_coder_agent(llm, self.bus),
            create_reviewer_agent(llm, self.bus),
        ]
        if extended:
            agents.extend([
                create_qa_agent(llm, self.bus),
                create_security_agent(llm, self.bus),
                create_devops_agent(llm, self.bus),
                create_docs_agent(llm, self.bus),
                create_perf_agent(llm, self.bus),
            ])
        return agents

    def _create_workflow(self, mode: WorkflowMode, llm, agents):
        """根据模式创建工作流"""
        if mode == WorkflowMode.DEBATE:
            return DebateWorkflow(agents, llm, self.bus, self.storage)

        if mode == WorkflowMode.PAIR_PROGRAMMING:
            from .pair_programming import PairProgrammingWorkflow
            return PairProgrammingWorkflow(
                agents, llm, self.bus, self.storage,
            )

        if mode == WorkflowMode.RED_BLUE_TEAM:
            from .red_blue_team import RedBlueTeamWorkflow
            return RedBlueTeamWorkflow(
                agents, llm, self.bus, self.storage,
            )

        if mode == WorkflowMode.SPEC_FIRST:
            from .spec_first import SpecFirstWorkflow
            return SpecFirstWorkflow(
                agents, llm, self.bus, self.storage,
            )

        if mode == WorkflowMode.TDD_LOOP:
            from .tdd_loop import TDDLoopWorkflow
            return TDDLoopWorkflow(agents, llm, self.bus, self.storage)

        logger.warning(f"Unknown mode '{mode.value}', fallback to debate")
        return DebateWorkflow(agents, llm, self.bus, self.storage)

    async def run_discussion(
        self,
        topic: str,
        mode: WorkflowMode = WorkflowMode.DEBATE,
        max_rounds: int = 3,
        extended_agents: bool = False,
        **kwargs: Any,
    ) -> WorkflowResult:
        """运行一次完整的讨论"""
        llm = self._create_llm()
        needs_extended = extended_agents or mode in (
            WorkflowMode.RED_BLUE_TEAM,
            WorkflowMode.TDD_LOOP,
            WorkflowMode.SPEC_FIRST,
        )
        agents = self._create_agents(llm, extended=needs_extended)
        workflow = self._create_workflow(mode, llm, agents)

        # 讨论开始前：注入历史记忆上下文
        memory_context = ""
        if self._memory:
            try:
                memory_context = await self._memory.recall_for_context(topic=topic)
                if memory_context:
                    kwargs.setdefault("extra_context", memory_context)
            except Exception as exc:
                logger.warning("Failed to recall memory context: %s", exc)

        result = await workflow.run(
            topic=topic, max_rounds=max_rounds, **kwargs,
        )

        # 讨论结束：自动保存决策和讨论摘要到记忆系统
        if self._memory:
            topic_tags = [mode.value]

            if result.success and result.decision:
                await self._memory.store_decision(
                    result.decision, tags=topic_tags,
                )

            # 存储讨论摘要
            try:
                summary_content = (
                    f"讨论主题: {topic}\n"
                    f"模式: {mode.value}\n"
                    f"轮次: {max_rounds}\n"
                    f"结果: {'成功' if result.success else '失败'}"
                )
                if result.decision:
                    summary_content += f"\n决策: {result.decision.summary}"
                await self._memory.store(
                    MemoryType.KNOWLEDGE,
                    summary_content,
                    title=f"讨论摘要: {topic[:60]}",
                    tags=topic_tags + ["discussion_summary"],
                    importance=3,
                )
            except Exception as exc:
                logger.warning("Failed to store discussion summary: %s", exc)

        return result


async def quick_discuss(topic: str, **kwargs: Any) -> WorkflowResult:
    """快速讨论 — 一个函数搞定"""
    _pipeline_keys = {"llm_provider", "llm_model", "db_path", "enable_memory"}
    pipeline_kwargs = {k: v for k, v in kwargs.items() if k in _pipeline_keys}
    discussion_kwargs = {k: v for k, v in kwargs.items() if k not in _pipeline_keys}

    pipeline = Pipeline(**pipeline_kwargs)
    await pipeline.setup()
    try:
        return await pipeline.run_discussion(topic, **discussion_kwargs)
    finally:
        await pipeline.teardown()
