"""Provider registry for pluggable AI backends."""

from __future__ import annotations

from typing import Callable

_registry: dict[str, type | Callable] = {}


def register(name: str, provider_cls: type | Callable) -> None:
    _registry[name] = provider_cls


def get_provider(name: str, **kwargs) -> Callable[[list[str]], str]:
    cls = _registry.get(name)
    if cls is None:
        raise ValueError(f"Unknown provider '{name}'. Registered: {list(_registry)}")
    return cls(**kwargs) if isinstance(cls, type) else cls


def list_providers() -> list[str]:
    return list(_registry)
