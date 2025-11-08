"""Context subsystem package for Phase 3 scaffolding."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - import side effects deferred at runtime
    from .context_engine import ContextEngine
    from .graph_store import GraphStore

__all__ = ["ContextEngine", "GraphStore"]


def __getattr__(name: str) -> Any:  # pragma: no cover - simple lazy loader
    if name == "ContextEngine":
        module = import_module("src.services.context.context_engine")
        return getattr(module, name)
    if name == "GraphStore":
        module = import_module("src.services.context.graph_store")
        return getattr(module, name)
    raise AttributeError(name)
