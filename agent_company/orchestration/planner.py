"""Planner — 计划器：将需求拆解为可验证子任务"""

from __future__ import annotations

import json
import logging

from ..core.models import (
    Message,
    Role,
    TaskCard,
    TaskStatus,
    new_id,
)
from ..core.protocols import build_context_messages
from ..llm.base import LLMProvider

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """你是一位资深项目经理/计划器。

你的职责是将讨论中形成的方案拆解为可执行的任务列表。

对于每个任务，你必须输出以下 JSON 格式：
```json
[
  {
    "objective": "任务目标描述",
    "definition_of_done": "完成标准",
    "inputs": ["输入依赖"],
    "outputs": ["预期产出"],
    "assignee_roles": ["coder", "reviewer"],
    "tools_allowed": ["executor", "test_runner", "linter"],
    "timebox_rounds": 3
  }
]
```

原则：
- 每个任务必须有明确的完成标准（definition_of_done）
- 任务粒度适中：一个 Agent 在 1-3 轮内可以完成
- 标注任务间的依赖关系
- 只产出可验证的任务（能被测试或审查验证）"""


class Planner:
    """计划器 — 拆解任务"""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def decompose(
        self, thread_id: str, discussion_messages: list[Message], decision_summary: str = ""
    ) -> list[TaskCard]:
        """将讨论结果拆解为任务列表"""
        prompt = PLANNER_PROMPT
        if decision_summary:
            prompt += f"\n\n已形成的决策：\n{decision_summary}"

        context = build_context_messages(discussion_messages, prompt, evidence_instruction=False)
        context.append({
            "role": "user",
            "content": "请将以上讨论结果拆解为可执行的任务列表，以 JSON 数组格式输出。",
        })

        raw = await self.llm.chat(messages=context, temperature=0.3)

        tasks = self._parse_tasks(raw, thread_id)
        logger.info(f"[Planner] Decomposed into {len(tasks)} tasks")
        return tasks

    def _parse_tasks(self, raw: str, thread_id: str) -> list[TaskCard]:
        """从 LLM 输出中解析任务列表"""
        tasks = []
        try:
            # 提取 JSON 部分
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                for item in data:
                    tasks.append(TaskCard(
                        id=new_id(),
                        thread_id=thread_id,
                        objective=item.get("objective", ""),
                        definition_of_done=item.get("definition_of_done", ""),
                        inputs=item.get("inputs", []),
                        outputs=item.get("outputs", []),
                        assignee_roles=[Role(r) for r in item.get("assignee_roles", ["coder"])],
                        tools_allowed=item.get("tools_allowed", []),
                        timebox_rounds=item.get("timebox_rounds", 3),
                        status=TaskStatus.PENDING,
                    ))
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[Planner] Failed to parse tasks: {e}")
            # fallback: 创建一个通用任务
            tasks.append(TaskCard(
                thread_id=thread_id,
                objective=raw[:200],
                assignee_roles=[Role.CODER],
            ))
        return tasks
