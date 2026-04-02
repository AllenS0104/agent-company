"""SSE 流式端点测试"""

from __future__ import annotations

import asyncio
import json

import pytest

from agent_company.api.routes import _format_sse, _message_to_sse
from agent_company.core.message_bus import MessageBus
from agent_company.core.models import (
    EvidenceBlock,
    Message,
    MessageType,
    Role,
    new_id,
    now,
)


# ── 辅助函数测试 ──────────────────────────

def test_format_sse():
    """SSE 事件格式化"""
    result = _format_sse("message", {"role": "architect", "content": "hello"})
    assert result.startswith("event: message\n")
    assert "data: " in result
    assert result.endswith("\n\n")
    data_line = result.split("\n")[1]
    payload = json.loads(data_line.removeprefix("data: "))
    assert payload["role"] == "architect"
    assert payload["content"] == "hello"


def test_format_sse_unicode():
    """SSE 格式化支持中文"""
    result = _format_sse("message", {"content": "你好世界"})
    payload = json.loads(result.split("\n")[1].removeprefix("data: "))
    assert payload["content"] == "你好世界"


def test_message_to_sse_without_evidence():
    """Message 转 SSE（无证据块）"""
    msg = Message(
        id=new_id(), thread_id="t1", agent_id="a1",
        agent_role=Role.ARCHITECT, content="My proposal",
        msg_type=MessageType.PROPOSAL, timestamp=now(),
    )
    result = _message_to_sse(msg)
    assert "event: message" in result
    payload = json.loads(result.split("\n")[1].removeprefix("data: "))
    assert payload["role"] == "architect"
    assert payload["content"] == "My proposal"
    assert payload["msg_type"] == "proposal"
    assert "claim" not in payload


def test_message_to_sse_with_evidence():
    """Message 转 SSE（含证据块）"""
    msg = Message(
        id=new_id(), thread_id="t1", agent_id="a1",
        agent_role=Role.REVIEWER, content="Challenge!",
        msg_type=MessageType.CHALLENGE, timestamp=now(),
        evidence_block=EvidenceBlock(
            claim="perf is bad", evidence="benchmark shows 200ms",
            risk="latency", next_step="optimize",
        ),
    )
    result = _message_to_sse(msg)
    payload = json.loads(result.split("\n")[1].removeprefix("data: "))
    assert payload["claim"] == "perf is bad"
    assert payload["evidence"] == "benchmark shows 200ms"
    assert payload["risk"] == "latency"
    assert payload["next_step"] == "optimize"


# ── 队列桥接集成测试 ──────────────────────────

async def test_queue_bridge_with_message_bus():
    """验证 subscribe_all + asyncio.Queue 桥接能正常传递消息"""
    bus = MessageBus()
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def on_message(msg: Message) -> None:
        await queue.put({"type": "message", "msg": msg})

    bus.subscribe_all(on_message)

    msg = Message(
        id=new_id(), thread_id="t1", agent_id="a1",
        agent_role=Role.CODER, content="code snippet",
        msg_type=MessageType.RESPONSE, timestamp=now(),
    )
    await bus.publish(msg)

    item = await asyncio.wait_for(queue.get(), timeout=2.0)
    assert item is not None
    assert item["type"] == "message"
    assert item["msg"].content == "code snippet"
    assert item["msg"].agent_role == Role.CODER

    # 清理
    bus._global_subs.remove(on_message)
    assert len(bus._global_subs) == 0


async def test_queue_bridge_multiple_messages():
    """验证多条消息按顺序送达"""
    bus = MessageBus()
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def on_message(msg: Message) -> None:
        await queue.put({"type": "message", "msg": msg})

    bus.subscribe_all(on_message)

    roles = [Role.IDEA, Role.ARCHITECT, Role.CODER, Role.REVIEWER]
    for role in roles:
        msg = Message(
            id=new_id(), thread_id="t1", agent_id=f"agent-{role.value}",
            agent_role=role, content=f"msg from {role.value}",
            msg_type=MessageType.RESPONSE, timestamp=now(),
        )
        await bus.publish(msg)

    received = []
    for _ in range(4):
        item = await asyncio.wait_for(queue.get(), timeout=2.0)
        received.append(item["msg"].agent_role)

    assert received == roles
    bus._global_subs.remove(on_message)
