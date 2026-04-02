"""增强 Memory 系统的测试"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest

from agent_company.memory.project_memory import MemoryType, ProjectMemory


@pytest.fixture
async def memory(tmp_path):
    """创建一个临时数据库的 ProjectMemory 实例"""
    db_path = str(tmp_path / "test_memory.db")
    mem = ProjectMemory(db_path)
    await mem.connect()
    yield mem
    await mem.close()


# ── store & recall 基础 ────────────────────

async def test_store_and_recall(memory: ProjectMemory):
    mid = await memory.store(MemoryType.KNOWLEDGE, "Python 是首选语言", title="技术栈选择")
    assert mid > 0

    results = await memory.recall()
    assert len(results) == 1
    assert results[0]["title"] == "技术栈选择"
    assert results[0]["content"] == "Python 是首选语言"


async def test_store_decision_default_importance(memory: ProjectMemory):
    from agent_company.core.models import Decision
    decision = Decision(
        thread_id="t1",
        summary="使用 FastAPI",
        chosen_option="FastAPI",
        reasoning="性能好且 async 原生支持",
        evidence=["benchmark 数据"],
        dissent=["Flask 更简单"],
    )
    mid = await memory.store_decision(decision)
    assert mid > 0

    results = await memory.recall()
    assert len(results) == 1
    assert results[0]["importance"] == 5
    assert "decision" in results[0]["tags"]


# ── tags 存储与过滤 ─────────────────────────

async def test_tags_storage(memory: ProjectMemory):
    await memory.store(MemoryType.KNOWLEDGE, "内容1", title="有标签", tags=["python", "backend"])
    await memory.store(MemoryType.KNOWLEDGE, "内容2", title="无标签")

    # 按标签过滤
    results = await memory.recall(tags=["python"])
    assert len(results) == 1
    assert results[0]["title"] == "有标签"
    assert "python" in results[0]["tags"]

    # 多个标签 AND 过滤
    results = await memory.recall(tags=["python", "backend"])
    assert len(results) == 1

    # 不匹配的标签
    results = await memory.recall(tags=["frontend"])
    assert len(results) == 0


async def test_tags_filter_no_false_positive(memory: ProjectMemory):
    """确保标签过滤不会因 content 中偶然包含标签名而误匹配"""
    await memory.store(MemoryType.KNOWLEDGE, "内容关于python的笔记", title="笔记", tags=["note"])
    results = await memory.recall(tags=["python"])
    assert len(results) == 0


# ── importance 排序 ─────────────────────────

async def test_importance_ordering(memory: ProjectMemory):
    await memory.store(MemoryType.KNOWLEDGE, "低重要度", title="low", importance=1)
    await memory.store(MemoryType.KNOWLEDGE, "高重要度", title="high", importance=5)
    await memory.store(MemoryType.KNOWLEDGE, "中重要度", title="mid", importance=3)

    results = await memory.recall(limit=10)
    importances = [r["importance"] for r in results]
    assert importances == sorted(importances, reverse=True)
    assert results[0]["title"] == "high"


async def test_importance_clamped(memory: ProjectMemory):
    """重要度超出 1-5 范围时应被截断"""
    mid = await memory.store(MemoryType.KNOWLEDGE, "test", importance=10)
    results = await memory.recall()
    assert results[0]["importance"] == 5

    mid2 = await memory.store(MemoryType.KNOWLEDGE, "test2", importance=-1)
    results = await memory.recall(limit=10)
    mins = [r["importance"] for r in results if r["id"] == mid2]
    assert mins[0] == 1


async def test_default_importance_by_type(memory: ProjectMemory):
    """不同类型应有不同默认重要度"""
    await memory.store(MemoryType.DECISION_HISTORY, "决策内容", title="dec")
    await memory.store(MemoryType.KNOWLEDGE, "知识内容", title="know")

    results = await memory.recall(limit=10)
    by_title = {r["title"]: r["importance"] for r in results}
    assert by_title["dec"] == 5
    assert by_title["know"] == 3


# ── find_related 搜索 ──────────────────────

async def test_find_related_basic(memory: ProjectMemory):
    await memory.store(MemoryType.KNOWLEDGE, "FastAPI 是一个高性能的 Python Web 框架", title="FastAPI 简介")
    await memory.store(MemoryType.KNOWLEDGE, "React 是前端框架", title="React 简介")
    await memory.store(MemoryType.KNOWLEDGE, "SQLite 是一个轻量数据库", title="SQLite 简介")

    results = await memory.find_related("FastAPI Python")
    assert len(results) >= 1
    assert results[0]["title"] == "FastAPI 简介"


async def test_find_related_empty_topic(memory: ProjectMemory):
    await memory.store(MemoryType.KNOWLEDGE, "test content", title="test")
    results = await memory.find_related("")
    assert results == []


async def test_find_related_no_match(memory: ProjectMemory):
    await memory.store(MemoryType.KNOWLEDGE, "Python web", title="后端")
    results = await memory.find_related("Kubernetes Docker")
    assert len(results) == 0


async def test_find_related_relevance_order(memory: ProjectMemory):
    """匹配更多关键词的记忆应排在前面"""
    await memory.store(MemoryType.KNOWLEDGE, "Python 和 FastAPI 的组合", title="Python FastAPI")
    await memory.store(MemoryType.KNOWLEDGE, "Python 基础教程", title="Python 基础")

    results = await memory.find_related("Python FastAPI")
    assert len(results) == 2
    assert results[0]["title"] == "Python FastAPI"


# ── get_summary 统计 ───────────────────────

async def test_get_summary_empty(memory: ProjectMemory):
    summary = await memory.get_summary()
    assert summary["total"] == 0
    assert summary["active"] == 0
    assert summary["archived"] == 0
    assert summary["by_type"] == {}
    assert summary["all_tags"] == []


async def test_get_summary_with_data(memory: ProjectMemory):
    await memory.store(MemoryType.KNOWLEDGE, "k1", title="知识1", tags=["python", "backend"])
    await memory.store(MemoryType.KNOWLEDGE, "k2", title="知识2", tags=["python"])
    await memory.store(MemoryType.DECISION_HISTORY, "d1", title="决策1", tags=["arch"])
    await memory.store(MemoryType.LESSON_LEARNED, "l1", title="教训1", importance=4)

    summary = await memory.get_summary()
    assert summary["total"] == 4
    assert summary["active"] == 4
    assert summary["archived"] == 0
    assert summary["by_type"]["knowledge"] == 2
    assert summary["by_type"]["decision_history"] == 1
    assert summary["by_type"]["lesson_learned"] == 1
    assert set(summary["all_tags"]) == {"python", "backend", "arch"}
    assert summary["latest_at"] is not None


# ── archive_old 归档 ───────────────────────

async def test_archive_old(memory: ProjectMemory):
    # 插入一条"旧"记忆（手动设置 created_at）
    old_date = (datetime.now() - timedelta(days=100)).isoformat()
    await memory.db.execute(
        "INSERT INTO memories (project_id, memory_type, title, content, tags, importance, archived, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
        ("default", "knowledge", "旧记忆", "很久以前的内容", "[]", 3, old_date),
    )
    await memory.db.commit()

    # 插入一条新记忆
    await memory.store(MemoryType.KNOWLEDGE, "新内容", title="新记忆")

    # 归档 90 天前的
    archived_count = await memory.archive_old(days=90)
    assert archived_count == 1

    # 默认 recall 不包含归档
    results = await memory.recall()
    assert len(results) == 1
    assert results[0]["title"] == "新记忆"

    # 明确包含归档
    all_results = await memory.recall(include_archived=True)
    assert len(all_results) == 2


async def test_archive_doesnt_touch_recent(memory: ProjectMemory):
    """不应归档最近的记忆"""
    await memory.store(MemoryType.KNOWLEDGE, "新", title="新记忆")
    archived = await memory.archive_old(days=90)
    assert archived == 0

    results = await memory.recall()
    assert len(results) == 1


# ── recall_for_context ─────────────────────

async def test_recall_for_context_with_topic(memory: ProjectMemory):
    await memory.store(MemoryType.KNOWLEDGE, "FastAPI 性能很好", title="FastAPI", importance=3)
    await memory.store(MemoryType.KNOWLEDGE, "React 组件化设计", title="React", importance=2)

    ctx = await memory.recall_for_context(topic="FastAPI")
    assert "FastAPI" in ctx
    assert "⭐" in ctx


async def test_recall_for_context_empty(memory: ProjectMemory):
    ctx = await memory.recall_for_context()
    assert ctx == ""


# ── 数据库迁移兼容性 ──────────────────────

async def test_migrate_adds_columns(tmp_path):
    """在没有 importance/archived 列的旧表上也能正常工作"""
    import aiosqlite

    db_path = str(tmp_path / "old.db")
    # 创建旧版表结构（没有 importance 和 archived）
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT DEFAULT 'default',
                memory_type TEXT NOT NULL,
                title TEXT DEFAULT '',
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                created_at TEXT
            )
        """)
        await db.execute(
            "INSERT INTO memories (project_id, memory_type, title, content, tags, created_at) "
            "VALUES ('default', 'knowledge', '旧数据', '旧内容', '[]', ?)",
            (datetime.now().isoformat(),),
        )
        await db.commit()

    mem = ProjectMemory(db_path)
    await mem.connect()
    try:
        results = await mem.recall()
        assert len(results) == 1
        assert results[0]["importance"] == 3  # 默认值

        # 新增记忆也应正常
        await mem.store(MemoryType.KNOWLEDGE, "新内容", importance=5)
        results = await mem.recall()
        assert len(results) == 2
    finally:
        await mem.close()
