"""工作流集成测试 — 用 Mock LLM Provider 测试 5 种工作流的完整执行"""

from __future__ import annotations

import pytest

from agent_company.agents.architect import create_architect_agent
from agent_company.agents.coder import create_coder_agent
from agent_company.agents.idea import create_idea_agent
from agent_company.agents.qa import create_qa_agent
from agent_company.agents.reviewer import create_reviewer_agent
from agent_company.agents.security import create_security_agent
from agent_company.core.message_bus import MessageBus
from agent_company.core.models import ThreadStatus, WorkflowMode
from agent_company.core.storage import Storage
from agent_company.llm.base import LLMProvider


# ── Mock LLM Provider ──────────────────────────────────────────────────

class MockLLMProvider(LLMProvider):
    """返回预设响应的 Mock Provider，格式能被 protocols.py 正确解析"""

    def __init__(self, model: str | None = "mock-model", **kwargs):
        super().__init__(model=model, **kwargs)
        self._call_count = 0

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> str:
        self._call_count += 1
        last_content = messages[-1].get("content", "") if messages else ""

        # Judge 仲裁 — 返回带标记段落的决策
        if "仲裁" in last_content or "决策" in last_content:
            return (
                "**决策摘要**: 采用微服务架构方案\n\n"
                "**选择的方案**: 基于 FastAPI 的微服务方案 A\n\n"
                "**理由**: 该方案有明确的证据支撑，扩展性好\n\n"
                "**证据**: 基准测试显示方案A性能优30%\n\n"
                "**反对意见**: 运维复杂度较高，需要额外监控"
            )

        # Planner 拆解任务 — 返回 JSON 任务列表
        if "拆解" in last_content or "任务列表" in last_content:
            return (
                '```json\n'
                '[\n'
                '  {\n'
                '    "objective": "搭建项目骨架",\n'
                '    "definition_of_done": "项目可启动并通过冒烟测试",\n'
                '    "inputs": ["架构设计文档"],\n'
                '    "outputs": ["项目代码仓库"],\n'
                '    "assignee_roles": ["coder"],\n'
                '    "tools_allowed": ["executor"],\n'
                '    "timebox_rounds": 2\n'
                '  }\n'
                ']\n'
                '```'
            )

        # 带 evidence block 标记的通用响应
        return (
            f"[CLAIM] 第{self._call_count}轮分析：方案可行，建议采用模块化设计\n"
            f"[EVIDENCE] 根据经验数据和基准测试结果验证\n"
            f"[RISK] 集成复杂度中等，需要额外测试\n"
            f"[NEXT_STEP] 进入下一阶段的详细设计和实现"
        )

    async def check_health(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "mock"


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm():
    return MockLLMProvider()


@pytest.fixture
def bus():
    return MessageBus()


@pytest.fixture
async def storage(tmp_path):
    db_path = str(tmp_path / "test_workflow.db")
    s = Storage(db_path)
    await s.connect()
    yield s
    await s.close()


def _create_basic_agents(llm, bus):
    """创建基础 4 角色 Agent"""
    return [
        create_idea_agent(llm, bus),
        create_architect_agent(llm, bus),
        create_coder_agent(llm, bus),
        create_reviewer_agent(llm, bus),
    ]


def _create_extended_agents(llm, bus):
    """创建扩展 6 角色 Agent（含 QA + Security）"""
    return _create_basic_agents(llm, bus) + [
        create_qa_agent(llm, bus),
        create_security_agent(llm, bus),
    ]


# ── Debate Workflow ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_debate_workflow_completes(mock_llm, bus, storage):
    """Debate 工作流能正常启动并完成"""
    from agent_company.workflow.debate import DebateWorkflow

    agents = _create_basic_agents(mock_llm, bus)
    wf = DebateWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="设计一个缓存系统", max_rounds=1)

    assert result.success is True
    assert result.error == ""


@pytest.mark.asyncio
async def test_debate_workflow_result_structure(mock_llm, bus, storage):
    """Debate 工作流返回完整的 WorkflowResult"""
    from agent_company.workflow.debate import DebateWorkflow

    agents = _create_basic_agents(mock_llm, bus)
    wf = DebateWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="API 网关设计", max_rounds=1)

    # WorkflowResult 包含 thread
    assert result.thread is not None
    assert result.thread.topic == "API 网关设计"
    assert result.thread.mode == WorkflowMode.DEBATE

    # 包含 messages
    assert len(result.messages) > 0

    # 包含 decision（debate 有 judge）
    assert result.decision is not None
    assert result.decision.summary != ""

    # 包含 tasks（debate 有 planner）
    assert len(result.tasks) > 0


@pytest.mark.asyncio
async def test_debate_workflow_messages_saved(mock_llm, bus, storage):
    """Debate 工作流的消息被正确保存到存储"""
    from agent_company.workflow.debate import DebateWorkflow

    agents = _create_basic_agents(mock_llm, bus)
    wf = DebateWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="日志系统", max_rounds=1)

    saved_messages = await storage.get_thread_messages(result.thread.id)
    assert len(saved_messages) > 0
    # 保存的消息数应等于返回的消息数
    assert len(saved_messages) == len(result.messages)


@pytest.mark.asyncio
async def test_debate_workflow_thread_closed(mock_llm, bus, storage):
    """Debate 工作流完成后 Thread 状态更新为 closed"""
    from agent_company.workflow.debate import DebateWorkflow

    agents = _create_basic_agents(mock_llm, bus)
    wf = DebateWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="数据库选型", max_rounds=1)

    loaded_thread = await storage.get_thread(result.thread.id)
    assert loaded_thread is not None
    assert loaded_thread.status == ThreadStatus.CLOSED


# ── Pair Programming Workflow ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_pair_programming_workflow_completes(mock_llm, bus, storage):
    """Pair Programming 工作流能正常启动并完成"""
    from agent_company.workflow.pair_programming import PairProgrammingWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = PairProgrammingWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="实现用户认证模块", max_rounds=1)

    assert result.success is True
    assert result.error == ""


@pytest.mark.asyncio
async def test_pair_programming_result_structure(mock_llm, bus, storage):
    """Pair Programming 返回包含 thread 和 messages 的结果"""
    from agent_company.workflow.pair_programming import PairProgrammingWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = PairProgrammingWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="编写排序算法", max_rounds=1)

    assert result.thread is not None
    assert result.thread.topic == "编写排序算法"
    assert result.thread.mode == WorkflowMode.PAIR_PROGRAMMING
    assert len(result.messages) > 0
    # pair_programming 没有 judge，decision 为 None
    assert result.decision is None


@pytest.mark.asyncio
async def test_pair_programming_messages_saved(mock_llm, bus, storage):
    """Pair Programming 消息被正确保存"""
    from agent_company.workflow.pair_programming import PairProgrammingWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = PairProgrammingWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="实现队列", max_rounds=1)

    saved = await storage.get_thread_messages(result.thread.id)
    assert len(saved) == len(result.messages)


@pytest.mark.asyncio
async def test_pair_programming_thread_closed(mock_llm, bus, storage):
    """Pair Programming 完成后线程关闭"""
    from agent_company.workflow.pair_programming import PairProgrammingWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = PairProgrammingWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="实现栈", max_rounds=1)

    loaded = await storage.get_thread(result.thread.id)
    assert loaded is not None
    assert loaded.status == ThreadStatus.CLOSED


# ── Red/Blue Team Workflow ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_red_blue_team_workflow_completes(mock_llm, bus, storage):
    """Red/Blue Team 工作流能正常完成"""
    from agent_company.workflow.red_blue_team import RedBlueTeamWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = RedBlueTeamWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="安全认证方案评审", max_rounds=1)

    assert result.success is True
    assert result.error == ""


@pytest.mark.asyncio
async def test_red_blue_team_result_structure(mock_llm, bus, storage):
    """Red/Blue Team 返回包含 decision 的结果"""
    from agent_company.workflow.red_blue_team import RedBlueTeamWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = RedBlueTeamWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="评审支付系统", max_rounds=1)

    assert result.thread is not None
    assert result.thread.mode == WorkflowMode.RED_BLUE_TEAM
    assert len(result.messages) > 0
    # red_blue_team 有 judge
    assert result.decision is not None


@pytest.mark.asyncio
async def test_red_blue_team_messages_saved(mock_llm, bus, storage):
    """Red/Blue Team 消息正确保存"""
    from agent_company.workflow.red_blue_team import RedBlueTeamWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = RedBlueTeamWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="渗透测试", max_rounds=1)

    saved = await storage.get_thread_messages(result.thread.id)
    assert len(saved) == len(result.messages)


@pytest.mark.asyncio
async def test_red_blue_team_thread_closed(mock_llm, bus, storage):
    """Red/Blue Team 完成后线程关闭"""
    from agent_company.workflow.red_blue_team import RedBlueTeamWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = RedBlueTeamWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="安全审计", max_rounds=1)

    loaded = await storage.get_thread(result.thread.id)
    assert loaded is not None
    assert loaded.status == ThreadStatus.CLOSED


# ── Spec First Workflow ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_spec_first_workflow_completes(mock_llm, bus, storage):
    """Spec-first 工作流能正常完成"""
    from agent_company.workflow.spec_first import SpecFirstWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = SpecFirstWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="设计 REST API 接口", max_rounds=1)

    assert result.success is True
    assert result.error == ""


@pytest.mark.asyncio
async def test_spec_first_result_structure(mock_llm, bus, storage):
    """Spec-first 返回包含 thread 和 messages 的结果"""
    from agent_company.workflow.spec_first import SpecFirstWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = SpecFirstWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="定义 gRPC 接口", max_rounds=1)

    assert result.thread is not None
    assert result.thread.mode == WorkflowMode.SPEC_FIRST
    assert len(result.messages) > 0
    # spec_first 没有 judge
    assert result.decision is None


@pytest.mark.asyncio
async def test_spec_first_messages_saved(mock_llm, bus, storage):
    """Spec-first 消息正确保存"""
    from agent_company.workflow.spec_first import SpecFirstWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = SpecFirstWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="接口定义", max_rounds=1)

    saved = await storage.get_thread_messages(result.thread.id)
    assert len(saved) == len(result.messages)


@pytest.mark.asyncio
async def test_spec_first_thread_closed(mock_llm, bus, storage):
    """Spec-first 完成后线程关闭"""
    from agent_company.workflow.spec_first import SpecFirstWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = SpecFirstWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="协议设计", max_rounds=1)

    loaded = await storage.get_thread(result.thread.id)
    assert loaded is not None
    assert loaded.status == ThreadStatus.CLOSED


# ── TDD Loop Workflow ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tdd_loop_workflow_completes(mock_llm, bus, storage):
    """TDD Loop 工作流能正常完成"""
    from agent_company.workflow.tdd_loop import TDDLoopWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = TDDLoopWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="实现字符串处理工具", max_rounds=1)

    assert result.success is True
    assert result.error == ""


@pytest.mark.asyncio
async def test_tdd_loop_result_structure(mock_llm, bus, storage):
    """TDD Loop 返回包含 thread 和 messages 的结果"""
    from agent_company.workflow.tdd_loop import TDDLoopWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = TDDLoopWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="实现解析器", max_rounds=1)

    assert result.thread is not None
    assert result.thread.mode == WorkflowMode.TDD_LOOP
    assert len(result.messages) > 0
    # tdd_loop 没有 judge
    assert result.decision is None


@pytest.mark.asyncio
async def test_tdd_loop_messages_saved(mock_llm, bus, storage):
    """TDD Loop 消息正确保存"""
    from agent_company.workflow.tdd_loop import TDDLoopWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = TDDLoopWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="实现验证器", max_rounds=1)

    saved = await storage.get_thread_messages(result.thread.id)
    assert len(saved) == len(result.messages)


@pytest.mark.asyncio
async def test_tdd_loop_thread_closed(mock_llm, bus, storage):
    """TDD Loop 完成后线程关闭"""
    from agent_company.workflow.tdd_loop import TDDLoopWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = TDDLoopWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="实现计算器", max_rounds=1)

    loaded = await storage.get_thread(result.thread.id)
    assert loaded is not None
    assert loaded.status == ThreadStatus.CLOSED


# ── 跨工作流共性验证 ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_all_workflows_have_system_messages(mock_llm, bus, storage):
    """所有工作流都包含 Moderator 的系统消息"""
    from agent_company.core.models import MessageType
    from agent_company.workflow.debate import DebateWorkflow

    agents = _create_basic_agents(mock_llm, bus)
    wf = DebateWorkflow(agents, mock_llm, bus, storage)
    result = await wf.run(topic="系统消息验证", max_rounds=1)

    system_msgs = [m for m in result.messages if m.msg_type == MessageType.SYSTEM]
    assert len(system_msgs) >= 1, "至少应有开场系统消息"


@pytest.mark.asyncio
async def test_workflow_multiple_rounds(mock_llm, bus, storage):
    """工作流支持多轮讨论"""
    from agent_company.workflow.tdd_loop import TDDLoopWorkflow

    agents = _create_extended_agents(mock_llm, bus)
    wf = TDDLoopWorkflow(agents, mock_llm, bus, storage)

    result_1round = await wf.run(topic="多轮测试-1轮", max_rounds=1)

    # 重新创建工作流（state machine 需要 reset）
    bus2 = MessageBus()
    storage2_path = str(storage.db_path).replace(".db", "_2.db")
    storage2 = Storage(storage2_path)
    await storage2.connect()
    agents2 = _create_extended_agents(mock_llm, bus2)
    wf2 = TDDLoopWorkflow(agents2, mock_llm, bus2, storage2)
    result_2round = await wf2.run(topic="多轮测试-2轮", max_rounds=2)
    await storage2.close()

    assert len(result_2round.messages) > len(result_1round.messages)
