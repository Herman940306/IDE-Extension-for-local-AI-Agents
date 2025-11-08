"""Lightweight retrieval tracing for observability and debugging.

Stores a bounded ring buffer of retrieval events with per-document scores.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import asdict, dataclass
from typing import Any, Deque, Dict, List, Optional


@dataclass
class RetrievalDocTrace:
    file: Optional[str]
    vector_score: float
    lexical_score: float
    fusion_score: float
    kept_after_threshold: bool
    extras: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RetrievalTraceBuffer:
    """Thread-safe ring buffer for retrieval traces."""

    def __init__(self, maxlen: int = 500) -> None:
        self._buf: Deque[RetrievalDocTrace] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, trace: RetrievalDocTrace) -> None:
        with self._lock:
            self._buf.append(trace)

    def snapshot(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            items = list(self._buf)[-limit:]
        return [t.to_dict() for t in items]

    def clear(self) -> None:
        with self._lock:
            self._buf.clear()


# Global buffer used by orchestrator and debug endpoint
retrieval_trace_buffer = RetrievalTraceBuffer(maxlen=1000)

__all__ = [
    "RetrievalTraceBuffer",
    "RetrievalDocTrace",
    "retrieval_trace_buffer",
]
