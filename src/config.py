"""Typed TOML config loader for chinese-anki."""

from __future__ import annotations

import dataclasses
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    """Raised when the configuration file is invalid or missing required values."""


@dataclass
class ProviderConfig:
    name: str = "deepseek"
    model: str = "deepseek-chat"
    temperature: float | None = None
    max_tokens: int | None = None
    api_key: str = ""


@dataclass
class PipelineConfig:
    chunk_size: int = 6
    max_workers: int = 2
    retry_attempts: int = 3
    continue_on_error: bool = True


@dataclass
class OutputConfig:
    markdown_root: str = "io/output_md"
    anki_root: str = "io/output_apkg"


@dataclass
class AnkiConnectConfig:
    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 8765


@dataclass
class AppConfig:
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    anki_connect: AnkiConnectConfig = field(default_factory=AnkiConnectConfig)


def _resolve_env_string(value: str) -> str:
    """Resolve 'env:VAR_NAME' references to their environment variable values."""
    if value.startswith("env:"):
        var_name = value[4:]
        env_val = os.getenv(var_name)
        if env_val is None:
            raise ConfigError(
                f"Environment variable '{var_name}' referenced in config is not set"
            )
        return env_val
    return value


def _make_dataclass(cls: type, data: dict) -> object:
    """Instantiate a dataclass from a dict, filtering to known fields only."""
    known = {f.name for f in dataclasses.fields(cls)}
    filtered = {k: v for k, v in data.items() if k in known}
    return cls(**filtered)


def load_config(config_path: str | Path) -> AppConfig:
    """Load and validate an AppConfig from a TOML file."""
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with path.open("rb") as fh:
        data = tomllib.load(fh)

    provider_data = dict(data.get("provider", {}))
    if "api_key" in provider_data and isinstance(provider_data["api_key"], str):
        provider_data["api_key"] = _resolve_env_string(provider_data["api_key"])

    return AppConfig(
        provider=_make_dataclass(ProviderConfig, provider_data),  # type: ignore[arg-type]
        pipeline=_make_dataclass(PipelineConfig, data.get("pipeline", {})),  # type: ignore[arg-type]
        output=_make_dataclass(OutputConfig, data.get("output", {})),  # type: ignore[arg-type]
        anki_connect=_make_dataclass(AnkiConnectConfig, data.get("anki_connect", {})),  # type: ignore[arg-type]
    )
