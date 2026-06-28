"""Provider registry and built-in provider implementations."""

from __future__ import annotations

import os

from .base import get_provider, list_providers, register
from .ollama import OllamaProvider
from .openai_compat import OpenAICompatibleProvider, OpenAICompatibleProviderConfig


class _OpenAIProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini", **kwargs) -> None:  # type: ignore[override]
        super().__init__(
            OpenAICompatibleProviderConfig(
                api_key=api_key or os.getenv("MODEL_API_KEY", ""),
                base_url="https://api.openai.com/v1",
                model=model,
            )
        )


class _DeepSeekProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str = "", model: str = "deepseek-chat", **kwargs) -> None:  # type: ignore[override]
        super().__init__(
            OpenAICompatibleProviderConfig(
                api_key=api_key
                or os.getenv("MODEL_API_KEY")
                or os.getenv("DEEPSEEK_API_KEY", ""),
                base_url="https://api.deepseek.com",
                model=model,
            )
        )


register("openai", _OpenAIProvider)
register("deepseek", _DeepSeekProvider)
register("ollama", OllamaProvider)

__all__ = [
    "get_provider",
    "list_providers",
    "register",
    "OpenAICompatibleProvider",
    "OpenAICompatibleProviderConfig",
    "OllamaProvider",
]
