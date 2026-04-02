"""Moderator — 主持人：控制讨论轮次、防发散"""

from __future__ import annotations

import logging

from ..core.message_bus import MessageBus
from ..core.models import Message, MessageType, Role, Thread, new_id, now

logger = logging.getLogger(__name__)


class Moderator:
    """主持人 — 控制讨论流程

    职责：
    1. 控制讨论轮次（不超过 max_rounds）
    2. 限制发言长度
    3. 检测跑题并打回
    4. 防发散：要求每轮回答"解决了什么？还缺什么证据？"
    """

    def __init__(self, bus: MessageBus, max_message_length: int = 2000):
        self.bus = bus
        self.max_message_length = max_message_length

    async def open_discussion(self, thread: Thread) -> Message:
        """开场白：宣布讨论主题和规则"""
        content = (
            f"📋 **讨论主题**: {thread.topic}\n"
            f"🔄 **最大轮次**: {thread.max_rounds}\n"
            f"📏 **发言限制**: {self.max_message_length} 字\n\n"
            f"**讨论规则**:\n"
            f"1. 每条发言必须包含 [Claim] [Evidence] [Risk] [Next Step]\n"
            f"2. 没有 Evidence 的主张权重自动降低\n"
            f"3. 每轮结束必须回答：「我解决了什么？还缺什么证据？」\n"
            f"4. 超出范围的讨论将被打回\n\n"
            f"请各角色开始发表观点。"
        )
        msg = Message(
            id=new_id(), thread_id=thread.id,
            agent_id="moderator", agent_role=Role.MODERATOR,
            content=content, msg_type=MessageType.SYSTEM, timestamp=now(),
        )
        await self.bus.publish(msg)
        return msg

    async def check_round(self, thread: Thread) -> str:
        """检查当前轮次状态，返回指令

        Returns:
            "continue" | "next_round" | "conclude" | "off_topic"
        """
        if thread.current_round >= thread.max_rounds:
            return "conclude"
        return "continue"

    async def announce_round(self, thread: Thread, round_num: int) -> Message:
        """宣布新轮次"""
        remaining = thread.max_rounds - round_num
        content = (
            f"🔄 **第 {round_num} 轮讨论**（剩余 {remaining} 轮）\n\n"
            f"请针对上一轮的观点进行质疑或补充。\n"
            f"提醒：请回答「我解决了什么？还缺什么证据？」"
        )
        msg = Message(
            id=new_id(), thread_id=thread.id,
            agent_id="moderator", agent_role=Role.MODERATOR,
            content=content, msg_type=MessageType.SYSTEM, timestamp=now(),
        )
        await self.bus.publish(msg)
        return msg

    async def conclude_discussion(self, thread: Thread) -> Message:
        """宣布讨论结束，进入决策阶段"""
        content = (
            f"⏹️ **讨论结束**（共 {thread.current_round} 轮）\n\n"
            f"讨论已达到最大轮次。现在进入决策阶段。\n"
            f"裁判将根据各方的主张和证据做出最终决策。"
        )
        msg = Message(
            id=new_id(), thread_id=thread.id,
            agent_id="moderator", agent_role=Role.MODERATOR,
            content=content, msg_type=MessageType.SYSTEM, timestamp=now(),
        )
        await self.bus.publish(msg)
        return msg

    def validate_message(self, message: Message) -> tuple[bool, str]:
        """验证消息是否符合规则

        Returns:
            (is_valid, reason)
        """
        if len(message.content) > self.max_message_length:
            return False, f"发言超过 {self.max_message_length} 字限制"

        if not message.has_evidence and message.msg_type in (
            MessageType.PROPOSAL, MessageType.CHALLENGE
        ):
            logger.warning(
                f"[Moderator] {message.agent_role.value} 的 {message.msg_type.value} "
                f"缺少证据，权重将被降低"
            )
        return True, ""
