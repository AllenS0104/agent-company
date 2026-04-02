"""全局配置管理"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def _find_env_file() -> Path | None:
    """从当前目录向上查找 .env 文件"""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        env_file = parent / ".env"
        if env_file.exists():
            return env_file
    return None


def _safe_int(env_var: str, default: int) -> int:
    """安全解析整数环境变量，失败时使用默认值并记录警告"""
    raw = os.getenv(env_var)
    if raw is None:
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        logger.warning(
            "环境变量 %s 的值 '%s' 不是有效整数，使用默认值 %d",
            env_var, raw, default,
        )
        return default


# 自动加载 .env
_env_file = _find_env_file()
if _env_file:
    load_dotenv(_env_file)


class Config:
    """应用配置（从环境变量读取）"""

    # GitHub Models API（推荐）
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_MODELS_MODEL: str = os.getenv("GITHUB_MODELS_MODEL", "openai/gpt-4.1")
    GITHUB_MODELS_BASE_URL: str = "https://models.github.ai/inference"

    # GitHub OAuth (可选，用于 Device Flow 登录)
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")

    # LLM
    DEFAULT_LLM_PROVIDER: str = os.getenv("DEFAULT_LLM_PROVIDER", "github")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4.1")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash")
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4.6")

    # 讨论设置
    MAX_DISCUSSION_ROUNDS: int = _safe_int("MAX_DISCUSSION_ROUNDS", 3)
    MAX_MESSAGE_LENGTH: int = _safe_int("MAX_MESSAGE_LENGTH", 2000)

    # 路径
    DB_PATH: str = os.getenv("DB_PATH", "agent_company.db")
    ARTIFACTS_DIR: str = os.getenv("ARTIFACTS_DIR", ".artifacts")

    # 日志
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


config = Config()
