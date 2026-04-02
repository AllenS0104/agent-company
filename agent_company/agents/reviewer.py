"""Reviewer Agent — 审查角色"""

from ..core.models import AgentConfig, Role
from .base import BaseAgent

DEFAULT_REVIEWER_PROMPT = """你是一位严谨的代码审查专家和质量把关者。

你的职责：
1. 审查方案和代码的正确性、可维护性、安全性
2. 找出潜在的 bug、边界问题和逻辑漏洞
3. 提出重构建议，确保代码风格一致性
4. 质疑不充分的论证，要求补充证据

你的输出应包含：
- 审查意见（按严重程度分级：Critical / Major / Minor）
- 具体问题描述和修改建议
- 好的设计/实现的肯定
- 是否通过审查的结论

你是团队的"质疑者"——你的存在是为了提高质量。
始终用证据（代码逻辑分析、最佳实践引用、历史教训）支持你的审查意见。
你有较高的仲裁权重（1.3）。"""


def create_reviewer_agent(llm, bus, **kwargs) -> BaseAgent:
    config = AgentConfig(
        name="Reviewer Agent",
        role=Role.REVIEWER,
        system_prompt=kwargs.pop("system_prompt", DEFAULT_REVIEWER_PROMPT),
        weight=1.3,  # 审查者在仲裁中有较高权重
        **kwargs,
    )
    return BaseAgent(config=config, llm=llm, bus=bus)
