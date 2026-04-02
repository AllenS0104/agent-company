"""Agent Company 核心数据模型与消息协议"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ──────────────────────────────────────────────
# 角色枚举
# ──────────────────────────────────────────────

class Role(str, Enum):
    """Agent 角色枚举（9种角色 + 3种调度角色）"""
    # 工作角色
    IDEA = "idea"
    ARCHITECT = "architect"
    CODER = "coder"
    REVIEWER = "reviewer"
    QA = "qa"
    SECURITY = "security"
    DEVOPS = "devops"
    PERF = "perf"
    DOCS = "docs"
    # 调度角色
    PLANNER = "planner"
    MODERATOR = "moderator"
    JUDGE = "judge"


class ThreadStatus(str, Enum):
    OPEN = "open"
    DISCUSSING = "discussing"
    DECIDING = "deciding"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    CLOSED = "closed"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    BLOCKED = "blocked"


class DecisionStatus(str, Enum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class MessageType(str, Enum):
    PROPOSAL = "proposal"
    CHALLENGE = "challenge"
    RESPONSE = "response"
    EVIDENCE = "evidence"
    DECISION = "decision"
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    SYSTEM = "system"


class ArtifactType(str, Enum):
    CODE = "code"
    TEST_REPORT = "test_report"
    ADR = "adr"
    RISK_LIST = "risk_list"
    README = "readme"
    DOCUMENT = "document"


class WorkflowMode(str, Enum):
    DEBATE = "debate"
    PAIR_PROGRAMMING = "pair_programming"
    RED_BLUE_TEAM = "red_blue_team"
    SPEC_FIRST = "spec_first"
    TDD_LOOP = "tdd_loop"


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now() -> datetime:
    return datetime.now()


# ──────────────────────────────────────────────
# 核心实体
# ──────────────────────────────────────────────

class AgentConfig(BaseModel):
    """Agent 配置"""
    id: str = Field(default_factory=new_id)
    name: str
    role: Role
    system_prompt: str = ""
    weight: float = 1.0  # 仲裁投票权重
    enabled: bool = True
    llm_provider: str | None = None  # 可指定不同 provider
    llm_model: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class EvidenceBlock(BaseModel):
    """证据优先协议：每条消息必须包含的结构化输出"""
    claim: str = ""          # 主张
    evidence: str = ""       # 证据（测试结果/日志/基准/推导）
    risk: str = ""           # 风险
    next_step: str = ""      # 下一步建议


class Message(BaseModel):
    """消息"""
    id: str = Field(default_factory=new_id)
    thread_id: str
    agent_id: str
    agent_role: Role
    content: str
    msg_type: MessageType = MessageType.RESPONSE
    evidence_block: EvidenceBlock | None = None
    timestamp: datetime = Field(default_factory=now)

    @property
    def has_evidence(self) -> bool:
        return self.evidence_block is not None and bool(self.evidence_block.evidence)


class Thread(BaseModel):
    """讨论线程"""
    id: str = Field(default_factory=new_id)
    topic: str
    mode: WorkflowMode = WorkflowMode.DEBATE
    status: ThreadStatus = ThreadStatus.OPEN
    max_rounds: int = 3
    current_round: int = 0
    created_at: datetime = Field(default_factory=now)
    messages: list[Message] = Field(default_factory=list)


class TaskCard(BaseModel):
    """任务卡片（Orchestrator 下发的可执行任务）"""
    id: str = Field(default_factory=new_id)
    thread_id: str
    decision_id: str | None = None
    objective: str
    definition_of_done: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    assignee_roles: list[Role] = Field(default_factory=list)
    tools_allowed: list[str] = Field(default_factory=list)
    timebox_rounds: int = 3
    status: TaskStatus = TaskStatus.PENDING
    result: str = ""
    created_at: datetime = Field(default_factory=now)


class Artifact(BaseModel):
    """产出物（代码/测试报告/ADR/风险清单等）"""
    id: str = Field(default_factory=new_id)
    task_id: str | None = None
    thread_id: str | None = None
    artifact_type: ArtifactType
    title: str = ""
    content: str = ""
    file_path: str | None = None
    created_at: datetime = Field(default_factory=now)


class Decision(BaseModel):
    """决策记录"""
    id: str = Field(default_factory=new_id)
    thread_id: str
    summary: str
    options: list[str] = Field(default_factory=list)
    chosen_option: str = ""
    reasoning: str = ""
    evidence: list[str] = Field(default_factory=list)
    dissent: list[str] = Field(default_factory=list)  # 反对意见
    status: DecisionStatus = DecisionStatus.DRAFT
    created_at: datetime = Field(default_factory=now)


class Vote(BaseModel):
    """投票（用于仲裁）"""
    agent_id: str
    agent_role: Role
    choice: str
    weight: float = 1.0
    reasoning: str = ""
