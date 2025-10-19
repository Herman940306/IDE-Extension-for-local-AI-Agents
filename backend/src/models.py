"""Compatibility shim for legacy ``src.models`` imports.

This module re-exports the canonical models defined under the
``src/models/`` package so that older imports such as
``from src.models import AgentResponse`` continue to work while the
project standardises on the package-based implementation.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Dict

# Mark this module as a package so submodules (e.g. ``src.models.task``)
# remain importable even though the historical ``models.py`` file still exists.
__path__ = [str(Path(__file__).with_name("models"))]

# Load the canonical package implementation and mirror its public API.
_package = importlib.import_module("src.models.__init__")


def _export_public_symbols(package_module: Any) -> Dict[str, Any]:
    exported: Dict[str, Any] = {}
    public_names = getattr(package_module, "__all__", None)

    if public_names is None:
        public_names = [
            name for name in dir(package_module) if not name.startswith("_")
        ]

    for name in public_names:
        exported[name] = getattr(package_module, name)

    return exported


_public_symbols = _export_public_symbols(_package)

globals().update(_public_symbols)
globals()["__all__"] = getattr(_package, "__all__", tuple(_public_symbols))
