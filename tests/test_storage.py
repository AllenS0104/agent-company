"""测试 SQLite 存储层"""

import pytest

from agent_company.core.models import (
    EvidenceBlock,
    Message,
    Role,
    TaskCard,
    Thread,
    WorkflowMode,
)
from agent_company.core.storage import Storage


@pytest.fixture
async def storage(tmp_path):
    db_path = str(tmp_path / "test.db")
    s = Storage(db_path)
    await s.connect()
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_thread_crud(storage):
    thread = Thread(topic="test topic", mode=WorkflowMode.DEBATE)
    await storage.save_thread(thread)
    loaded = await storage.get_thread(thread.id)
    assert loaded is not None
    assert loaded.topic == "test topic"


@pytest.mark.asyncio
async def test_message_crud(storage):
    thread = Thread(topic="test")
    await storage.save_thread(thread)

    msg = Message(
        thread_id=thread.id, agent_id="a1", agent_role=Role.CODER,
        content="hello", evidence_block=EvidenceBlock(claim="test", evidence="proof"),
    )
    await storage.save_message(msg)

    messages = await storage.get_thread_messages(thread.id)
    assert len(messages) == 1
    assert messages[0].content == "hello"
    assert messages[0].evidence_block.claim == "test"


@pytest.mark.asyncio
async def test_task_crud(storage):
    task = TaskCard(thread_id="t1", objective="build it", assignee_roles=[Role.CODER])
    await storage.save_task(task)
    tasks = await storage.get_thread_tasks("t1")
    assert len(tasks) == 1
    assert tasks[0].objective == "build it"


@pytest.mark.asyncio
async def test_list_threads(storage):
    await storage.save_thread(Thread(topic="a"))
    await storage.save_thread(Thread(topic="b"))
    threads = await storage.list_threads()
    assert len(threads) == 2
