"""Rich 终端美化显示"""

from __future__ import annotations

from contextlib import contextmanager

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..core.models import Decision, Message, Role, TaskCard
from ..workflow.base import WorkflowResult

# 角色颜色映射
ROLE_COLORS: dict[Role, str] = {
    Role.IDEA: "bright_yellow",
    Role.ARCHITECT: "bright_blue",
    Role.CODER: "bright_green",
    Role.REVIEWER: "bright_red",
    Role.QA: "bright_magenta",
    Role.SECURITY: "red",
    Role.DEVOPS: "bright_yellow",
    Role.PERF: "bright_cyan",
    Role.DOCS: "white",
    Role.PLANNER: "yellow",
    Role.MODERATOR: "cyan",
    Role.JUDGE: "bright_white",
}

ROLE_EMOJI: dict[Role, str] = {
    Role.IDEA: "💡",
    Role.ARCHITECT: "🏗️",
    Role.CODER: "💻",
    Role.REVIEWER: "🔍",
    Role.QA: "🧪",
    Role.SECURITY: "🔒",
    Role.DEVOPS: "🚀",
    Role.PERF: "⚡",
    Role.DOCS: "📝",
    Role.PLANNER: "📋",
    Role.MODERATOR: "🎙️",
    Role.JUDGE: "⚖️",
}


class DisplayManager:
    """终端显示管理器"""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def show_banner(self):
        self.console.print(Panel.fit(
            "[bold bright_blue]🏢 Agent Company[/bold bright_blue]\n"
            "[dim]多AI协作讨论与执行框架[/dim]",
            border_style="bright_blue",
        ))

    def show_topic(self, topic: str, rounds: int):
        self.console.print(f"\n📋 [bold]讨论主题:[/bold] {topic}")
        self.console.print(f"🔄 [bold]最大轮次:[/bold] {rounds}\n")

    @contextmanager
    def progress(self, description: str = "处理中..."):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            progress.add_task(description, total=None)
            yield progress

    def show_messages(self, messages: list[Message]):
        self.console.print("\n" + "=" * 60)
        self.console.print("[bold]📝 讨论过程[/bold]")
        self.console.print("=" * 60)

        for msg in messages:
            color = ROLE_COLORS.get(msg.agent_role, "white")
            emoji = ROLE_EMOJI.get(msg.agent_role, "🤖")
            role_label = msg.agent_role.value.upper()

            self.console.print(f"\n{emoji} [{color} bold][{role_label}][/{color} bold]")
            # 截断过长内容
            content = msg.content
            if len(content) > 500:
                content = content[:500] + "...(省略)"
            self.console.print(Panel(content, border_style=color, expand=False))

            if msg.has_evidence and msg.evidence_block:
                eb = msg.evidence_block
                self.console.print(f"  📌 [bold]Claim:[/bold] {eb.claim[:100]}")
                self.console.print(f"  📊 [bold]Evidence:[/bold] {eb.evidence[:100]}")
                if eb.risk:
                    self.console.print(f"  ⚠️  [bold]Risk:[/bold] {eb.risk[:100]}")

    def show_decision(self, decision: Decision):
        self.console.print("\n" + "=" * 60)
        self.console.print("[bold]⚖️ 最终决策[/bold]")
        self.console.print("=" * 60)

        self.console.print(Panel(
            f"[bold]摘要:[/bold] {decision.summary}\n\n"
            f"[bold]选择:[/bold] {decision.chosen_option}\n\n"
            f"[bold]理由:[/bold] {decision.reasoning}",
            title="Decision",
            border_style="bright_white",
        ))

    def show_tasks(self, tasks: list[TaskCard]):
        self.console.print("\n" + "=" * 60)
        self.console.print("[bold]📋 任务计划[/bold]")
        self.console.print("=" * 60)

        table = Table(show_header=True, header_style="bold")
        table.add_column("#", style="dim")
        table.add_column("目标", style="bright_white")
        table.add_column("完成标准", style="dim")
        table.add_column("分配", style="bright_green")
        table.add_column("状态", style="yellow")

        for i, task in enumerate(tasks, 1):
            roles = ", ".join(r.value for r in task.assignee_roles)
            table.add_row(
                str(i),
                task.objective[:60],
                task.definition_of_done[:40],
                roles,
                task.status.value,
            )

        self.console.print(table)

    def show_summary(self, result: WorkflowResult):
        self.console.print("\n" + "=" * 60)
        self.console.print(Panel(
            f"✅ [bold green]讨论完成[/bold green]\n\n"
            f"📝 消息总数: {len(result.messages)}\n"
            f"📋 生成任务: {len(result.tasks)}\n"
            f"{'⚖️ 决策已形成' if result.decision else '❌ 未形成决策'}",
            title="Summary",
            border_style="green",
        ))

    def show_error(self, error: str):
        self.console.print(Panel(
            f"❌ [bold red]讨论失败[/bold red]\n\n{error}",
            border_style="red",
        ))

    def show_roles(self, roles: list[Role]):
        self.console.print("\n🏢 [bold]可用的 Agent 角色:[/bold]\n")
        for role in roles:
            emoji = ROLE_EMOJI.get(role, "🤖")
            color = ROLE_COLORS.get(role, "white")
            self.console.print(f"  {emoji} [{color}]{role.value:12s}[/{color}]")
        self.console.print()
