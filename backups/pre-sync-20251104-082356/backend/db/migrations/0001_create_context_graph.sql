PRAGMA foreign_keys = ON;

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

CREATE TABLE IF NOT EXISTS edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    relation TEXT,
    weight REAL DEFAULT 1.0,
    FOREIGN KEY(source) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY(target) REFERENCES nodes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nodes_workspace ON nodes(workspace_id);
CREATE INDEX IF NOT EXISTS idx_nodes_last_touched ON nodes(last_touched);
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source);
