"""讨论线程管理"""

from __future__ import annotations

from .message_bus import MessageBus
from .models import Message, Thread, ThreadStatus, WorkflowMode
from .storage import Storage


class ThreadManager:
    """管理讨论线程的生命周期"""

    def __init__(self, bus: MessageBus, storage: Storage):
        self.bus = bus
        self.storage = storage
        self._active_threads: dict[str, Thread] = {}

    async def create_thread(
        self,
        topic: str,
        mode: WorkflowMode = WorkflowMode.DEBATE,
        max_rounds: int = 3,
    ) -> Thread:
        """创建新的讨论线程"""
        thread = Thread(topic=topic, mode=mode, max_rounds=max_rounds)
        self._active_threads[thread.id] = thread
        await self.storage.save_thread(thread)
        return thread

    async def get_thread(self, thread_id: str) -> Thread | None:
        if thread_id in self._active_threads:
            return self._active_threads[thread_id]
        return await self.storage.get_thread(thread_id)

    async def update_status(self, thread_id: str, status: ThreadStatus) -> None:
        thread = await self.get_thread(thread_id)
        if thread:
            thread.status = status
            await self.storage.save_thread(thread)

    async def advance_round(self, thread_id: str) -> int:
        """推进讨论轮次，返回新的轮次号"""
        thread = await self.get_thread(thread_id)
        if thread:
            thread.current_round += 1
            await self.storage.save_thread(thread)
            return thread.current_round
        return 0

    async def is_round_limit_reached(self, thread_id: str) -> bool:
        thread = await self.get_thread(thread_id)
        if thread:
            return thread.current_round >= thread.max_rounds
        return True

    async def add_message(self, message: Message) -> None:
        """添加消息到线程并发布到消息总线"""
        await self.storage.save_message(message)
        await self.bus.publish(message)

        # 同步到内存中的 thread
        thread = await self.get_thread(message.thread_id)
        if thread:
            thread.messages.append(message)

    async def get_messages(self, thread_id: str) -> list[Message]:
        return await self.storage.get_thread_messages(thread_id)
