"""Coder Agent — 开发角色"""

from ..core.models import AgentConfig, Role
from .base import BaseAgent

DEFAULT_CODER_PROMPT = """你是一位高级软件开发工程师。

你的职责：
1. 根据需求和架构设计编写高质量代码
2. 提供实现说明和技术细节
3. 自测代码逻辑的正确性
4. 遵循最佳实践和代码规范

你的输出应包含：
- 代码实现（完整、可运行）
- 实现说明（设计选择的理由）
- 自测结果（运行了哪些基本验证）
- 已知限制和待优化点

始终用证据（代码运行结果、测试通过情况）支持你的主张。
优先保证代码正确性，其次考虑性能和可读性。"""


def create_coder_agent(llm, bus, **kwargs) -> BaseAgent:
    config = AgentConfig(
        name="Coder Agent",
        role=Role.CODER,
        system_prompt=kwargs.pop("system_prompt", DEFAULT_CODER_PROMPT),
        weight=1.0,
        **kwargs,
    )
    return BaseAgent(config=config, llm=llm, bus=bus)
