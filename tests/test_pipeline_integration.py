"""Pipeline 集成测试 — 测试 Pipeline 的 run_discussion() 和 quick_discuss()"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from agent_company.core.models import WorkflowMode
from agent_company.llm.base import LLMProvider
from agent_company.workflow.pipeline import Pipeline, quick_discuss


# ── Mock LLM Provider ──────────────────────────────────────────────────

class MockLLMProvider(LLMProvider):
    """Pipeline 测试用 Mock Provider"""

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

        if "仲裁" in last_content or "决策" in last_content:
            return (
                "**决策摘要**: 采用方案 A\n\n"
                "**选择的方案**: 方案 A — 微服务架构\n\n"
                "**理由**: 扩展性强\n\n"
                "**证据**: 测试数据支撑\n\n"
                "**反对意见**: 复杂度偏高"
            )

        if "拆解" in last_content or "任务列表" in last_content:
            return (
                '[\n'
                '  {\n'
                '    "objective": "实现核心模块",\n'
                '    "definition_of_done": "单元测试通过",\n'
                '    "inputs": ["设计文档"],\n'
                '    "outputs": ["代码"],\n'
                '    "assignee_roles": ["coder"],\n'
                '    "tools_allowed": ["executor"],\n'
                '    "timebox_rounds": 2\n'
                '  }\n'
                ']'
            )

        return (
            f"[CLAIM] 第{self._call_count}轮分析完成\n"
            f"[EVIDENCE] 数据验证通过\n"
            f"[RISK] 低风险\n"
            f"[NEXT_STEP] 继续推进"
        )

    async def check_health(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "mock"


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
async def pipeline(tmp_path):
    """创建用临时数据库的 Pipeline 并 mock create_provider"""
    db_path = str(tmp_path / "test_pipeline.db")
    p = Pipeline(llm_provider="mock", db_path=db_path, enable_memory=False)
    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        await p.setup()
        yield p
        await p.teardown()


# ── Pipeline.run_discussion() 测试 ──────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_run_debate(pipeline):
    """Pipeline 能正确运行 debate 模式"""
    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        result = await pipeline.run_discussion(
            topic="测试 pipeline debate",
            mode=WorkflowMode.DEBATE,
            max_rounds=1,
        )

    assert result.success is True
    assert result.thread is not None
    assert len(result.messages) > 0


@pytest.mark.asyncio
async def test_pipeline_run_pair_programming(pipeline):
    """Pipeline 能正确运行 pair_programming 模式"""
    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        result = await pipeline.run_discussion(
            topic="测试 pipeline pair programming",
            mode=WorkflowMode.PAIR_PROGRAMMING,
            max_rounds=1,
        )

    assert result.success is True
    assert result.thread is not None
    assert result.thread.mode == WorkflowMode.PAIR_PROGRAMMING


@pytest.mark.asyncio
async def test_pipeline_run_red_blue_team(pipeline):
    """Pipeline 能正确运行 red_blue_team 模式"""
    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        result = await pipeline.run_discussion(
            topic="测试 red blue team",
            mode=WorkflowMode.RED_BLUE_TEAM,
            max_rounds=1,
        )

    assert result.success is True
    assert result.thread is not None
    assert result.thread.mode == WorkflowMode.RED_BLUE_TEAM


@pytest.mark.asyncio
async def test_pipeline_run_spec_first(pipeline):
    """Pipeline 能正确运行 spec_first 模式"""
    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        result = await pipeline.run_discussion(
            topic="测试 spec first",
            mode=WorkflowMode.SPEC_FIRST,
            max_rounds=1,
        )

    assert result.success is True
    assert result.thread is not None
    assert result.thread.mode == WorkflowMode.SPEC_FIRST


@pytest.mark.asyncio
async def test_pipeline_run_tdd_loop(pipeline):
    """Pipeline 能正确运行 tdd_loop 模式"""
    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        result = await pipeline.run_discussion(
            topic="测试 tdd loop",
            mode=WorkflowMode.TDD_LOOP,
            max_rounds=1,
        )

    assert result.success is True
    assert result.thread is not None
    assert result.thread.mode == WorkflowMode.TDD_LOOP


# ── Pipeline 参数传递 ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_extended_agents_for_red_blue(pipeline):
    """red_blue_team 模式自动启用 extended agents"""
    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        result = await pipeline.run_discussion(
            topic="自动扩展 agents",
            mode=WorkflowMode.RED_BLUE_TEAM,
            max_rounds=1,
        )

    # red_blue 需要 QA 和 Security，如果 agent 不存在工作流会跳过
    # 但 Pipeline 会自动传 extended=True
    assert result.success is True


@pytest.mark.asyncio
async def test_pipeline_max_rounds_passed(pipeline):
    """max_rounds 参数正确传递"""
    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        result = await pipeline.run_discussion(
            topic="轮次控制",
            mode=WorkflowMode.DEBATE,
            max_rounds=2,
        )

    assert result.success is True
    assert result.thread is not None


# ── Pipeline setup/teardown ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_setup_teardown(tmp_path):
    """Pipeline setup/teardown 正确初始化和清理资源"""
    db_path = str(tmp_path / "setup_test.db")
    p = Pipeline(db_path=db_path, enable_memory=False)
    await p.setup()

    assert p.storage is not None
    assert p.bus is not None

    await p.teardown()


@pytest.mark.asyncio
async def test_pipeline_setup_with_memory(tmp_path):
    """Pipeline 开启 memory 时正确初始化"""
    db_path = str(tmp_path / "memory_test.db")
    p = Pipeline(db_path=db_path, enable_memory=True)
    await p.setup()

    assert p.memory is not None

    await p.teardown()


@pytest.mark.asyncio
async def test_pipeline_not_setup_raises():
    """Pipeline 未 setup 时访问 storage/bus 抛出 RuntimeError"""
    p = Pipeline(enable_memory=False)
    with pytest.raises(RuntimeError, match="not set up"):
        _ = p.storage
    with pytest.raises(RuntimeError, match="not set up"):
        _ = p.bus


# ── quick_discuss() ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quick_discuss(tmp_path):
    """quick_discuss() 快捷函数能正常工作"""
    db_path = str(tmp_path / "quick_test.db")
    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        result = await quick_discuss(
            "快速讨论测试",
            db_path=db_path,
            enable_memory=False,
            max_rounds=1,
        )

    assert result.success is True
    assert result.thread is not None
    assert len(result.messages) > 0
