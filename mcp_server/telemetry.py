from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


def _log_paths() -> tuple[Path, Path]:
    log_dir = Path(os.getenv("MCP_TOOL_SPANS_DIR", "logs"))
    return log_dir, log_dir / "mcp_tool_spans.jsonl"


@dataclass
class ToolSpan:
    timestamp_ms: int
    tool_name: str
    method: Optional[str]
    duration_ms: int
    success: bool
    error_code: Optional[str]


def emit_span(
    tool_name: str,
    start_time: float,
    method: Optional[str] = None,
    success: bool = True,
    error_code: Optional[str] = None,
) -> None:
    log_dir, log_file = _log_paths()
    log_dir.mkdir(parents=True, exist_ok=True)
    end = time.perf_counter()
    span = ToolSpan(
        timestamp_ms=int(time.time() * 1000),
        tool_name=tool_name,
        method=method,
        duration_ms=int((end - start_time) * 1000),
        success=success,
        error_code=error_code,
    )
    with log_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(span), ensure_ascii=False) + "\n")
