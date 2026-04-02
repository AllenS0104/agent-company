"""API 路由集成测试 — 用 FastAPI TestClient 测试 API 端点"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from agent_company.api.server import app
from agent_company.core.models import (
    Decision,
    DecisionStatus,
    Message,
    MessageType,
    Role,
    Thread,
    ThreadStatus,
    WorkflowMode,
    now,
)
from agent_company.llm.base import LLMProvider
from agent_company.workflow.base import WorkflowResult


# ── Mock LLM Provider ──────────────────────────────────────────────────

class MockLLMProvider(LLMProvider):
    """API 测试用 Mock Provider"""

    def __init__(self, model: str | None = "mock-model", **kwargs):
        super().__init__(model=model, **kwargs)

    async def chat(self, messages, temperature=0.7, max_tokens=2000, **kwargs) -> str:
        last = messages[-1].get("content", "") if messages else ""
        if "仲裁" in last or "决策" in last:
            return (
                "**决策摘要**: 测试决策\n\n"
                "**选择的方案**: 方案 A\n\n"
                "**理由**: 测试理由\n\n"
                "**证据**: 测试证据\n\n"
                "**反对意见**: 无"
            )
        if "拆解" in last or "任务列表" in last:
            return '[{"objective":"测试任务","definition_of_done":"完成","inputs":[],"outputs":[],"assignee_roles":["coder"],"tools_allowed":[],"timebox_rounds":1}]'
        return (
            "[CLAIM] 测试回复\n[EVIDENCE] 证据\n"
            "[RISK] 风险\n[NEXT_STEP] 下一步"
        )

    async def check_health(self) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return "mock"


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
async def mock_pipeline(tmp_path):
    """创建并初始化一个 mock pipeline，注入到 server 模块"""
    from agent_company.workflow.pipeline import Pipeline

    db_path = str(tmp_path / "api_test.db")
    p = Pipeline(llm_provider="mock", db_path=db_path, enable_memory=False)

    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        await p.setup()

    yield p

    await p.teardown()


@pytest.fixture
async def client(mock_pipeline):
    """创建 AsyncClient，通过设置 server._pipeline 使 get_pipeline() 返回测试 pipeline"""
    import agent_company.api.server as server_mod

    original = server_mod._pipeline
    server_mod._pipeline = mock_pipeline
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    finally:
        server_mod._pipeline = original


# ── GET /api/modes ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_modes(client):
    """GET /api/modes 返回正确的模式列表"""
    resp = await client.get("/api/modes")
    assert resp.status_code == 200
    data = resp.json()
    assert "modes" in data
    mode_ids = [m["id"] for m in data["modes"]]
    assert "debate" in mode_ids
    assert "pair" in mode_ids
    assert "redblue" in mode_ids
    assert "spec" in mode_ids
    assert "tdd" in mode_ids
    assert len(data["modes"]) == 5


@pytest.mark.asyncio
async def test_modes_have_name_and_desc(client):
    """每个模式都包含 name 和 desc 字段"""
    resp = await client.get("/api/modes")
    for mode in resp.json()["modes"]:
        assert "name" in mode
        assert "desc" in mode
        assert mode["name"] != ""
        assert mode["desc"] != ""


# ── GET /api/roles ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_roles(client):
    """GET /api/roles 返回正确的角色列表"""
    resp = await client.get("/api/roles")
    assert resp.status_code == 200
    data = resp.json()
    assert "roles" in data
    roles = data["roles"]
    assert "idea" in roles
    assert "architect" in roles
    assert "coder" in roles
    assert "reviewer" in roles
    assert "qa" in roles
    assert "security" in roles


# ── GET /api/providers ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_providers(client):
    """GET /api/providers 返回 provider 列表"""
    resp = await client.get("/api/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert "providers" in data
    assert isinstance(data["providers"], list)


# ── GET /api/threads ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_threads_empty(client):
    """GET /api/threads 初始返回空列表"""
    resp = await client.get("/api/threads")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


# ── POST /api/discuss ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_discuss(client, mock_pipeline):
    """POST /api/discuss 能接受请求并返回结果"""
    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        resp = await client.post(
            "/api/discuss",
            json={
                "topic": "API 测试讨论",
                "mode": "debate",
                "max_rounds": 1,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["thread_id"] != ""
    assert len(data["messages"]) > 0


@pytest.mark.asyncio
async def test_post_discuss_response_structure(client, mock_pipeline):
    """POST /api/discuss 返回正确的响应结构"""
    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        resp = await client.post(
            "/api/discuss",
            json={
                "topic": "结构验证",
                "mode": "debate",
                "max_rounds": 1,
            },
        )

    data = resp.json()
    assert "success" in data
    assert "thread_id" in data
    assert "messages" in data
    assert "error" in data

    # debate 模式应有 decision
    if data.get("decision"):
        d = data["decision"]
        assert "summary" in d
        assert "chosen_option" in d
        assert "reasoning" in d
        assert "status" in d


@pytest.mark.asyncio
async def test_post_discuss_messages_have_fields(client, mock_pipeline):
    """POST /api/discuss 返回的消息包含必要字段"""
    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        resp = await client.post(
            "/api/discuss",
            json={"topic": "字段验证", "mode": "debate", "max_rounds": 1},
        )

    msgs = resp.json()["messages"]
    assert len(msgs) > 0
    for msg in msgs:
        assert "agent_role" in msg
        assert "msg_type" in msg
        assert "content" in msg


@pytest.mark.asyncio
async def test_get_threads_after_discuss(client, mock_pipeline):
    """讨论后 GET /api/threads 能返回对应线程"""
    with patch(
        "agent_company.workflow.pipeline.create_provider",
        return_value=MockLLMProvider(),
    ):
        await client.post(
            "/api/discuss",
            json={"topic": "线程列表验证", "mode": "debate", "max_rounds": 1},
        )

    resp = await client.get("/api/threads")
    assert resp.status_code == 200
    threads = resp.json()
    assert len(threads) >= 1
    assert any(t["topic"] == "线程列表验证" for t in threads)


# ── GET /api/memory ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_memory_no_memory(client, mock_pipeline):
    """Pipeline 未开启 memory 时返回空列表"""
    resp = await client.get("/api/memory")
    assert resp.status_code == 200
    data = resp.json()
    assert data["memories"] == []
