"""Model provider adapters for card generation."""

from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI

from .api import create_prompt


@dataclass(frozen=True)
class OpenAICompatibleProviderConfig:
    """Configuration for an OpenAI-compatible chat completions provider."""

    api_key: str
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"


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
        return cls(
            OpenAICompatibleProviderConfig(
                api_key=api_key,
                base_url=os.getenv(base_url_env, "https://api.deepseek.com"),
                model=os.getenv(model_env, "deepseek-chat"),
            )
        )

    def __call__(self, words: list[str]) -> str:
        """Generate markdown card content for one chunk of vocab words."""

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": "user", "content": create_prompt(words)}],
            stream=False,
        )
        return response.choices[0].message.content or ""
