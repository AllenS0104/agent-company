"""消息总线 — Agent 间通信的发布/订阅/广播机制"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

from .models import Message, MessageType, Role

logger = logging.getLogger(__name__)

# 订阅回调类型
Subscriber = Callable[[Message], Coroutine[Any, Any, None]]


class MessageBus:
    """异步消息总线

    支持：
    - 按线程订阅（只接收特定 thread 的消息）
    - 按角色订阅（只接收特定角色发出的消息）
    - 按消息类型订阅
    - 广播（所有订阅者都收到）
    """

    def __init__(self):
        # thread_id -> list[subscriber]
        self._thread_subs: dict[str, list[Subscriber]] = defaultdict(list)
        # role -> list[subscriber]
        self._role_subs: dict[Role, list[Subscriber]] = defaultdict(list)
        # msg_type -> list[subscriber]
        self._type_subs: dict[MessageType, list[Subscriber]] = defaultdict(list)
        # 全局订阅者
        self._global_subs: list[Subscriber] = []
        # 消息历史（内存缓存）
        self._history: dict[str, list[Message]] = defaultdict(list)
        # 广播锁
        self._lock = asyncio.Lock()

    def subscribe_thread(self, thread_id: str, callback: Subscriber) -> None:
        """订阅特定线程的消息"""
        self._thread_subs[thread_id].append(callback)

    def subscribe_role(self, role: Role, callback: Subscriber) -> None:
        """订阅特定角色发出的消息"""
        self._role_subs[role].append(callback)

    def subscribe_type(self, msg_type: MessageType, callback: Subscriber) -> None:
        """订阅特定类型的消息"""
        self._type_subs[msg_type].append(callback)

    def subscribe_all(self, callback: Subscriber) -> None:
        """订阅所有消息"""
        self._global_subs.append(callback)

    async def publish(self, message: Message) -> None:
        """发布消息到总线"""
        async with self._lock:
            self._history[message.thread_id].append(message)

        logger.debug(
            f"[Bus] {message.agent_role.value} -> thread:{message.thread_id[:8]} "
            f"type:{message.msg_type.value}"
        )

        # 收集所有需要通知的回调
        callbacks: list[Subscriber] = []
        callbacks.extend(self._global_subs)
        callbacks.extend(self._thread_subs.get(message.thread_id, []))
        callbacks.extend(self._role_subs.get(message.agent_role, []))
        callbacks.extend(self._type_subs.get(message.msg_type, []))

        # 去重并并发执行
        seen = set()
        unique_callbacks = []
        for cb in callbacks:
            cb_id = id(cb)
            if cb_id not in seen:
                seen.add(cb_id)
                unique_callbacks.append(cb)

        if unique_callbacks:
            results = await asyncio.gather(
                *(cb(message) for cb in unique_callbacks),
                return_exceptions=True,
            )
            for idx, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        "[Bus] Subscriber %s raised exception: %s",
                        unique_callbacks[idx], result, exc_info=result,
                    )

    async def broadcast(
        self, thread_id: str, content: str, msg_type: MessageType = MessageType.SYSTEM,
    ) -> None:
        """广播系统消息"""
        from .models import new_id, now
        msg = Message(
            id=new_id(),
            thread_id=thread_id,
            agent_id="system",
            agent_role=Role.MODERATOR,
            content=content,
            msg_type=msg_type,
            timestamp=now(),
        )
        await self.publish(msg)

    def get_thread_history(self, thread_id: str) -> list[Message]:
        """获取线程内所有消息"""
        return list(self._history.get(thread_id, []))

    def clear_thread(self, thread_id: str) -> None:
        """清除线程消息缓存"""
        self._history.pop(thread_id, None)

    def clear_all(self) -> None:
        """清除所有缓存"""
        self._history.clear()
        self._thread_subs.clear()
        self._role_subs.clear()
        self._type_subs.clear()
        self._global_subs.clear()
