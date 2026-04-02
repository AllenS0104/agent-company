"""SQLite 持久化层"""

from __future__ import annotations

import json

import aiosqlite

from .models import (
    Artifact,
    Decision,
    Message,
    MessageType,
    Role,
    TaskCard,
    TaskStatus,
    Thread,
    ThreadStatus,
    WorkflowMode,
)

_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    mode TEXT DEFAULT 'debate',
    status TEXT DEFAULT 'open',
    max_rounds INTEGER DEFAULT 3,
    current_round INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    agent_role TEXT NOT NULL,
    content TEXT NOT NULL,
    msg_type TEXT DEFAULT 'response',
    claim TEXT DEFAULT '',
    evidence TEXT DEFAULT '',
    risk TEXT DEFAULT '',
    next_step TEXT DEFAULT '',
    timestamp TEXT,
    FOREIGN KEY (thread_id) REFERENCES threads(id)
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    decision_id TEXT,
    objective TEXT NOT NULL,
    definition_of_done TEXT DEFAULT '',
    inputs TEXT DEFAULT '[]',
    outputs TEXT DEFAULT '[]',
    assignee_roles TEXT DEFAULT '[]',
    tools_allowed TEXT DEFAULT '[]',
    timebox_rounds INTEGER DEFAULT 3,
    status TEXT DEFAULT 'pending',
    result TEXT DEFAULT '',
    created_at TEXT,
    FOREIGN KEY (thread_id) REFERENCES threads(id)
);

CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    options TEXT DEFAULT '[]',
    chosen_option TEXT DEFAULT '',
    reasoning TEXT DEFAULT '',
    evidence TEXT DEFAULT '[]',
    dissent TEXT DEFAULT '[]',
    status TEXT DEFAULT 'draft',
    created_at TEXT,
    FOREIGN KEY (thread_id) REFERENCES threads(id)
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    task_id TEXT,
    thread_id TEXT,
    artifact_type TEXT NOT NULL,
    title TEXT DEFAULT '',
    content TEXT DEFAULT '',
    file_path TEXT,
    created_at TEXT
);
"""


class Storage:
    """异步 SQLite 存储层"""

    def __init__(self, db_path: str = "agent_company.db"):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_CREATE_TABLES_SQL)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._db

    # ── Thread ──────────────────────────────────

    async def save_thread(self, thread: Thread) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO threads "
            "(id, topic, mode, status, max_rounds, current_round, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (thread.id, thread.topic, thread.mode.value, thread.status.value,
             thread.max_rounds, thread.current_round, thread.created_at.isoformat()),
        )
        await self.db.commit()

    async def get_thread(self, thread_id: str) -> Thread | None:
        async with self.db.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return Thread(
                id=row["id"], topic=row["topic"],
                mode=WorkflowMode(row["mode"]), status=ThreadStatus(row["status"]),
                max_rounds=row["max_rounds"], current_round=row["current_round"],
            )

    async def list_threads(self, status: ThreadStatus | None = None) -> list[Thread]:
        sql = "SELECT * FROM threads"
        params: tuple = ()
        if status:
            sql += " WHERE status = ?"
            params = (status.value,)
        sql += " ORDER BY created_at DESC"
        threads = []
        async with self.db.execute(sql, params) as cur:
            async for row in cur:
                threads.append(Thread(
                    id=row["id"], topic=row["topic"],
                    mode=WorkflowMode(row["mode"]), status=ThreadStatus(row["status"]),
                    max_rounds=row["max_rounds"], current_round=row["current_round"],
                ))
        return threads

    # ── Message ─────────────────────────────────

    async def save_message(self, msg: Message) -> None:
        eb = msg.evidence_block
        await self.db.execute(
            "INSERT INTO messages (id, thread_id, agent_id, agent_role, content, msg_type, "
            "claim, evidence, risk, next_step, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (msg.id, msg.thread_id, msg.agent_id, msg.agent_role.value, msg.content,
             msg.msg_type.value,
             eb.claim if eb else "", eb.evidence if eb else "",
             eb.risk if eb else "", eb.next_step if eb else "",
             msg.timestamp.isoformat()),
        )
        await self.db.commit()

    async def get_thread_messages(self, thread_id: str) -> list[Message]:
        messages = []
        async with self.db.execute(
            "SELECT * FROM messages WHERE thread_id = ? ORDER BY timestamp", (thread_id,)
        ) as cur:
            async for row in cur:
                from .models import EvidenceBlock
                eb = None
                if row["claim"] or row["evidence"] or row["risk"] or row["next_step"]:
                    eb = EvidenceBlock(
                        claim=row["claim"], evidence=row["evidence"],
                        risk=row["risk"], next_step=row["next_step"],
                    )
                messages.append(Message(
                    id=row["id"], thread_id=row["thread_id"],
                    agent_id=row["agent_id"], agent_role=Role(row["agent_role"]),
                    content=row["content"], msg_type=MessageType(row["msg_type"]),
                    evidence_block=eb,
                ))
        return messages

    # ── Task ────────────────────────────────────

    async def save_task(self, task: TaskCard) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO tasks (id, thread_id, decision_id, objective, "
            "definition_of_done, inputs, outputs, assignee_roles, tools_allowed, "
            "timebox_rounds, status, result, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (task.id, task.thread_id, task.decision_id, task.objective,
             task.definition_of_done, json.dumps(task.inputs),
             json.dumps(task.outputs), json.dumps([r.value for r in task.assignee_roles]),
             json.dumps(task.tools_allowed), task.timebox_rounds,
             task.status.value, task.result, task.created_at.isoformat()),
        )
        await self.db.commit()

    async def get_thread_tasks(self, thread_id: str) -> list[TaskCard]:
        tasks = []
        async with self.db.execute(
            "SELECT * FROM tasks WHERE thread_id = ? ORDER BY created_at", (thread_id,)
        ) as cur:
            async for row in cur:
                tasks.append(TaskCard(
                    id=row["id"], thread_id=row["thread_id"],
                    decision_id=row["decision_id"], objective=row["objective"],
                    definition_of_done=row["definition_of_done"],
                    inputs=json.loads(row["inputs"]), outputs=json.loads(row["outputs"]),
                    assignee_roles=[Role(r) for r in json.loads(row["assignee_roles"])],
                    tools_allowed=json.loads(row["tools_allowed"]),
                    timebox_rounds=row["timebox_rounds"],
                    status=TaskStatus(row["status"]), result=row["result"],
                ))
        return tasks

    # ── Decision ────────────────────────────────

    async def save_decision(self, decision: Decision) -> None:
        await self.db.execute(
            "INSERT OR REPLACE INTO decisions (id, thread_id, summary, options, "
            "chosen_option, reasoning, evidence, dissent, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (decision.id, decision.thread_id, decision.summary,
             json.dumps(decision.options), decision.chosen_option,
             decision.reasoning, json.dumps(decision.evidence),
             json.dumps(decision.dissent), decision.status.value,
             decision.created_at.isoformat()),
        )
        await self.db.commit()

    async def get_thread_decision(self, thread_id: str) -> "Decision | None":
        from .models import DecisionStatus
        async with self.db.execute(
            "SELECT * FROM decisions WHERE thread_id = ? ORDER BY created_at DESC LIMIT 1",
            (thread_id,),
        ) as cur:
            row = await cur.fetchone()
            if not row:
                return None
            return Decision(
                id=row["id"], thread_id=row["thread_id"],
                summary=row["summary"],
                options=json.loads(row["options"]),
                chosen_option=row["chosen_option"],
                reasoning=row["reasoning"],
                evidence=json.loads(row["evidence"]),
                dissent=json.loads(row["dissent"]),
                status=DecisionStatus(row["status"]),
            )

    # ── Artifact ────────────────────────────────

    async def save_artifact(self, artifact: Artifact) -> None:
        await self.db.execute(
            "INSERT INTO artifacts (id, task_id, thread_id, artifact_type, title, "
            "content, file_path, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (artifact.id, artifact.task_id, artifact.thread_id,
             artifact.artifact_type.value, artifact.title,
             artifact.content, artifact.file_path, artifact.created_at.isoformat()),
        )
        await self.db.commit()
