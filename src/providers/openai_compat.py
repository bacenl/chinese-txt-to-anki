"""OpenAI-compatible chat completions provider."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from ..api import create_prompt


@dataclass(frozen=True)
class OpenAICompatibleProviderConfig:
    """Configuration for an OpenAI-compatible chat completions provider."""

    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float | None = None
    max_tokens: int | None = None


class OpenAICompatibleProvider:
    """Callable provider backed by OpenAI-compatible chat completions."""

    def __init__(self, config: OpenAICompatibleProviderConfig) -> None:
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url)

    @classmethod
    def from_env(
        cls,
        *,
        api_key_env: str = "MODEL_API_KEY",
        fallback_api_key_env: str = "DEEPSEEK_API_KEY",
        base_url_env: str = "MODEL_BASE_URL",
        model_env: str = "MODEL_NAME",
        temperature_env: str = "MODEL_TEMPERATURE",
        max_tokens_env: str = "MODEL_MAX_TOKENS",
    ) -> "OpenAICompatibleProvider":
        """Create a provider from environment variables.

        `MODEL_API_KEY` is the provider-neutral name. `DEEPSEEK_API_KEY`
        remains supported for existing local setups.
        """
        api_key = os.getenv(api_key_env) or os.getenv(fallback_api_key_env)
        if not api_key:
            raise ValueError(
                f"Please set {api_key_env} or {fallback_api_key_env} environment variable"
            )
        temperature = os.getenv(temperature_env)
        max_tokens = os.getenv(max_tokens_env)
        return cls(
            OpenAICompatibleProviderConfig(
                api_key=api_key,
                base_url=os.getenv(base_url_env, "https://api.deepseek.com"),
                model=os.getenv(model_env, "deepseek-chat"),
                temperature=float(temperature) if temperature else None,
                max_tokens=int(max_tokens) if max_tokens else None,
            )
        )

    def __call__(self, words: list[str], template: str = "") -> str:
        """Generate markdown card content for one chunk of vocab words."""
        if template:
            prompt = template.replace("{words_text}", "\n".join(words))
        else:
            prompt = create_prompt(words)

        request: dict[str, Any] = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        if self.config.temperature is not None:
            request["temperature"] = self.config.temperature
        if self.config.max_tokens is not None:
            request["max_tokens"] = self.config.max_tokens

        response = self.client.chat.completions.create(**request)
        return response.choices[0].message.content or ""
