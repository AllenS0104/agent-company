"""BaseAgent — 所有角色 Agent 的基类"""

from __future__ import annotations

import logging

from ..core.message_bus import MessageBus
from ..core.models import (
    AgentConfig,
    Message,
    MessageType,
    Role,
    new_id,
    now,
)
from ..core.protocols import build_context_messages, parse_evidence_block
from ..llm.base import LLMProvider

logger = logging.getLogger(__name__)


class BaseAgent:
    """Agent 基类

    职责：
    1. 接收消息（通过消息总线）
    2. 思考（调用 LLM）
    3. 以证据格式输出回复
    """

    def __init__(
        self,
        config: AgentConfig,
        llm: LLMProvider,
        bus: MessageBus,
    ):
        self.config = config
        self.llm = llm
        self.bus = bus
        self._inbox: list[Message] = []

    @property
    def id(self) -> str:
        return self.config.id

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def role(self) -> Role:
        return self.config.role

    async def think(
        self,
        thread_messages: list[Message],
        extra_instruction: str = "",
        temperature: float = 0.7,
    ) -> Message:
        """核心思考循环：根据上下文调用 LLM 生成回复

        Args:
            thread_messages: 线程中的所有历史消息
            extra_instruction: 额外指令（由 Orchestrator 注入）
            temperature: LLM 温度参数

        Returns:
            包含证据块的 Message
        """
        system_prompt = self._build_system_prompt(extra_instruction)
        context = build_context_messages(thread_messages, system_prompt)

        raw_response = await self.llm.chat(
            messages=context,
            temperature=temperature,
        )

        evidence_block = parse_evidence_block(raw_response)
        msg_type = self._determine_message_type(raw_response, thread_messages)

        message = Message(
            id=new_id(),
            thread_id=thread_messages[0].thread_id if thread_messages else "",
            agent_id=self.id,
            agent_role=self.role,
            content=raw_response,
            msg_type=msg_type,
            evidence_block=evidence_block,
            timestamp=now(),
        )

        logger.info(f"[{self.role.value}] Generated response ({len(raw_response)} chars)")
        return message

    async def respond(
        self,
        thread_id: str,
        thread_messages: list[Message],
        extra_instruction: str = "",
    ) -> Message:
        """思考并通过消息总线发布回复"""
        message = await self.think(thread_messages, extra_instruction)
        message.thread_id = thread_id
        await self.bus.publish(message)
        return message

    def _build_system_prompt(self, extra_instruction: str = "") -> str:
        """构建系统提示词"""
        prompt = self.config.system_prompt
        if extra_instruction:
            prompt += f"\n\n--- 当前轮次特别指令 ---\n{extra_instruction}"
        return prompt

    def _determine_message_type(
        self, response: str, history: list[Message]
    ) -> MessageType:
        """根据内容判断消息类型"""
        response_lower = response.lower()
        if any(kw in response_lower for kw in ["反对", "质疑", "不同意", "challenge", "disagree"]):
            return MessageType.CHALLENGE
        if any(kw in response_lower for kw in ["方案", "建议", "proposal", "propose"]):
            return MessageType.PROPOSAL
        if any(kw in response_lower for kw in ["决定", "结论", "decision", "conclude"]):
            return MessageType.DECISION
        return MessageType.RESPONSE

    def __repr__(self) -> str:
        return f"<Agent:{self.name}({self.role.value})>"
