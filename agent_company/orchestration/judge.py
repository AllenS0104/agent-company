"""Judge — 裁判：冲突仲裁 + 证据评分 + ADR 生成"""

from __future__ import annotations

import logging

from ..core.models import (
    Decision,
    DecisionStatus,
    Message,
    Role,
    new_id,
)
from ..core.protocols import build_context_messages
from ..llm.base import LLMProvider

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """你是一位公正的裁判/仲裁者。

你的职责是根据讨论内容做出最终决策。

仲裁流程（按优先级）：
1. **实验/测试验证**：如果争议可以通过实验解决，优先建议实验
2. **约束/目标函数**：根据性能、成本、安全、交付时间等硬约束裁决
3. **证据权重投票**：有证据支持的主张权重更高
4. **最终裁决**：综合所有因素做出决定

你必须输出以下内容：
- **决策摘要**: 一句话总结
- **选择的方案**: 具体选择了什么
- **理由**: 为什么做出这个选择
- **证据**: 支持决策的关键证据
- **反对意见记录**: 被否决的观点（确保可追溯）
- **ADR**: 架构决策记录

你追求的是"正确和可追溯"，而不是"皆大欢喜"。"""


class Judge:
    """裁判 — 仲裁决策"""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def arbitrate(
        self,
        thread_id: str,
        discussion_messages: list[Message],
        agent_weights: dict[str, float] | None = None,
    ) -> Decision:
        """根据讨论内容做出仲裁决策

        4步仲裁协议：
        1. 能否用实验/测试解决？
        2. 能否用约束/目标函数裁决？
        3. 投票 + 权重
        4. 最终裁决 + ADR
        """
        # 计算证据权重
        scored_messages = self._score_messages(discussion_messages, agent_weights or {})

        context = build_context_messages(
            discussion_messages, JUDGE_PROMPT, evidence_instruction=False,
        )
        context.append({
            "role": "user",
            "content": (
                f"以上是各方的讨论。\n\n"
                f"证据评分结果：\n{scored_messages}\n\n"
                f"请按照仲裁流程做出最终决策，包含：决策摘要、选择的方案、理由、"
                f"证据、反对意见记录。"
            ),
        })

        raw = await self.llm.chat(messages=context, temperature=0.3)

        decision = Decision(
            id=new_id(),
            thread_id=thread_id,
            summary=self._extract_section(raw, "决策摘要", "选择"),
            chosen_option=self._extract_section(raw, "选择的方案", "理由"),
            reasoning=self._extract_section(raw, "理由", "证据"),
            evidence=[self._extract_section(raw, "证据", "反对")],
            dissent=[self._extract_section(raw, "反对意见", "")],
            status=DecisionStatus.APPROVED,
        )

        logger.info(f"[Judge] Decision: {decision.summary[:100]}")
        return decision

    def _score_messages(
        self, messages: list[Message], weights: dict[str, float]
    ) -> str:
        """为消息评分（基于证据和角色权重）"""
        scores = []
        for msg in messages:
            if msg.agent_role in (Role.MODERATOR, Role.PLANNER):
                continue

            base_weight = weights.get(msg.agent_id, 1.0)
            evidence_bonus = 0.5 if msg.has_evidence else 0.0
            score = base_weight + evidence_bonus

            scores.append(
                f"- [{msg.agent_role.value}] 权重={score:.1f} "
                f"{'(有证据)' if msg.has_evidence else '(无证据)'}: "
                f"{msg.content[:80]}..."
            )
        return "\n".join(scores) if scores else "无评分数据"

    def _extract_section(self, text: str, start_marker: str, end_marker: str) -> str:
        """从文本中提取指定段落"""
        text_lower = text.lower()
        start_marker_lower = start_marker.lower()
        end_marker_lower = end_marker.lower()

        start = text_lower.find(start_marker_lower)
        if start == -1:
            return ""

        start += len(start_marker)
        # 跳过冒号和换行
        while start < len(text) and text[start] in "：:\n ":
            start += 1

        if end_marker:
            end = text_lower.find(end_marker_lower, start)
            if end == -1:
                end = len(text)
        else:
            end = len(text)

        return text[start:end].strip()

    async def generate_adr(
        self, decision: Decision, thread_topic: str
    ) -> str:
        """生成 ADR（Architecture Decision Record）"""
        adr = f"""# ADR: {thread_topic}

## 状态
{decision.status.value}

## 背景
{thread_topic}

## 决策
{decision.summary}

### 选择的方案
{decision.chosen_option}

### 理由
{decision.reasoning}

### 证据
{chr(10).join('- ' + e for e in decision.evidence if e)}

### 反对意见（已记录）
{chr(10).join('- ' + d for d in decision.dissent if d)}

## 后果
按照以上决策执行实现。
"""
        return adr
