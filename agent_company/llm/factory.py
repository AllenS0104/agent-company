"""LLM Provider 工厂 — 根据配置创建对应的 Provider 实例"""

from __future__ import annotations

from typing import Any

from .base import LLMProvider

_REGISTRY: dict[str, type[LLMProvider]] = {}


def register_provider(name: str, cls: type[LLMProvider]) -> None:
    _REGISTRY[name] = cls


def create_provider(name: str, **kwargs: Any) -> LLMProvider:
    """根据名称创建 LLM Provider 实例

    Args:
        name: provider 名称 (openai / gemini / claude)
        **kwargs: 传递给 Provider 构造函数的参数

    Returns:
        LLMProvider 实例
    """
    if name not in _REGISTRY:
        # 惰性注册内置 provider
        _lazy_register(name)

    if name not in _REGISTRY:
        available = ", ".join(_REGISTRY.keys()) if _REGISTRY else "none"
        raise ValueError(f"Unknown LLM provider: '{name}'. Available: {available}")

    return _REGISTRY[name](**kwargs)


def _lazy_register(name: str) -> None:
    """惰性加载并注册内置 Provider，避免未安装依赖时报错"""
    try:
        if name == "github":
            from .github_provider import GitHubModelsProvider
            register_provider("github", GitHubModelsProvider)
        elif name == "openai":
            from .openai_provider import OpenAIProvider
            register_provider("openai", OpenAIProvider)
        elif name == "gemini":
            from .gemini_provider import GeminiProvider
            register_provider("gemini", GeminiProvider)
        elif name == "claude":
            from .claude_provider import ClaudeProvider
            register_provider("claude", ClaudeProvider)
    except ImportError:
        pass


def list_providers() -> list[str]:
    """列出所有可用的 Provider"""
    for name in ("github", "openai", "gemini", "claude"):
        if name not in _REGISTRY:
            _lazy_register(name)
    return list(_REGISTRY.keys())
