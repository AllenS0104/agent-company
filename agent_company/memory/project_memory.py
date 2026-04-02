"""项目记忆 — 持久化项目知识库"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from enum import Enum

import aiosqlite

from ..core.models import Decision


class MemoryType(str, Enum):
    ADR = "adr"
    STYLE_GUIDE = "style_guide"
    KNOWLEDGE = "knowledge"
    DECISION_HISTORY = "decision_history"
    LESSON_LEARNED = "lesson_learned"


# 各类型的默认重要度
_DEFAULT_IMPORTANCE: dict[MemoryType, int] = {
    MemoryType.DECISION_HISTORY: 5,
    MemoryType.ADR: 5,
    MemoryType.LESSON_LEARNED: 4,
    MemoryType.KNOWLEDGE: 3,
    MemoryType.STYLE_GUIDE: 3,
}


class ProjectMemory:
    """项目记忆 — 跨讨论的知识积累

    存储：
    - ADR 决策记录历史
    - 代码风格约束
    - 项目知识（已知约束、技术栈偏好等）
    - 经验教训

    增强能力：
    - 跨讨论关联搜索（find_related）
    - 记忆摘要统计（get_summary）
    - 标签系统（tags 过滤）
    - 重要度评级（importance 1-5）
    - 记忆归档（archive_old）
    """

    _CREATE_SQL = """
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id TEXT DEFAULT 'default',
        memory_type TEXT NOT NULL,
        title TEXT DEFAULT '',
        content TEXT NOT NULL,
        tags TEXT DEFAULT '[]',
        importance INTEGER DEFAULT 3,
        archived INTEGER DEFAULT 0,
        created_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_memories_project
        ON memories(project_id, memory_type);
    """

    _MIGRATE_SQL = [
        ("importance", "ALTER TABLE memories ADD COLUMN importance INTEGER DEFAULT 3"),
        ("archived", "ALTER TABLE memories ADD COLUMN archived INTEGER DEFAULT 0"),
    ]

    def __init__(self, db_path: str = "agent_company.db"):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._migrate()
        await self._db.executescript(self._CREATE_SQL)
        await self._db.commit()

    async def _migrate(self) -> None:
        """自动添加缺失的列（兼容旧数据库）"""
        # Check if table exists first
        async with self.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
        ) as cur:
            if not await cur.fetchone():
                return  # table doesn't exist yet, CREATE TABLE will handle it

        for _col_name, alter_sql in self._MIGRATE_SQL:
            try:
                await self.db.execute(alter_sql)
            except Exception:
                pass  # column already exists
        await self.db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if not self._db:
            raise RuntimeError("Memory not connected")
        return self._db

    # ── 存储 ─────────────────────────────────

    async def store(
        self,
        memory_type: MemoryType,
        content: str,
        title: str = "",
        tags: list[str] | None = None,
        importance: int | None = None,
        project_id: str = "default",
    ) -> int:
        """存储一条记忆

        Args:
            importance: 1-5 重要度，None 时使用该类型的默认值
        """
        if importance is None:
            importance = _DEFAULT_IMPORTANCE.get(memory_type, 3)
        importance = max(1, min(5, importance))

        cursor = await self.db.execute(
            "INSERT INTO memories "
            "(project_id, memory_type, title, content, tags, importance, archived, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
            (
                project_id, memory_type.value, title, content,
                json.dumps(tags or []),
                importance,
                datetime.now().isoformat(),
            ),
        )
        await self.db.commit()
        return cursor.lastrowid or 0

    async def store_decision(
        self,
        decision: Decision,
        project_id: str = "default",
        tags: list[str] | None = None,
    ) -> int:
        """将决策存为记忆（默认重要度 5）"""
        content = (
            f"## 决策: {decision.summary}\n\n"
            f"**选择**: {decision.chosen_option}\n\n"
            f"**理由**: {decision.reasoning}\n\n"
            f"**证据**: {', '.join(decision.evidence)}\n\n"
            f"**反对意见**: {', '.join(decision.dissent)}"
        )
        decision_tags = list(tags or [])
        if "decision" not in decision_tags:
            decision_tags.append("decision")
        return await self.store(
            MemoryType.DECISION_HISTORY, content,
            title=decision.summary, tags=decision_tags,
            importance=5, project_id=project_id,
        )

    # ── 检索 ─────────────────────────────────

    async def recall(
        self,
        memory_type: MemoryType | None = None,
        keyword: str = "",
        tags: list[str] | None = None,
        project_id: str = "default",
        limit: int = 10,
        include_archived: bool = False,
    ) -> list[dict]:
        """检索记忆，支持按关键词、类型、标签过滤"""
        sql = "SELECT * FROM memories WHERE project_id = ?"
        params: list = [project_id]

        if not include_archived:
            sql += " AND archived = 0"

        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type.value)

        if keyword:
            sql += " AND (content LIKE ? OR title LIKE ?)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])

        if tags:
            for tag in tags:
                sql += " AND tags LIKE ?"
                params.append(f'%"{tag}"%')

        sql += " ORDER BY importance DESC, created_at DESC LIMIT ?"
        params.append(limit)

        results = []
        async with self.db.execute(sql, params) as cur:
            async for row in cur:
                results.append(self._row_to_dict(row))
        return results

    async def recall_for_context(
        self,
        project_id: str = "default",
        topic: str = "",
        limit: int = 5,
    ) -> str:
        """检索记忆并格式化为 Agent 可用的上下文

        优先返回高重要度的记忆；若提供 topic，额外搜索相关记忆。
        """
        memories = await self.recall(project_id=project_id, limit=limit)

        if topic:
            related = await self.find_related(topic, limit=3, project_id=project_id)
            seen_ids = {m["id"] for m in memories}
            for r in related:
                if r["id"] not in seen_ids:
                    memories.append(r)

        if not memories:
            return ""

        lines = ["## 项目历史记忆\n"]
        for mem in memories:
            stars = "⭐" * mem.get("importance", 3)
            lines.append(f"### [{mem['type']}] {mem['title']}  {stars}")
            lines.append(mem["content"][:500])
            lines.append("")

        return "\n".join(lines)

    # ── 跨讨论关联搜索 ─────────────────────────

    async def find_related(
        self,
        topic: str,
        limit: int = 5,
        project_id: str = "default",
    ) -> list[dict]:
        """根据主题关键词搜索相关的历史记忆

        对 topic 进行分词，在 title 和 content 中做 LIKE 匹配，
        按匹配词数降序 + 重要度降序排序。
        """
        keywords = [w.strip() for w in topic.replace(",", " ").split() if w.strip()]
        if not keywords:
            return []

        # Build WHERE conditions: at least one keyword must match
        where_parts = []
        where_params: list = []
        for kw in keywords:
            where_parts.append("(title LIKE ? OR content LIKE ?)")
            where_params.extend([f"%{kw}%", f"%{kw}%"])

        where_clause = " OR ".join(where_parts)

        # Build score expression for ordering
        case_parts = []
        score_params: list = []
        for kw in keywords:
            case_parts.append(
                "(CASE WHEN title LIKE ? OR content LIKE ? THEN 1 ELSE 0 END)"
            )
            score_params.extend([f"%{kw}%", f"%{kw}%"])

        score_expr = " + ".join(case_parts)

        sql = (
            f"SELECT *, ({score_expr}) AS relevance "
            f"FROM memories "
            f"WHERE project_id = ? AND archived = 0 AND ({where_clause}) "
            f"ORDER BY relevance DESC, importance DESC, created_at DESC "
            f"LIMIT ?"
        )
        params = score_params + [project_id] + where_params + [limit]

        results = []
        async with self.db.execute(sql, params) as cur:
            async for row in cur:
                results.append(self._row_to_dict(row))
        return results

    # ── 记忆摘要 ─────────────────────────────

    async def get_summary(self, project_id: str = "default") -> dict:
        """返回记忆系统的统计摘要"""
        summary: dict = {
            "total": 0,
            "active": 0,
            "archived": 0,
            "by_type": {},
            "by_importance": {},
            "all_tags": [],
            "latest_at": None,
        }

        # 总数与归档数
        async with self.db.execute(
            "SELECT COUNT(*) as cnt, "
            "SUM(CASE WHEN archived = 0 THEN 1 ELSE 0 END) as active, "
            "SUM(CASE WHEN archived = 1 THEN 1 ELSE 0 END) as arc, "
            "MAX(created_at) as latest "
            "FROM memories WHERE project_id = ?",
            (project_id,),
        ) as cur:
            row = await cur.fetchone()
            if row:
                summary["total"] = row["cnt"] or 0
                summary["active"] = row["active"] or 0
                summary["archived"] = row["arc"] or 0
                summary["latest_at"] = row["latest"]

        # 按类型分布
        async with self.db.execute(
            "SELECT memory_type, COUNT(*) as cnt FROM memories "
            "WHERE project_id = ? AND archived = 0 GROUP BY memory_type",
            (project_id,),
        ) as cur:
            async for row in cur:
                summary["by_type"][row["memory_type"]] = row["cnt"]

        # 按重要度分布
        async with self.db.execute(
            "SELECT importance, COUNT(*) as cnt FROM memories "
            "WHERE project_id = ? AND archived = 0 GROUP BY importance ORDER BY importance",
            (project_id,),
        ) as cur:
            async for row in cur:
                summary["by_importance"][str(row["importance"])] = row["cnt"]

        # 收集所有标签
        tag_set: set[str] = set()
        async with self.db.execute(
            "SELECT tags FROM memories WHERE project_id = ? AND archived = 0",
            (project_id,),
        ) as cur:
            async for row in cur:
                for tag in json.loads(row["tags"] or "[]"):
                    tag_set.add(tag)
        summary["all_tags"] = sorted(tag_set)

        return summary

    # ── 归档 ─────────────────────────────────

    async def archive_old(self, days: int = 90, project_id: str = "default") -> int:
        """归档超过指定天数的旧记忆

        Returns:
            归档的记忆条数
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor = await self.db.execute(
            "UPDATE memories SET archived = 1 "
            "WHERE project_id = ? AND archived = 0 AND created_at < ?",
            (project_id, cutoff),
        )
        await self.db.commit()
        return cursor.rowcount

    # ── ADR ─────────────────────────────────

    async def get_all_adrs(self, project_id: str = "default") -> list[dict]:
        """获取所有 ADR 决策记录"""
        return await self.recall(
            memory_type=MemoryType.DECISION_HISTORY,
            project_id=project_id, limit=100,
        )

    # ── 内部辅助 ─────────────────────────────

    @staticmethod
    def _row_to_dict(row: aiosqlite.Row) -> dict:
        """将数据库行转为字典"""
        return {
            "id": row["id"],
            "type": row["memory_type"],
            "title": row["title"],
            "content": row["content"],
            "tags": json.loads(row["tags"] or "[]"),
            "importance": row["importance"] if "importance" in row.keys() else 3,
            "created_at": row["created_at"],
        }
