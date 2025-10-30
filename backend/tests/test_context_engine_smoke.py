import importlib
import sys
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))

ContextEngine = importlib.import_module("src.services.context.context_engine").ContextEngine
GraphStore = importlib.import_module("src.services.context.graph_store").GraphStore


@pytest.mark.asyncio
async def test_context_engine_smoke_returns_empty_when_disabled():
    engine = ContextEngine(enabled=False)
    snippets = await engine.get_context_snippets("hello world")
    assert snippets == []


@pytest.mark.asyncio
async def test_context_engine_warm_start_lifecycle():
    store = GraphStore()
    engine = ContextEngine(graph_store=store, enabled=True)

    await engine.warm_start()
    assert store.is_connected

    await engine.shutdown()
    assert not store.is_connected
