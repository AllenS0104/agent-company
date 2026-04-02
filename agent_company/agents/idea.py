"""Idea Agent — 产品/需求角色"""

from ..core.models import AgentConfig, Role
from .base import BaseAgent

DEFAULT_IDEA_PROMPT = """你是一位经验丰富的产品经理 / 需求分析师。

你的职责：
1. 分析用户的需求，提出清晰的用户故事
2. 定义验收标准和边界条件
3. 评估优先级和价值
4. 确保问题定义明确，成功标准清晰

你的输出应包含：
- 用户故事（As a... I want... So that...）
- 验收标准（明确的通过/失败条件）
- 边界条件（什么在范围内，什么不在）
- 优先级建议

始终用证据支持你的主张。"""


def create_idea_agent(llm, bus, **kwargs) -> BaseAgent:
    config = AgentConfig(
        name="Idea Agent",
        role=Role.IDEA,
        system_prompt=kwargs.pop("system_prompt", DEFAULT_IDEA_PROMPT),
        weight=1.0,
        **kwargs,
    )
    return BaseAgent(config=config, llm=llm, bus=bus)
