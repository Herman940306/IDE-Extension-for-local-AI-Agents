"""SQLite-backed async graph store for context knowledge management."""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

DB_SCHEMA_VERSION = 1


class GraphStore:
    """Persist graph nodes and edges used by the context subsystem."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or "./data/context/context.db"
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Open the SQLite connection and ensure schema exists."""

        if self._conn is not None:
            return

        db_dir = os.path.dirname(os.path.abspath(self.db_path))
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = await aiosqlite.connect(self.db_path)
        self._conn = conn
        await conn.execute("PRAGMA foreign_keys = ON;")
        await self._apply_migrations()
        await conn.commit()

    async def disconnect(self) -> None:
        """Close the underlying database connection."""

        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def _apply_migrations(self) -> None:
        conn = self._require_connection()
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                title TEXT,
                content_preview TEXT,
                metadata TEXT,
                workspace_id TEXT,
                last_touched REAL,
                importance_score REAL DEFAULT 1.0,
                embedding_ref TEXT
            );
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                relation TEXT,
                weight REAL DEFAULT 1.0,
                FOREIGN KEY(source) REFERENCES nodes(id) ON DELETE CASCADE,
                FOREIGN KEY(target) REFERENCES nodes(id) ON DELETE CASCADE
            );
            """
        )
        await conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_nodes_workspace ON nodes(workspace_id);"""
        )
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_nodes_last_touched
            ON nodes(last_touched);
            """
        )
        await conn.execute(
            """CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source);"""
        )

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------
    async def add_node(self, **node_data: Any) -> None:
        node_id = node_data.get("id") or node_data.get("node_id")
        if not node_id:
            raise ValueError("node id is required")

        node_type = node_data.get("type") or node_data.get("node_type")
        if not node_type:
            raise ValueError("node type is required")

        workspace_id = node_data.get("workspace_id")
        if not workspace_id:
            raise ValueError("workspace_id is required")

        title = node_data.get("title")
        content_preview = node_data.get("content_preview")
        metadata = node_data.get("metadata") or {}
        last_touched = node_data.get("last_touched")
        importance_score = float(node_data.get("importance_score", 1.0))
        embedding_ref = node_data.get("embedding_ref")

        conn = self._require_connection()
        timestamp = last_touched or time.time()
        metadata_json = json.dumps(metadata or {})
        await conn.execute(
            """
            INSERT OR REPLACE INTO nodes (
                id,
                type,
                title,
                content_preview,
                metadata,
                workspace_id,
                last_touched,
                importance_score,
                embedding_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                node_id,
                node_type,
                title,
                content_preview,
                metadata_json,
                workspace_id,
                timestamp,
                importance_score,
                embedding_ref,
            ),
        )
        await conn.commit()

    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        conn = self._require_connection()
        cursor = await conn.execute(
            """
            SELECT
                id,
                type,
                title,
                content_preview,
                metadata,
                workspace_id,
                last_touched,
                importance_score,
                embedding_ref
            FROM nodes
            WHERE id = ?;
            """,
            (node_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if not row:
            return None
        return {
            "id": row[0],
            "type": row[1],
            "title": row[2],
            "content_preview": row[3],
            "metadata": json.loads(row[4] or "{}"),
            "workspace_id": row[5],
            "last_touched": row[6],
            "importance_score": row[7],
            "embedding_ref": row[8],
        }

    async def delete_node(self, node_id: str) -> None:
        conn = self._require_connection()
        await conn.execute("DELETE FROM nodes WHERE id = ?;", (node_id,))
        await conn.commit()

    # ------------------------------------------------------------------
    # Edge CRUD
    # ------------------------------------------------------------------
    async def add_edge(
        self,
        source: str,
        target: str,
        relation: Optional[str] = None,
        weight: float = 1.0,
    ) -> int:
        conn = self._require_connection()
        cursor = await conn.execute(
            "INSERT INTO edges (source, target, relation, weight) VALUES (?, ?, ?, ?);",
            (source, target, relation, weight),
        )
        await conn.commit()
        rowid = cursor.lastrowid
        # mypy: lastrowid can be Optional[int]; ensure it's present before returning
        if rowid is None:
            await cursor.close()
            raise RuntimeError("Failed to retrieve lastrowid after edge insert")
        await cursor.close()
        return int(rowid)

    async def get_neighbors(
        self,
        node_id: str,
        workspace_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        conn = self._require_connection()
        sql = """
        SELECT
            n.id,
            n.type,
            n.title,
            n.content_preview,
            n.metadata,
            n.workspace_id,
            n.last_touched,
            n.importance_score,
            n.embedding_ref,
            e.weight,
            e.relation
        FROM edges e
        JOIN nodes n ON e.target = n.id
        WHERE e.source = ?
        """
        params: Tuple[Any, ...] = (node_id,)
        if workspace_id:
            sql += " AND n.workspace_id = ?"
            params = (node_id, workspace_id)
        sql += " ORDER BY e.weight DESC LIMIT ?;"
        params = params + (limit,)

        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()
        await cursor.close()

        results: List[Dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "id": row[0],
                    "type": row[1],
                    "title": row[2],
                    "content_preview": row[3],
                    "metadata": json.loads(row[4] or "{}"),
                    "workspace_id": row[5],
                    "last_touched": row[6],
                    "importance_score": row[7],
                    "embedding_ref": row[8],
                    "edge_weight": row[9],
                    "relation": row[10],
                }
            )
        return results

    # ------------------------------------------------------------------
    # Embedding reference helpers
    # ------------------------------------------------------------------
    async def upsert_embedding_ref(self, node_id: str, embedding_ref: str) -> None:
        conn = self._require_connection()
        await conn.execute(
            "UPDATE nodes SET embedding_ref = ? WHERE id = ?;",
            (embedding_ref, node_id),
        )
        await conn.commit()

    # ------------------------------------------------------------------
    # Search helpers
    # ------------------------------------------------------------------
    async def list_nodes_for_workspace(
        self, workspace_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        conn = self._require_connection()
        cursor = await conn.execute(
            """
            SELECT
                id,
                type,
                title,
                content_preview,
                metadata,
                last_touched,
                importance_score,
                embedding_ref
            FROM nodes
            WHERE workspace_id = ?
            ORDER BY last_touched DESC
            LIMIT ?;
            """,
            (workspace_id, limit),
        )
        rows = await cursor.fetchall()
        await cursor.close()

        results: List[Dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "id": row[0],
                    "type": row[1],
                    "title": row[2],
                    "content_preview": row[3],
                    "metadata": json.loads(row[4] or "{}"),
                    "last_touched": row[5],
                    "importance_score": row[6],
                    "embedding_ref": row[7],
                }
            )
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _require_connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("GraphStore is not connected")
        return self._conn

    @property
    def is_connected(self) -> bool:
        return self._conn is not None
