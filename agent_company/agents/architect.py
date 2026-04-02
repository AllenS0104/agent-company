"""Architect Agent — 架构角色"""

from ..core.models import AgentConfig, Role
from .base import BaseAgent

DEFAULT_ARCHITECT_PROMPT = """你是一位资深软件架构师。

你的职责：
1. 分析需求并提出 2-3 个架构方案进行对比
2. 评估每个方案的优缺点、成本和风险
3. 定义模块划分和接口契约
4. 识别技术风险并提出缓解策略

你的输出应包含：
- 方案对比（至少 2 个备选方案）
- 每个方案的优缺点分析
- 推荐方案及理由
- 接口契约 / 模块划分建议
- 风险清单

你有较高的仲裁权重。决策时你的意见权重为 1.5。
始终用证据（基准测试方案、架构原则、类似系统经验）支持你的主张。"""


def create_architect_agent(llm, bus, **kwargs) -> BaseAgent:
    config = AgentConfig(
        name="Architect Agent",
        role=Role.ARCHITECT,
        system_prompt=kwargs.pop("system_prompt", DEFAULT_ARCHITECT_PROMPT),
        weight=1.5,  # 架构师在仲裁中有更高权重
        **kwargs,
    )
    return BaseAgent(config=config, llm=llm, bus=bus)
