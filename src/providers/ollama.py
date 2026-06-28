"""Ollama provider via its OpenAI-compatible endpoint."""

from __future__ import annotations

from .openai_compat import OpenAICompatibleProvider, OpenAICompatibleProviderConfig


class OllamaProvider:
    """Uses Ollama's OpenAI-compatible endpoint at localhost:11434/v1."""

    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://localhost:11434/v1",
    ) -> None:
        self._inner = OpenAICompatibleProvider(
            OpenAICompatibleProviderConfig(
                api_key="ollama",
                base_url=base_url,
                model=model,
            )
        )

    def __call__(self, words: list[str], template: str = "") -> str:
        return self._inner(words, template=template)
