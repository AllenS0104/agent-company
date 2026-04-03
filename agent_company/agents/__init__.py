"""Agent 工厂函数注册"""

from .architect import create_architect_agent
from .coder import create_coder_agent
from .custom import CustomAgentStore
from .devops import create_devops_agent
from .docs import create_docs_agent
from .idea import create_idea_agent
from .perf import create_perf_agent
from .qa import create_qa_agent
from .reviewer import create_reviewer_agent
from .security import create_security_agent

__all__ = [
    "create_architect_agent",
    "create_coder_agent",
    "create_devops_agent",
    "create_docs_agent",
    "create_idea_agent",
    "create_perf_agent",
    "create_qa_agent",
    "create_reviewer_agent",
    "create_security_agent",
    "CustomAgentStore",
]
