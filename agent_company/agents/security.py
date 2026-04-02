"""Security Agent — 安全角色"""

from ..core.models import AgentConfig, Role
from .base import BaseAgent

DEFAULT_SECURITY_PROMPT = """你是一位资深安全工程师。

你的职责：
1. 识别方案和代码中的安全风险
2. 构建威胁模型（STRIDE 框架）
3. 检查依赖项安全风险和漏洞
4. 扫描敏感信息泄露（API Key、密码、Token）
5. 提出安全加固建议

你的输出应包含：
- 威胁模型（按 STRIDE 分类）
- 安全风险清单（按严重程度：Critical/High/Medium/Low）
- 依赖项风险分析
- 加固建议和最佳实践
- 合规性检查（如适用）

你有最高的仲裁权重（1.5），因为安全没有妥协。
始终用具体的攻击场景或 CVE 引用作为证据。"""


def create_security_agent(llm, bus, **kwargs) -> BaseAgent:
    config = AgentConfig(
        name="Security Agent",
        role=Role.SECURITY,
        system_prompt=kwargs.pop("system_prompt", DEFAULT_SECURITY_PROMPT),
        weight=1.5,
        **kwargs,
    )
    return BaseAgent(config=config, llm=llm, bus=bus)
