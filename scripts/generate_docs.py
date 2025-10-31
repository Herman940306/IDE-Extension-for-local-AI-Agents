"""
Minimal documentation refresh script.

This placeholder aggregates a simple status note into work/docs to indicate that
the doc refresh step ran successfully. It avoids heavy dependencies (mkdocs/sphinx)
and keeps CI stable while leaving room to plug in a richer generator later.

Behavior:
- Ensures work/docs exists
- Writes a timestamped marker file with a brief summary

Exit codes:
- 0 on success (always)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    docs_dir = repo_root / "work" / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
    marker = docs_dir / f"DOC_REFRESH_{ts}.md"

    content = (
        "# Documentation refresh\n\n"
        f"- Timestamp (UTC): {ts}\n"
        "- Status: Placeholder doc refresh completed.\n\n"
        "This script is a minimal stub. Replace with a real documentation pipeline\n"
        "(e.g., mkdocs, sphinx, or pdoc) when ready.\n"
    )

    # Write with UTF-8 to be Windows-safe and emoji-safe
    marker.write_text(content, encoding="utf-8")

    # Also emit a short console message for CI logs
    print(f"Docs refreshed placeholder written to: {marker}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - defensive fallback
        # Do not fail CI on doc refresh issues
        print(f"Doc refresh encountered a non-fatal error: {exc}", file=sys.stderr)
        raise SystemExit(0)
