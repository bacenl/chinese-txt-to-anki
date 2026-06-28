"""Tests for the typed TOML config module (Task 4.1)."""

import pytest

from src.config import AppConfig, ConfigError, load_config


# ---------------------------------------------------------------------------
# Basic loading
# ---------------------------------------------------------------------------


def test_config_loads_provider_section(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[provider]\nname = "openai"\nmodel = "gpt-4o-mini"\n',
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.provider.name == "openai"
    assert config.provider.model == "gpt-4o-mini"


def test_config_loads_pipeline_section(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        "[pipeline]\nchunk_size = 10\nmax_workers = 4\nretry_attempts = 2\n",
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.pipeline.chunk_size == 10
    assert config.pipeline.max_workers == 4
    assert config.pipeline.retry_attempts == 2


def test_config_loads_output_section(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[output]\nmarkdown_root = "io/md"\nanki_root = "io/apkg"\n',
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.output.markdown_root == "io/md"
    assert config.output.anki_root == "io/apkg"


def test_config_loads_anki_connect_section(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[anki_connect]\nenabled = true\nhost = "localhost"\nport = 8765\n',
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.anki_connect.enabled is True
    assert config.anki_connect.host == "localhost"
    assert config.anki_connect.port == 8765


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def test_empty_config_file_uses_defaults(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("", encoding="utf-8")

    config = load_config(config_file)

    assert config.pipeline.chunk_size == 6
    assert config.pipeline.max_workers == 2
    assert config.pipeline.retry_attempts == 3
    assert config.pipeline.continue_on_error is True
    assert config.anki_connect.enabled is False
    assert config.anki_connect.port == 8765


# ---------------------------------------------------------------------------
# env: prefix resolution
# ---------------------------------------------------------------------------


def test_env_prefix_resolves_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_SECRET_KEY", "resolved-value")
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[provider]\napi_key = "env:MY_SECRET_KEY"\n',
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.provider.api_key == "resolved-value"


def test_env_prefix_raises_config_error_when_var_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("ABSENT_VAR", raising=False)
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[provider]\napi_key = "env:ABSENT_VAR"\n',
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="ABSENT_VAR"):
        load_config(config_file)


def test_non_env_string_value_is_used_literally(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[provider]\napi_key = "literal-key"\n',
        encoding="utf-8",
    )

    config = load_config(config_file)

    assert config.provider.api_key == "literal-key"


# ---------------------------------------------------------------------------
# load_config return type
# ---------------------------------------------------------------------------


def test_load_config_returns_app_config_instance(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text("", encoding="utf-8")

    config = load_config(config_file)

    assert isinstance(config, AppConfig)


def test_load_config_missing_file_raises():
    with pytest.raises((FileNotFoundError, ConfigError)):
        load_config("/nonexistent/path/config.toml")
