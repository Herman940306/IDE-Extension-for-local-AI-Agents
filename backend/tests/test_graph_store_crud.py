import importlib
import sys
import time
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.append(str(SRC_ROOT))

GraphStore = importlib.import_module("src.services.context.graph_store").GraphStore


@pytest.mark.asyncio
async def test_graph_store_node_edge_crud(tmp_path):
    db_file = str(tmp_path / "context_graph.db")
    store = GraphStore(db_file)
    await store.connect()

    try:
        node_a = {
            "id": "node:a",
            "type": "file",
            "title": "a.py",
            "content_preview": "def foo(): pass",
            "metadata": {"language": "python"},
            "workspace_id": "ws1",
            "last_touched": time.time(),
            "importance_score": 1.0,
            "embedding_ref": None,
        }
        await store.add_node(**node_a)

        res_a = await store.get_node("node:a")
        assert res_a is not None
        assert res_a["id"] == "node:a"
        assert res_a["workspace_id"] == "ws1"
        assert res_a["metadata"]["language"] == "python"

        node_b = {
            "id": "node:b",
            "type": "file",
            "title": "b.py",
            "content_preview": "def bar(): pass",
            "metadata": {"language": "python"},
            "workspace_id": "ws1",
            "last_touched": time.time(),
            "importance_score": 0.75,
            "embedding_ref": None,
        }
        await store.add_node(**node_b)
        edge_id = await store.add_edge(
            "node:a",
            "node:b",
            relation="imports",
            weight=0.9,
        )
        assert edge_id > 0

        neighbors = await store.get_neighbors("node:a", workspace_id="ws1", limit=10)
        assert any(nb["id"] == "node:b" for nb in neighbors)

        await store.upsert_embedding_ref("node:b", "vec_ref_b")
        node_b_row = await store.get_node("node:b")
        assert node_b_row["embedding_ref"] == "vec_ref_b"

        nodes = await store.list_nodes_for_workspace("ws1", limit=10)
        assert len(nodes) >= 2

        await store.delete_node("node:b")
        res_b = await store.get_node("node:b")
        assert res_b is None

    finally:
        await store.disconnect()
