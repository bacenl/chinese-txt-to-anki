"""Tests for the provider registry and pluggable backends (Task 1.1)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.providers import get_provider, list_providers, register
from src.providers import OllamaProvider, OpenAICompatibleProvider


# ---------------------------------------------------------------------------
# Registry API
# ---------------------------------------------------------------------------


def test_register_and_get_provider_returns_instance():
    class _FakeProvider:
        def __call__(self, words: list[str]) -> str:
            return "ok"

    register("_test_fake", _FakeProvider)
    provider = get_provider("_test_fake")

    assert callable(provider)
    assert provider(["word"]) == "ok"


def test_register_and_get_provider_class_is_instantiated_with_kwargs():
    class _KwargProvider:
        def __init__(self, model: str = "default"):
            self.model = model

        def __call__(self, words: list[str]) -> str:
            return self.model

    register("_test_kwarg", _KwargProvider)
    provider = get_provider("_test_kwarg", model="custom-model")

    assert provider(["word"]) == "custom-model"


def test_register_callable_is_returned_directly():
    def _plain_fn(words: list[str]) -> str:
        return "plain"

    register("_test_plain", _plain_fn)
    provider = get_provider("_test_plain")

    assert provider is _plain_fn


def test_get_unknown_provider_raises_value_error():
    with pytest.raises(ValueError, match="unknown_xyz"):
        get_provider("unknown_xyz")


def test_list_providers_includes_auto_registered_names():
    names = list_providers()

    assert "openai" in names
    assert "deepseek" in names
    assert "ollama" in names


def test_list_providers_returns_list():
    assert isinstance(list_providers(), list)


# ---------------------------------------------------------------------------
# Auto-registered providers are callable
# ---------------------------------------------------------------------------


_OPENAI_CLS = "src.providers.openai_compat.OpenAI"


def test_openai_provider_is_callable():
    with patch(_OPENAI_CLS):
        provider = get_provider("openai", api_key="test-key")
    assert callable(provider)


def test_deepseek_provider_is_callable():
    with patch(_OPENAI_CLS):
        provider = get_provider("deepseek", api_key="test-key")
    assert callable(provider)


# ---------------------------------------------------------------------------
# OllamaProvider
# ---------------------------------------------------------------------------


def test_ollama_provider_delegates_to_openai_compat():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "# 你好"

    with patch(_OPENAI_CLS) as mock_openai_cls, \
         patch("src.providers.openai_compat.create_prompt", return_value="prompt: 你好"):
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        provider = OllamaProvider(model="qwen2.5:7b")
        result = provider(["你好"])

    assert result == "# 你好"
    mock_client.chat.completions.create.assert_called_once()


def test_ollama_provider_uses_localhost_base_url():
    with patch(_OPENAI_CLS) as mock_openai_cls:
        OllamaProvider()
        call_kwargs = mock_openai_cls.call_args[1]

    assert "localhost" in call_kwargs.get("base_url", "")


def test_ollama_provider_default_model_is_qwen():
    with patch(_OPENAI_CLS):
        provider = OllamaProvider()

    assert "qwen" in provider._inner.config.model


def test_ollama_provider_custom_model_and_url():
    with patch(_OPENAI_CLS):
        provider = OllamaProvider(model="llama3", base_url="http://remote:11434/v1")

    assert provider._inner.config.model == "llama3"
    assert provider._inner.config.base_url == "http://remote:11434/v1"


# ---------------------------------------------------------------------------
# Ollama integration (skipped unless OLLAMA_INTEGRATION_TEST=1)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not __import__("os").getenv("OLLAMA_INTEGRATION_TEST"),
    reason="OLLAMA_INTEGRATION_TEST not set",
)
def test_ollama_provider_real_call():
    provider = OllamaProvider()
    result = provider(["你好"])
    assert isinstance(result, str)
    assert len(result) > 0
