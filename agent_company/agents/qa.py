"""QA Agent — 测试角色"""

from ..core.models import AgentConfig, Role
from .base import BaseAgent

DEFAULT_QA_PROMPT = """你是一位经验丰富的 QA 测试工程师。

你的职责：
1. 根据需求和实现生成全面的测试用例
2. 编写单元测试和集成测试代码
3. 分析测试覆盖率，找出覆盖盲区
4. 提出边界条件和异常场景的测试建议

你的输出应包含：
- 测试用例清单（正向/反向/边界/异常）
- 测试代码（pytest 格式）
- 覆盖率分析与建议
- 复现步骤（如果发现 bug）

你有较高的仲裁权重（1.3），因为质量是底线。
始终用测试结果作为证据支持你的主张。"""


def create_qa_agent(llm, bus, **kwargs) -> BaseAgent:
    config = AgentConfig(
        name="QA Agent",
        role=Role.QA,
        system_prompt=kwargs.pop("system_prompt", DEFAULT_QA_PROMPT),
        weight=1.3,
        **kwargs,
    )
    return BaseAgent(config=config, llm=llm, bus=bus)
