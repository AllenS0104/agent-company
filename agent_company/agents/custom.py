"""自定义 Agent 管理"""

from __future__ import annotations

import uuid

import aiosqlite

from ..core.message_bus import MessageBus
from ..core.models import AgentConfig, Role
from .base import BaseAgent


class CustomAgentStore:
    """管理用户自定义的 Agent 角色"""

    def __init__(self, db_path: str = "agent_company.db"):
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self):
        self._db = await aiosqlite.connect(self._db_path)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS custom_agents (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                emoji TEXT DEFAULT '🤖',
                description TEXT DEFAULT '',
                system_prompt TEXT NOT NULL,
                color TEXT DEFAULT '#8b5cf6',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await self._db.commit()

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    async def list_agents(self) -> list[dict]:
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT id, name, emoji, description, system_prompt, color, created_at "
            "FROM custom_agents ORDER BY created_at"
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0], "name": r[1], "emoji": r[2], "description": r[3],
                "system_prompt": r[4], "color": r[5], "created_at": r[6],
            }
            for r in rows
        ]

    async def get_agent(self, agent_id: str) -> dict | None:
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT id, name, emoji, description, system_prompt, color "
            "FROM custom_agents WHERE id = ?",
            (agent_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0], "name": row[1], "emoji": row[2], "description": row[3],
            "system_prompt": row[4], "color": row[5],
        }

    async def create_agent(self, data: dict) -> dict:
        assert self._db is not None
        agent_id = data.get("id", uuid.uuid4().hex[:8])
        await self._db.execute(
            "INSERT INTO custom_agents (id, name, emoji, description, system_prompt, color) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                agent_id, data["name"], data.get("emoji", "🤖"),
                data.get("description", ""), data["system_prompt"],
                data.get("color", "#8b5cf6"),
            ),
        )
        await self._db.commit()
        result = await self.get_agent(agent_id)
        assert result is not None
        return result

    async def update_agent(self, agent_id: str, data: dict) -> dict | None:
        assert self._db is not None
        fields: list[str] = []
        values: list[str] = []
        for key in ("name", "emoji", "description", "system_prompt", "color"):
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        if not fields:
            return await self.get_agent(agent_id)
        fields.append("updated_at = CURRENT_TIMESTAMP")
        values.append(agent_id)
        await self._db.execute(
            f"UPDATE custom_agents SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        await self._db.commit()
        return await self.get_agent(agent_id)

    async def delete_agent(self, agent_id: str) -> bool:
        assert self._db is not None
        cursor = await self._db.execute(
            "DELETE FROM custom_agents WHERE id = ?", (agent_id,)
        )
        await self._db.commit()
        return cursor.rowcount > 0

    def create_base_agent(
        self,
        agent_data: dict,
        llm,
        bus: MessageBus,
    ) -> BaseAgent:
        """从自定义配置创建 BaseAgent 实例"""
        config = AgentConfig(
            name=agent_data["name"],
            role=Role.IDEA,  # 自定义 Agent 使用 IDEA 作为默认角色
            system_prompt=agent_data["system_prompt"],
            weight=1.0,
        )
        return BaseAgent(config=config, llm=llm, bus=bus)
