"""测试新增的 3 个 Agent 角色：DevOps / Docs / Performance"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_company.agents.devops import DEFAULT_DEVOPS_PROMPT, create_devops_agent
from agent_company.agents.docs import DEFAULT_DOCS_PROMPT, create_docs_agent
from agent_company.agents.perf import DEFAULT_PERF_PROMPT, create_perf_agent
from agent_company.core.models import Role


# ── fixtures ──

@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="[CLAIM] test [EVIDENCE] ok [RISK] none [NEXT] done")
    return llm


@pytest.fixture
def mock_bus():
    bus = MagicMock()
    bus.publish = AsyncMock()
    return bus


# ── Role 枚举测试 ──

class TestRoleEnum:
    def test_devops_role_value(self):
        assert Role.DEVOPS == "devops"
        assert Role.DEVOPS.value == "devops"

    def test_docs_role_value(self):
        assert Role.DOCS == "docs"
        assert Role.DOCS.value == "docs"

    def test_perf_role_value(self):
        assert Role.PERF == "perf"
        assert Role.PERF.value == "perf"

    def test_new_roles_in_enum(self):
        all_values = [r.value for r in Role]
        assert "devops" in all_values
        assert "docs" in all_values
        assert "perf" in all_values


# ── Agent 创建测试 ──

class TestAgentCreation:
    def test_create_devops_agent(self, mock_llm, mock_bus):
        agent = create_devops_agent(mock_llm, mock_bus)
        assert agent.role == Role.DEVOPS
        assert agent.name == "DevOps Agent"
        assert agent.config.weight == 1.2

    def test_create_docs_agent(self, mock_llm, mock_bus):
        agent = create_docs_agent(mock_llm, mock_bus)
        assert agent.role == Role.DOCS
        assert agent.name == "Docs Agent"
        assert agent.config.weight == 1.0

    def test_create_perf_agent(self, mock_llm, mock_bus):
        agent = create_perf_agent(mock_llm, mock_bus)
        assert agent.role == Role.PERF
        assert agent.name == "Performance Agent"
        assert agent.config.weight == 1.2

    def test_custom_system_prompt(self, mock_llm, mock_bus):
        custom = "自定义提示词"
        agent = create_devops_agent(mock_llm, mock_bus, system_prompt=custom)
        assert agent.config.system_prompt == custom


# ── System Prompt 关键词测试 ──

class TestSystemPrompts:
    def test_devops_prompt_keywords(self):
        keywords = ["CI/CD", "容器化", "基础设施", "监控", "部署策略", "回滚"]
        for kw in keywords:
            assert kw in DEFAULT_DEVOPS_PROMPT, f"DevOps prompt missing keyword: {kw}"

    def test_docs_prompt_keywords(self):
        keywords = ["API 文档", "README", "ADR", "Markdown", "变更日志"]
        for kw in keywords:
            assert kw in DEFAULT_DOCS_PROMPT, f"Docs prompt missing keyword: {kw}"

    def test_perf_prompt_keywords(self):
        keywords = ["性能", "瓶颈", "复杂度", "缓存", "数据库", "负载测试"]
        for kw in keywords:
            assert kw in DEFAULT_PERF_PROMPT, f"Perf prompt missing keyword: {kw}"


# ── Pipeline 集成测试 ──

class TestPipelineIntegration:
    def test_pipeline_imports_new_agents(self):
        """验证 pipeline 能正确导入新 Agent 创建函数"""
        from agent_company.workflow.pipeline import Pipeline
        pipeline = Pipeline.__new__(Pipeline)
        assert hasattr(pipeline, '_create_agents')

    def test_pipeline_creates_extended_agents(self, mock_llm, mock_bus):
        """验证 extended 模式包含新 Agent"""
        from agent_company.workflow.pipeline import Pipeline
        pipeline = Pipeline.__new__(Pipeline)
        pipeline._bus = mock_bus

        agents = pipeline._create_agents(mock_llm, extended=True)
        agent_roles = {a.role for a in agents}

        assert Role.DEVOPS in agent_roles
        assert Role.DOCS in agent_roles
        assert Role.PERF in agent_roles
        assert Role.QA in agent_roles
        assert Role.SECURITY in agent_roles

    def test_pipeline_base_agents_unchanged(self, mock_llm, mock_bus):
        """验证基础 Agent 列表不变"""
        from agent_company.workflow.pipeline import Pipeline
        pipeline = Pipeline.__new__(Pipeline)
        pipeline._bus = mock_bus

        agents = pipeline._create_agents(mock_llm, extended=False)
        agent_roles = {a.role for a in agents}

        assert Role.IDEA in agent_roles
        assert Role.ARCHITECT in agent_roles
        assert Role.CODER in agent_roles
        assert Role.REVIEWER in agent_roles
        assert Role.DEVOPS not in agent_roles


# ── __init__.py 注册测试 ──

class TestAgentRegistration:
    def test_all_create_functions_importable(self):
        from agent_company.agents import (
            create_devops_agent,
            create_docs_agent,
            create_perf_agent,
        )
        assert callable(create_devops_agent)
        assert callable(create_docs_agent)
        assert callable(create_perf_agent)
