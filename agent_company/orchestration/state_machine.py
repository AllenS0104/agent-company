"""流程状态机 — 控制讨论→决策→执行的完整生命周期"""

from __future__ import annotations

import logging
from enum import Enum

from ..core.models import ThreadStatus

logger = logging.getLogger(__name__)


class Phase(str, Enum):
    """工作流阶段"""
    INIT = "init"
    COLLECTING_VIEWS = "collecting_views"
    CHALLENGING = "challenging"
    DECIDING = "deciding"
    PLANNING = "planning"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    FAILED = "failed"


# 合法的状态转移
_TRANSITIONS: dict[Phase, list[Phase]] = {
    Phase.INIT: [Phase.COLLECTING_VIEWS],
    Phase.COLLECTING_VIEWS: [Phase.CHALLENGING, Phase.DECIDING],
    Phase.CHALLENGING: [Phase.COLLECTING_VIEWS, Phase.DECIDING],
    Phase.DECIDING: [Phase.PLANNING, Phase.COLLECTING_VIEWS],  # 决策不通过可以重新讨论
    Phase.PLANNING: [Phase.EXECUTING],
    Phase.EXECUTING: [Phase.REVIEWING, Phase.FAILED],
    Phase.REVIEWING: [Phase.COMPLETED, Phase.EXECUTING],  # 审查不通过可以重新执行
    Phase.COMPLETED: [],
    Phase.FAILED: [Phase.INIT],  # 可以重启
}

# Phase 到 ThreadStatus 的映射
_PHASE_TO_STATUS: dict[Phase, ThreadStatus] = {
    Phase.INIT: ThreadStatus.OPEN,
    Phase.COLLECTING_VIEWS: ThreadStatus.DISCUSSING,
    Phase.CHALLENGING: ThreadStatus.DISCUSSING,
    Phase.DECIDING: ThreadStatus.DECIDING,
    Phase.PLANNING: ThreadStatus.DECIDING,
    Phase.EXECUTING: ThreadStatus.EXECUTING,
    Phase.REVIEWING: ThreadStatus.REVIEWING,
    Phase.COMPLETED: ThreadStatus.CLOSED,
    Phase.FAILED: ThreadStatus.CLOSED,
}


class StateMachine:
    """讨论流程状态机"""

    def __init__(self):
        self._phase = Phase.INIT

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def thread_status(self) -> ThreadStatus:
        return _PHASE_TO_STATUS[self._phase]

    def can_transition(self, target: Phase) -> bool:
        return target in _TRANSITIONS.get(self._phase, [])

    def transition(self, target: Phase) -> None:
        if not self.can_transition(target):
            allowed = _TRANSITIONS.get(self._phase, [])
            raise ValueError(
                f"Cannot transition from {self._phase.value} to {target.value}. "
                f"Allowed: {[p.value for p in allowed]}"
            )
        logger.info(f"[StateMachine] {self._phase.value} → {target.value}")
        self._phase = target

    @property
    def is_terminal(self) -> bool:
        return self._phase in (Phase.COMPLETED, Phase.FAILED)

    def reset(self) -> None:
        self._phase = Phase.INIT
