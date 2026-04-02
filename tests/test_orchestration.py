"""测试状态机"""

import pytest

from agent_company.orchestration.state_machine import Phase, StateMachine


def test_initial_state():
    sm = StateMachine()
    assert sm.phase == Phase.INIT
    assert not sm.is_terminal


def test_valid_transition():
    sm = StateMachine()
    sm.transition(Phase.COLLECTING_VIEWS)
    assert sm.phase == Phase.COLLECTING_VIEWS


def test_invalid_transition():
    sm = StateMachine()
    with pytest.raises(ValueError):
        sm.transition(Phase.EXECUTING)


def test_full_lifecycle():
    sm = StateMachine()
    sm.transition(Phase.COLLECTING_VIEWS)
    sm.transition(Phase.CHALLENGING)
    sm.transition(Phase.DECIDING)
    sm.transition(Phase.PLANNING)
    sm.transition(Phase.EXECUTING)
    sm.transition(Phase.REVIEWING)
    sm.transition(Phase.COMPLETED)
    assert sm.is_terminal


def test_reset():
    sm = StateMachine()
    sm.transition(Phase.COLLECTING_VIEWS)
    sm.reset()
    assert sm.phase == Phase.INIT


def test_review_can_loop_back():
    sm = StateMachine()
    sm.transition(Phase.COLLECTING_VIEWS)
    sm.transition(Phase.CHALLENGING)
    sm.transition(Phase.DECIDING)
    sm.transition(Phase.PLANNING)
    sm.transition(Phase.EXECUTING)
    sm.transition(Phase.REVIEWING)
    # 审查不通过，回到执行
    sm.transition(Phase.EXECUTING)
    assert sm.phase == Phase.EXECUTING
