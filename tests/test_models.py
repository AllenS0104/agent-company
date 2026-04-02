"""测试核心数据模型"""

from agent_company.core.models import (
    AgentConfig,
    Decision,
    DecisionStatus,
    EvidenceBlock,
    Message,
    Role,
    TaskCard,
    TaskStatus,
    Thread,
    ThreadStatus,
    Vote,
    WorkflowMode,
)


def test_role_enum():
    assert Role.IDEA == "idea"
    assert Role.ARCHITECT == "architect"
    assert Role.CODER == "coder"
    assert Role.REVIEWER == "reviewer"


def test_agent_config():
    config = AgentConfig(name="Test Agent", role=Role.CODER)
    assert config.name == "Test Agent"
    assert config.role == Role.CODER
    assert config.weight == 1.0
    assert config.enabled is True
    assert len(config.id) == 12


def test_evidence_block():
    eb = EvidenceBlock(
        claim="方案A更好",
        evidence="基准测试延迟 20ms",
        risk="内存消耗较高",
        next_step="开始实现",
    )
    assert eb.claim == "方案A更好"
    assert eb.evidence == "基准测试延迟 20ms"


def test_message():
    msg = Message(
        thread_id="t1",
        agent_id="a1",
        agent_role=Role.ARCHITECT,
        content="我建议使用方案A",
        evidence_block=EvidenceBlock(evidence="延迟测试通过"),
    )
    assert msg.has_evidence is True
    assert msg.agent_role == Role.ARCHITECT


def test_message_without_evidence():
    msg = Message(
        thread_id="t1",
        agent_id="a1",
        agent_role=Role.CODER,
        content="我同意",
    )
    assert msg.has_evidence is False


def test_thread():
    thread = Thread(topic="如何设计消息队列", max_rounds=3)
    assert thread.status == ThreadStatus.OPEN
    assert thread.mode == WorkflowMode.DEBATE
    assert thread.current_round == 0


def test_task_card():
    task = TaskCard(
        thread_id="t1",
        objective="实现核心模块",
        definition_of_done="测试通过",
        assignee_roles=[Role.CODER, Role.REVIEWER],
    )
    assert task.status == TaskStatus.PENDING
    assert len(task.assignee_roles) == 2


def test_decision():
    decision = Decision(
        thread_id="t1",
        summary="选择方案A",
        chosen_option="事件驱动架构",
        reasoning="延迟更低",
    )
    assert decision.status == DecisionStatus.DRAFT


def test_vote():
    vote = Vote(
        agent_id="a1",
        agent_role=Role.ARCHITECT,
        choice="方案A",
        weight=1.5,
    )
    assert vote.weight == 1.5
