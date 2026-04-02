"""测试消息总线"""

import pytest

from agent_company.core.message_bus import MessageBus
from agent_company.core.models import Message, MessageType, Role, new_id, now


@pytest.fixture
def bus():
    return MessageBus()


def _make_msg(thread_id="t1", role=Role.CODER, content="test") -> Message:
    return Message(
        id=new_id(), thread_id=thread_id,
        agent_id="a1", agent_role=role,
        content=content, msg_type=MessageType.RESPONSE,
        timestamp=now(),
    )


@pytest.mark.asyncio
async def test_publish_and_history(bus):
    msg = _make_msg()
    await bus.publish(msg)
    history = bus.get_thread_history("t1")
    assert len(history) == 1
    assert history[0].content == "test"


@pytest.mark.asyncio
async def test_thread_subscription(bus):
    received = []

    async def handler(m: Message):
        received.append(m)

    bus.subscribe_thread("t1", handler)
    await bus.publish(_make_msg(thread_id="t1"))
    await bus.publish(_make_msg(thread_id="t2"))

    assert len(received) == 1


@pytest.mark.asyncio
async def test_role_subscription(bus):
    received = []

    async def handler(m: Message):
        received.append(m)

    bus.subscribe_role(Role.ARCHITECT, handler)
    await bus.publish(_make_msg(role=Role.ARCHITECT))
    await bus.publish(_make_msg(role=Role.CODER))

    assert len(received) == 1


@pytest.mark.asyncio
async def test_global_subscription(bus):
    received = []

    async def handler(m: Message):
        received.append(m)

    bus.subscribe_all(handler)
    await bus.publish(_make_msg())
    await bus.publish(_make_msg())

    assert len(received) == 2


@pytest.mark.asyncio
async def test_clear(bus):
    await bus.publish(_make_msg())
    assert len(bus.get_thread_history("t1")) == 1
    bus.clear_thread("t1")
    assert len(bus.get_thread_history("t1")) == 0
