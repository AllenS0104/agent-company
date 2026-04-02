"""Agent Company 端到端 Demo

运行方式:
    python -m examples.demo_discussion
    或
    agent-company discuss "如何设计一个高并发消息队列？"
"""

import asyncio
import logging
import os
import sys

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console

from agent_company.cli.display import DisplayManager
from agent_company.workflow.pipeline import Pipeline


async def main():
    topic = "如何设计一个高并发、低延迟的消息队列系统？要求支持百万级 QPS。"

    console = Console()
    display = DisplayManager(console)
    display.show_banner()
    display.show_topic(topic, rounds=2)

    pipeline = Pipeline()
    await pipeline.setup()

    try:
        console.print("[dim]正在启动讨论...[/dim]\n")
        result = await pipeline.run_discussion(topic, max_rounds=2)

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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s - %(message)s")
    asyncio.run(main())
