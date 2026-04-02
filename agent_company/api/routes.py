"""FastAPI 路由"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from ..config import config
from ..core.models import Message, WorkflowMode

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Request / Response 模型 ──────────────

class DiscussRequest(BaseModel):
    topic: str
    mode: str = "debate"
    max_rounds: int = 3
    extended_agents: bool = False
    provider: str | None = None
    model: str | None = None


class MessageResponse(BaseModel):
    agent_role: str
    msg_type: str
    content: str
    claim: str = ""
    evidence: str = ""
    risk: str = ""
    next_step: str = ""


class DecisionResponse(BaseModel):
    summary: str
    chosen_option: str
    reasoning: str
    status: str


class TaskResponse(BaseModel):
    objective: str
    definition_of_done: str
    assignee_roles: list[str]
    status: str


class DiscussResponse(BaseModel):
    success: bool
    thread_id: str = ""
    messages: list[MessageResponse] = Field(default_factory=list)
    decision: DecisionResponse | None = None
    tasks: list[TaskResponse] = Field(default_factory=list)
    error: str = ""


class ThreadListItem(BaseModel):
    id: str
    topic: str
    mode: str
    status: str


# ── 路由 ─────────────────────────────────

@router.post("/discuss", response_model=DiscussResponse)
async def discuss(req: DiscussRequest):
    """发起一次多 Agent 讨论"""
    from .server import get_pipeline

    mode_map = {
        "debate": WorkflowMode.DEBATE,
        "pair": WorkflowMode.PAIR_PROGRAMMING,
        "redblue": WorkflowMode.RED_BLUE_TEAM,
        "spec": WorkflowMode.SPEC_FIRST,
        "tdd": WorkflowMode.TDD_LOOP,
    }
    workflow_mode = mode_map.get(req.mode, WorkflowMode.DEBATE)

    pipeline = get_pipeline()

    # 如果指定了 provider/model，创建新的临时 pipeline
    if req.provider or req.model:
        from ..workflow.pipeline import Pipeline
        temp_pipeline = Pipeline(
            llm_provider=req.provider,
            llm_model=req.model,
        )
        await temp_pipeline.setup()
        try:
            result = await temp_pipeline.run_discussion(
                topic=req.topic,
                mode=workflow_mode,
                max_rounds=req.max_rounds,
                extended_agents=req.extended_agents,
            )
        finally:
            await temp_pipeline.teardown()
    else:
        result = await pipeline.run_discussion(
            topic=req.topic,
            mode=workflow_mode,
            max_rounds=req.max_rounds,
            extended_agents=req.extended_agents,
        )

    messages = []
    for msg in result.messages:
        eb = msg.evidence_block
        messages.append(MessageResponse(
            agent_role=msg.agent_role.value,
            msg_type=msg.msg_type.value,
            content=msg.content,
            claim=eb.claim if eb else "",
            evidence=eb.evidence if eb else "",
            risk=eb.risk if eb else "",
            next_step=eb.next_step if eb else "",
        ))

    decision = None
    if result.decision:
        d = result.decision
        decision = DecisionResponse(
            summary=d.summary,
            chosen_option=d.chosen_option,
            reasoning=d.reasoning,
            status=d.status.value,
        )

    tasks = []
    for t in result.tasks:
        tasks.append(TaskResponse(
            objective=t.objective,
            definition_of_done=t.definition_of_done,
            assignee_roles=[r.value for r in t.assignee_roles],
            status=t.status.value,
        ))

    return DiscussResponse(
        success=result.success,
        thread_id=result.thread.id if result.thread else "",
        messages=messages,
        decision=decision,
        tasks=tasks,
        error=result.error,
    )


# ── SSE 流式讨论端点 ─────────────────────────

def _format_sse(event: str, data: dict) -> str:
    """格式化 SSE 事件"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _message_to_sse(msg: Message) -> str:
    """将 Message 转换为 SSE message 事件"""
    eb = msg.evidence_block
    data = {
        "role": msg.agent_role.value,
        "content": msg.content,
        "msg_type": msg.msg_type.value,
    }
    if eb:
        data.update(claim=eb.claim, evidence=eb.evidence, risk=eb.risk, next_step=eb.next_step)
    return _format_sse("message", data)


@router.post("/discuss/stream")
async def discuss_stream(req: DiscussRequest):
    """SSE 流式讨论 - 实时推送每条消息"""
    from ..workflow.pipeline import Pipeline
    from .server import get_pipeline

    mode_map = {
        "debate": WorkflowMode.DEBATE,
        "pair": WorkflowMode.PAIR_PROGRAMMING,
        "redblue": WorkflowMode.RED_BLUE_TEAM,
        "spec": WorkflowMode.SPEC_FIRST,
        "tdd": WorkflowMode.TDD_LOOP,
    }
    workflow_mode = mode_map.get(req.mode, WorkflowMode.DEBATE)

    use_temp = bool(req.provider or req.model)
    pipeline = get_pipeline()

    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    async def _on_message(msg: Message) -> None:
        """消息总线订阅回调：将消息推入队列"""
        await queue.put({"type": "message", "msg": msg})

    async def _run_discussion() -> None:
        """后台执行讨论，结束后向队列发送哨兵值"""
        target_pipeline = pipeline
        try:
            if use_temp:
                target_pipeline = Pipeline(
                    llm_provider=req.provider,
                    llm_model=req.model,
                )
                await target_pipeline.setup()

            # 注册全局订阅者
            target_pipeline.bus.subscribe_all(_on_message)

            result = await target_pipeline.run_discussion(
                topic=req.topic,
                mode=workflow_mode,
                max_rounds=req.max_rounds,
                extended_agents=req.extended_agents,
            )

            # 发送决策事件
            if result.decision:
                d = result.decision
                await queue.put({"type": "decision", "data": {
                    "summary": d.summary,
                    "chosen_option": d.chosen_option,
                    "reasoning": d.reasoning,
                    "status": d.status.value,
                }})

            # 发送任务事件
            if result.tasks:
                await queue.put({"type": "tasks", "data": {
                    "tasks": [
                        {
                            "objective": t.objective,
                            "definition_of_done": t.definition_of_done,
                            "assignee_roles": [r.value for r in t.assignee_roles],
                            "status": t.status.value,
                        }
                        for t in result.tasks
                    ],
                }})

            # 发送完成事件
            thread_id = result.thread.id if result.thread else ""
            await queue.put({"type": "done", "data": {
                "thread_id": thread_id,
                "success": result.success,
                "error": result.error,
            }})

        except Exception as e:
            logger.error("[SSE] Discussion failed: %s", e, exc_info=True)
            await queue.put({"type": "error", "data": {"error": str(e)}})
        finally:
            # 哨兵值：通知生成器结束
            await queue.put(None)
            # 清理订阅
            try:
                target_pipeline.bus._global_subs.remove(_on_message)
            except ValueError:
                pass
            if use_temp:
                await target_pipeline.teardown()

    async def _event_generator():
        """SSE 事件生成器"""
        task = asyncio.create_task(_run_discussion())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                if item["type"] == "message":
                    yield _message_to_sse(item["msg"])
                elif item["type"] in ("decision", "tasks", "done", "error"):
                    yield _format_sse(item["type"], item["data"])
        except asyncio.CancelledError:
            task.cancel()
            raise
        finally:
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/threads", response_model=list[ThreadListItem])
async def list_threads():
    """列出所有讨论线程"""
    from .server import get_pipeline
    pipeline = get_pipeline()
    threads = await pipeline.storage.list_threads()
    return [
        ThreadListItem(
            id=t.id, topic=t.topic,
            mode=t.mode.value, status=t.status.value,
        )
        for t in threads
    ]


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str):
    """获取线程内所有消息"""
    from .server import get_pipeline
    pipeline = get_pipeline()
    messages = await pipeline.storage.get_thread_messages(thread_id)
    if not messages:
        raise HTTPException(404, "Thread not found")

    return [
        MessageResponse(
            agent_role=m.agent_role.value,
            msg_type=m.msg_type.value,
            content=m.content,
            claim=m.evidence_block.claim if m.evidence_block else "",
            evidence=m.evidence_block.evidence if m.evidence_block else "",
            risk=m.evidence_block.risk if m.evidence_block else "",
            next_step=m.evidence_block.next_step if m.evidence_block else "",
        )
        for m in messages
    ]


@router.get("/threads/{thread_id}/export")
async def export_thread(thread_id: str):
    """导出讨论为 Markdown"""
    from ..tools.exporter import MarkdownExporter
    from .server import get_pipeline

    pipeline = get_pipeline()
    thread = await pipeline.storage.get_thread(thread_id)
    if not thread:
        raise HTTPException(404, "Thread not found")

    messages = await pipeline.storage.get_thread_messages(thread_id)
    decision = await pipeline.storage.get_thread_decision(thread_id)
    tasks = await pipeline.storage.get_thread_tasks(thread_id)

    md = await MarkdownExporter.export_thread(thread, messages, decision, tasks)

    return Response(
        content=md,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="discussion-{thread_id}.md"',
        },
    )


@router.get("/config")
async def get_config():
    """返回当前配置（不含完整 API Key，只显示是否已配置）"""
    return {
        "default_provider": config.DEFAULT_LLM_PROVIDER,
        "providers": {
            "github": {
                "configured": bool(config.GITHUB_TOKEN),
                "model": config.GITHUB_MODELS_MODEL,
            },
            "openai": {"configured": bool(config.OPENAI_API_KEY), "model": config.OPENAI_MODEL},
            "gemini": {"configured": bool(config.GEMINI_API_KEY), "model": config.GEMINI_MODEL},
            "claude": {"configured": bool(config.CLAUDE_API_KEY), "model": config.CLAUDE_MODEL},
        }
    }


@router.post("/config")
async def update_config(body: dict):
    """运行时更新 API Key 和模型配置（不持久化到 .env，仅当前会话有效）"""
    if "github_token" in body:
        config.GITHUB_TOKEN = body["github_token"]
    if "openai_api_key" in body:
        config.OPENAI_API_KEY = body["openai_api_key"]
    if "openai_base_url" in body:
        config.OPENAI_BASE_URL = body["openai_base_url"]
    if "gemini_api_key" in body:
        config.GEMINI_API_KEY = body["gemini_api_key"]
    if "claude_api_key" in body:
        config.CLAUDE_API_KEY = body["claude_api_key"]
    return {"success": True, "message": "配置已更新（仅当前会话有效）"}


@router.get("/providers")
async def list_providers():
    """列出可用的 LLM Provider"""
    from ..llm.factory import list_providers
    return {"providers": list_providers()}


@router.get("/roles")
async def list_roles():
    """列出所有 Agent 角色"""
    from ..core.models import Role
    return {"roles": [r.value for r in Role]}


@router.get("/modes")
async def list_modes():
    """列出所有协作模式"""
    return {
        "modes": [
            {"id": "debate", "name": "Debate → Synthesize", "desc": "辩论后综合"},
            {"id": "pair", "name": "Pair Programming", "desc": "结对编码"},
            {"id": "redblue", "name": "Red/Blue Team", "desc": "攻防模式"},
            {"id": "spec", "name": "Spec-first", "desc": "契约优先"},
            {"id": "tdd", "name": "TDD Loop", "desc": "测试驱动闭环"},
        ]
    }


@router.get("/memory")
async def get_memories(
    keyword: str = "",
    tags: str = "",
    limit: int = 10,
):
    """检索项目记忆，支持 keyword 和 tags（逗号分隔）过滤"""
    from .server import get_pipeline
    pipeline = get_pipeline()
    if not pipeline.memory:
        return {"memories": []}
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    memories = await pipeline.memory.recall(keyword=keyword, tags=tag_list, limit=limit)
    return {"memories": memories}


@router.get("/memory/summary")
async def get_memory_summary():
    """返回记忆统计摘要"""
    from .server import get_pipeline
    pipeline = get_pipeline()
    if not pipeline.memory:
        return {"total": 0, "active": 0, "archived": 0,
                "by_type": {}, "by_importance": {}, "all_tags": [], "latest_at": None}
    return await pipeline.memory.get_summary()


@router.get("/memory/related")
async def get_related_memories(topic: str, limit: int = 5):
    """搜索与 topic 相关的记忆"""
    from .server import get_pipeline
    pipeline = get_pipeline()
    if not pipeline.memory:
        return {"memories": []}
    memories = await pipeline.memory.find_related(topic=topic, limit=limit)
    return {"memories": memories}
