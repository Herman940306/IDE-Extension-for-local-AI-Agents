import time
from pathlib import Path

import pytest

# Targets under test
from src.services.context_manager import ContextManager
from src.services.embeddings_service import EmbeddingsService
from src.services.memory_service import (
    MemoryConfig,
    MemoryService,
    Message,
    MessageType,
    StorageBackend,
)


@pytest.mark.asyncio
class TestContextManager:
    async def test_detect_language_and_imports(self, tmp_path: Path):
        # Arrange: create small python file
        project = tmp_path
        file_path = project / "sample.py"
        file_path.write_text(
            """
import os
from pathlib import Path

x = 1
""".strip()
        )
        cm = ContextManager(workspace_path=str(project), enable_file_watcher=False)

        # Act
        lang = cm._detect_language(file_path)
        content = await cm._read_file(file_path)
        imports = await cm._extract_imports(content, lang)

        # Assert
        assert lang == "python"
        assert any(s.startswith("import os") for s in imports)
        assert any(s.startswith("from pathlib") for s in imports)

    @pytest.mark.parametrize(
        "fname,expected",
        [
            ("index.ts", "typescript"),
            ("index.tsx", "typescript"),
            ("index.js", "javascript"),
            ("unknown.xyz", "unknown"),
        ],
    )
    async def test_detect_language_by_extension(self, tmp_path: Path, fname: str, expected: str):
        cm = ContextManager(workspace_path=str(tmp_path), enable_file_watcher=False)
        path = tmp_path / fname
        path.write_text("console.log('ok')")
        assert cm._detect_language(path) == expected

    @pytest.mark.asyncio
    async def test_get_dependencies_python_relative(self, tmp_path: Path):
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        f = pkg / "mod.py"
        f.write_text("from .utils import helper\n")
        cm = ContextManager(workspace_path=str(tmp_path), enable_file_watcher=False)
        deps = await cm._get_dependencies(f)
        assert "utils" in deps[0]


@pytest.mark.asyncio
class TestEmbeddingsService:
    async def test_embed_code_raises_before_initialize(self):
        svc = EmbeddingsService(provider="sentence-transformers")
        with pytest.raises(RuntimeError):
            await svc.embed_code("print('hi')")

    async def test_initialize_and_embed_with_mock(self, monkeypatch):
        # Avoid heavy deps by monkeypatching the SentenceTransformer and Chroma flags
        class DummyModel:
            def encode(
                self,
                text,
                convert_to_numpy=True,
                batch_size: int | None = None,
            ):
                if isinstance(text, list):
                    return [[0.1, 0.2, 0.3] for _ in text]
                return [0.1, 0.2, 0.3]

        import src.services.embeddings_service as es

        monkeypatch.setattr(es, "SentenceTransformer", DummyModel, raising=True)
        monkeypatch.setattr(es, "CHROMADB_AVAILABLE", False, raising=True)
        monkeypatch.setattr(es, "chromadb", None, raising=True)
        monkeypatch.setattr(es, "Settings", None, raising=True)

        svc = EmbeddingsService(provider="sentence-transformers")
        await svc.initialize()

        vec = await svc.embed_code("def f():\n    return 1\n")
        assert isinstance(vec, list) and len(vec) == 3

        batch = await svc.embed_code_batch(["a", "b", "c"])
        assert len(batch) == 3 and all(len(v) == 3 for v in batch)


@pytest.mark.asyncio
class TestMemoryServiceLifecycle:
    async def test_create_store_retrieve_persist(self, tmp_path: Path):
        # Arrange
        db_path = tmp_path / "memory.db"
        cfg = MemoryConfig(
            backend=StorageBackend.SQLITE,
            sqlite_path=str(db_path),
            max_messages_per_session=100,
            session_ttl_days=1,
        )
        mem = MemoryService(cfg)
        await mem.initialize()

        session_id = "sess-1"
        await mem.create_session(session_id=session_id, workspace_path=str(tmp_path))

        # Act: store a couple of messages
        msg1 = Message(
            id="m1",
            session_id=session_id,
            type=MessageType.USER_QUERY,
            content="hello",
            metadata={},
            timestamp=time.time() - 2,
        )
        msg2 = Message(
            id="m2",
            session_id=session_id,
            type=MessageType.AGENT_RESPONSE,
            content="hi",
            metadata={},
            timestamp=time.time() - 1,
        )
        await mem.store_message(session_id, msg1)
        await mem.store_message(session_id, msg2)

        # Assert: history returns messages in chronological order
        hist = await mem.get_session_history(session_id, limit=10)
        assert [m.id for m in hist] == ["m1", "m2"]

        # Persist session and verify
        ok = await mem.persist_session(session_id)
        assert ok is True

        stats = await mem.get_session_statistics(session_id)
        assert stats["total_messages"] == 2

        await mem.close()
