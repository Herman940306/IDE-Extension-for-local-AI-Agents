"""Utility helpers for the context subsystem scaffolding."""

from __future__ import annotations

from typing import Dict, Iterable, Optional

_DEFAULT_KEYS = ("retriever", "graph", "memory")


def normalize_merge_weights(
    weights: Optional[Dict[str, float]],
    required_keys: Iterable[str] = _DEFAULT_KEYS,
) -> Dict[str, float]:
    """Return a normalized weights dict covering required sources.

    The helper ensures every key has a non-negative weight and that the values sum
    to 1.0 when possible. If the provided weights are empty or invalid, a
    reasonable default set is returned to keep the orchestrator predictable.
    """

    if not weights:
        return {"retriever": 0.5, "graph": 0.3, "memory": 0.2}

    cleaned: Dict[str, float] = {}
    for key in required_keys:
        value = max(0.0, float(weights.get(key, 0.0)))
        cleaned[key] = value

    total = sum(cleaned.values())
    if total <= 0.0:
        return {"retriever": 0.5, "graph": 0.3, "memory": 0.2}

    return {key: value / total for key, value in cleaned.items()}
