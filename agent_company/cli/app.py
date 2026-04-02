"""CLI 主入口"""

from __future__ import annotations

import asyncio
import logging

import typer
from rich.console import Console

from ..workflow.pipeline import Pipeline
from .display import DisplayManager

app = typer.Typer(
    name="agent-company",
    help="🏢 Agent Company — 多AI协作讨论与执行框架",
    add_completion=False,
)
console = Console()


@app.command()
def discuss(
    topic: str = typer.Argument(..., help="讨论主题/问题"),
    rounds: int = typer.Option(3, "--rounds", "-r", help="最大讨论轮次"),
    provider: str = typer.Option(
        None, "--provider", "-p",
        help="LLM Provider (github/openai/gemini/claude)",
    ),
    model: str = typer.Option(None, "--model", "-m", help="LLM 模型名称"),
    mode: str = typer.Option(
        "debate", "--mode", "-w",
        help="协作模式 (debate/pair/redblue/spec/tdd)",
    ),
    extended: bool = typer.Option(
        False, "--extended", "-e", help="启用扩展 Agent (QA+Security)",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="显示详细日志"),
):
    """🗣️ 发起一次多 Agent 讨论"""
    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s - %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    display = DisplayManager(console)
    display.show_banner()
    display.show_topic(topic, rounds)

    workflow_mode = _parse_mode(mode)
    asyncio.run(
        _run_discussion(topic, rounds, provider, model, workflow_mode, extended, display),
    )


def _parse_mode(mode: str):
    from ..core.models import WorkflowMode
    mode_map = {
        "debate": WorkflowMode.DEBATE,
        "pair": WorkflowMode.PAIR_PROGRAMMING,
        "redblue": WorkflowMode.RED_BLUE_TEAM,
        "spec": WorkflowMode.SPEC_FIRST,
        "tdd": WorkflowMode.TDD_LOOP,
    }
    return mode_map.get(mode, WorkflowMode.DEBATE)


async def _run_discussion(
    topic: str, rounds: int, provider: str | None, model: str | None,
    workflow_mode, extended: bool, display: DisplayManager,
):
    pipeline = Pipeline(
        llm_provider=provider,
        llm_model=model,
    )
    await pipeline.setup()

    try:
        with display.progress("讨论进行中..."):
            result = await pipeline.run_discussion(
                topic, mode=workflow_mode, max_rounds=rounds,
                extended_agents=extended,
            )

        if result.success:
            display.show_messages(result.messages)
            if result.decision:
                display.show_decision(result.decision)
            if result.tasks:
                display.show_tasks(result.tasks)
            display.show_summary(result)
        else:
            display.show_error(result.error)
    finally:
        await pipeline.teardown()


@app.command()
def agents():
    """📋 列出所有可用的 Agent 角色"""
    from ..core.models import Role
    display = DisplayManager(console)
    display.show_roles(list(Role))


@app.command()
def providers():
    """🔌 列出所有可用的 LLM Provider"""
    from ..llm.factory import list_providers
    available = list_providers()
    console.print("\n🔌 [bold]可用的 LLM Providers:[/bold]")
    for p in available:
        console.print(f"  • {p}")
    if not available:
        console.print("  (未安装任何 Provider SDK)")
    console.print()


@app.command()
def modes():
    """🔄 列出所有协作模式"""
    mode_info = [
        ("debate", "Debate → Synthesize", "辩论后综合（默认）"),
        ("pair", "Pair Programming", "结对编码"),
        ("redblue", "Red/Blue Team", "攻防模式"),
        ("spec", "Spec-first", "契约优先"),
        ("tdd", "TDD Loop", "测试驱动闭环"),
    ]
    console.print("\n🔄 [bold]协作模式:[/bold]\n")
    for mid, name, desc in mode_info:
        console.print(f"  [cyan]{mid:10s}[/cyan] {name:25s} {desc}")
    console.print(
        "\n  使用: agent-company discuss --mode tdd \"问题\"\n"
    )


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="监听地址"),
    port: int = typer.Option(8000, help="监听端口"),
):
    """🌐 启动 Web API 服务"""
    console.print(f"\n🌐 启动 Web API: http://{host}:{port}")
    console.print("📖 API 文档: http://{host}:{port}/docs\n")
    from ..api.server import start_server
    start_server(host=host, port=port)


@app.command()
def memory(
    keyword: str = typer.Argument("", help="搜索关键词"),
    limit: int = typer.Option(10, help="最大返回条数"),
):
    """🧠 查看项目记忆"""
    asyncio.run(_show_memory(keyword, limit))


async def _show_memory(keyword: str, limit: int):
    from ..memory.project_memory import ProjectMemory
    mem = ProjectMemory()
    await mem.connect()
    try:
        results = await mem.recall(keyword=keyword, limit=limit)
        if not results:
            console.print("\n🧠 暂无记忆\n")
            return
        console.print(f"\n🧠 [bold]项目记忆[/bold] ({len(results)} 条)\n")
        for r in results:
            console.print(
                f"  [{r['type']}] [bold]{r['title']}[/bold]"
            )
            content = r["content"][:200]
            console.print(f"  {content}")
            console.print()
    finally:
        await mem.close()


if __name__ == "__main__":
    app()
