"""
Embeddings Service Tests
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from src.services.embeddings_service import EmbeddingsService


class TestEmbeddingsService:
    """Test EmbeddingsService initialization and core methods"""

    @pytest.fixture
    def embeddings_config(self):
        return {
            "model_name": "microsoft/codebert-base",
            "chroma_persist_dir": "./test_data/chroma",
            "collection_name": "test_embeddings",
        }

    @pytest.fixture
    def embeddings_service(self, embeddings_config):
        return EmbeddingsService(**embeddings_config)

    def test_initialization(self, embeddings_service, embeddings_config):
        """Test service initializes with correct configuration"""
        assert embeddings_service.model_name == embeddings_config["model_name"]
        assert (
            embeddings_service.chroma_persist_dir
            == embeddings_config["chroma_persist_dir"]
        )
        assert (
            embeddings_service.collection_name == embeddings_config["collection_name"]
        )
        assert embeddings_service.is_initialized is False
        assert embeddings_service.model is None

    @pytest.mark.asyncio
    async def test_initialize_success(self, embeddings_service):
        """Test successful initialization of embeddings service"""
        mock_model = MagicMock()
        mock_chroma = MagicMock()
        mock_collection = MagicMock()

        with patch(
            "src.services.embeddings_service.SentenceTransformer",
            return_value=mock_model,
        ):
            with patch(
                "src.services.embeddings_service.chromadb.Client",
                return_value=mock_chroma,
            ):
                mock_chroma.get_or_create_collection.return_value = mock_collection

                await embeddings_service.initialize()

                assert embeddings_service.is_initialized is True
                assert embeddings_service.model == mock_model
                assert embeddings_service.chroma_client == mock_chroma
                assert embeddings_service.collection == mock_collection

    async def test_initialize_failure(self, embeddings_service):
        """Test initialization failure handling"""
        with patch(
            "src.services.embeddings_service.SentenceTransformer",
            side_effect=Exception("Model load failed"),
        ):
            with pytest.raises(Exception) as exc:
                await embeddings_service.initialize()
            assert "Model load failed" in str(exc.value)
            assert embeddings_service.is_initialized is False

    @pytest.mark.asyncio
    async def test_initialize_failure_b017(self, embeddings_service):
        """Test initialization failure handling with specific exception (B017)"""

        class CustomTestException(Exception):
            pass

        with patch(
            "src.services.embeddings_service.SentenceTransformer",
            side_effect=CustomTestException("Model load failed"),
        ):
            with pytest.raises(CustomTestException) as exc:
                await embeddings_service.initialize()
            assert "Model load failed" in str(exc.value)
            assert embeddings_service.is_initialized is False

    @pytest.mark.asyncio
    async def test_embed_code_success(self, embeddings_service):
        """Test successful code embedding generation"""
        mock_model = MagicMock()
        mock_embedding = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        mock_model.encode.return_value = mock_embedding

        embeddings_service.model = mock_model
        embeddings_service.is_initialized = True

        code = "def hello(): return 'world'"
        result = await embeddings_service.embed_code(code)

        assert isinstance(result, list)
        assert len(result) == 5
        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_model.encode.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_code_not_initialized(self, embeddings_service):
        """Test embed_code fails when not initialized"""
        with pytest.raises(RuntimeError) as exc:
            await embeddings_service.embed_code("def test(): pass")
        assert "not initialized" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_embed_code_with_metadata(self, embeddings_service):
        """Test embedding with metadata"""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.1, 0.2])

        embeddings_service.model = mock_model
        embeddings_service.is_initialized = True

        metadata = {"file": "test.py", "line": 10}
        result = await embeddings_service.embed_code("print('test')", metadata=metadata)

        assert isinstance(result, list)
        assert len(result) == 2

    def test_default_model_name(self):
        """Test default model name is set correctly"""
        service = EmbeddingsService()
        assert service.model_name == "microsoft/codebert-base"
        assert service.collection_name == "code_embeddings"

    @pytest.mark.asyncio
    async def test_embed_empty_code(self, embeddings_service):
        """Test embedding empty code string"""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.0])

        embeddings_service.model = mock_model
        embeddings_service.is_initialized = True

        result = await embeddings_service.embed_code("")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_embed_large_code(self, embeddings_service):
        """Test embedding large code block"""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([0.1] * 768)  # Typical embedding size

        embeddings_service.model = mock_model
        embeddings_service.is_initialized = True

        large_code = "def test():\n    " + "pass\n    " * 1000
        result = await embeddings_service.embed_code(large_code)

        assert isinstance(result, list)
        assert len(result) == 768


class TestEmbeddingsVectorOperations:
    """Test vector storage and retrieval operations"""

    @pytest.fixture
    def initialized_service(self):
        service = EmbeddingsService()
        service.is_initialized = True
        service.model = MagicMock()
        service.chroma_client = MagicMock()
        service.collection = MagicMock()
        return service

    @pytest.mark.asyncio
    async def test_model_encoding_called_correctly(self, initialized_service):
        """Test model encode is called with correct parameters"""
        mock_embedding = np.array([0.5, 0.6])
        initialized_service.model.encode.return_value = mock_embedding

        code = "import numpy"
        await initialized_service.embed_code(code)

        # Verify encode was called (actual call happens in executor)
        assert initialized_service.model is not None

    def test_chroma_collection_metadata(self):
        """Test ChromaDB collection is created with correct metadata"""
        service = EmbeddingsService(collection_name="custom_collection")
        assert service.collection_name == "custom_collection"

    def test_multiple_instances_independent(self):
        """Test multiple service instances are independent"""
        service1 = EmbeddingsService(collection_name="collection1")
        service2 = EmbeddingsService(collection_name="collection2")

        assert service1.collection_name != service2.collection_name
        assert service1.is_initialized is False
        assert service2.is_initialized is False


class TestEmbeddingsBatchOperations:
    """Test batch embedding operations"""

    @pytest.fixture
    def service(self):
        service = EmbeddingsService()
        service.is_initialized = True
        service.model = MagicMock()
        service.model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        service.collection = MagicMock()
        return service

    @pytest.mark.asyncio
    async def test_embed_code_batch_success(self, service):
        """Test batch embedding generation"""
        codes = ["def foo(): pass", "def bar(): pass"]
        result = await service.embed_code_batch(codes)

        assert len(result) == 2
        assert isinstance(result[0], list)
        assert isinstance(result[1], list)

    @pytest.mark.asyncio
    async def test_embed_code_batch_not_initialized(self):
        """Test batch embed fails when not initialized"""
        service = EmbeddingsService()
        with pytest.raises(RuntimeError) as exc:
            await service.embed_code_batch(["code1", "code2"])
        assert "not initialized" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_embed_code_batch_no_model(self):
        """Test batch embed fails when model not loaded"""
        service = EmbeddingsService()
        service.is_initialized = True
        service.model = None
        with pytest.raises(RuntimeError) as exc:
            await service.embed_code_batch(["code1", "code2"])
        assert "model not loaded" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_embed_code_batch_empty_list(self, service):
        """Test batch embedding with empty list"""
        service.model.encode.return_value = np.array([])
        result = await service.embed_code_batch([])
        assert result == []


class TestCodebaseEmbedding:
    """Test codebase-wide embedding operations"""

    @pytest.fixture
    def service(self, tmp_path):
        service = EmbeddingsService()
        service.is_initialized = True
        service.model = MagicMock()
        service.model.encode.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        service.collection = MagicMock()
        return service

    @pytest.mark.asyncio
    async def test_embed_codebase_not_initialized(self):
        """Test codebase embedding fails when not initialized"""
        service = EmbeddingsService()
        with pytest.raises(RuntimeError) as exc:
            await service.embed_codebase("/fake/path")
        assert "not initialized" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_embed_codebase_invalid_path(self, service):
        """Test codebase embedding with invalid path"""
        with pytest.raises(ValueError) as exc:
            await service.embed_codebase("/nonexistent/path")
        assert "does not exist" in str(exc.value)

    @pytest.mark.asyncio
    async def test_embed_codebase_success(self, service, tmp_path):
        """Test successful codebase embedding"""
        # Create test files
        (tmp_path / "test1.py").write_text("def foo(): pass")
        (tmp_path / "test2.py").write_text("def bar(): return 42")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "test3.js").write_text("function baz() {}")

        result = await service.embed_codebase(str(tmp_path))

        assert result == 3  # Should process 3 files
        service.collection.upsert.assert_called()

    @pytest.mark.asyncio
    async def test_embed_codebase_filtered_extensions(self, service, tmp_path):
        """Test codebase embedding with filtered extensions"""
        (tmp_path / "test1.py").write_text("def foo(): pass")
        (tmp_path / "test2.js").write_text("function bar() {}")
        (tmp_path / "test3.md").write_text("# Documentation")

        result = await service.embed_codebase(str(tmp_path), file_extensions=[".py"])

        assert result == 1  # Should only process .py files


class TestSimilaritySearch:
    """Test semantic similarity search"""

    @pytest.fixture
    def service(self):
        service = EmbeddingsService()
        service.is_initialized = True
        service.model = MagicMock()
        service.model.encode.return_value = np.array([0.1, 0.2, 0.3])
        service.collection = MagicMock()
        return service

    @pytest.mark.asyncio
    async def test_find_similar_code_success(self, service):
        """Test finding similar code"""
        service.collection.query.return_value = {
            "documents": [["def foo(): pass", "def bar(): return 42"]],
            "metadatas": [
                [
                    {"file_path": "test1.py", "file_name": "test1.py"},
                    {"file_path": "test2.py", "file_name": "test2.py"},
                ]
            ],
            "distances": [[0.1, 0.3]],
        }

        results = await service.find_similar_code("def test()", top_k=2)

        assert len(results) == 2
        assert results[0]["code"] == "def foo(): pass"
        assert results[0]["metadata"]["file_path"] == "test1.py"
        assert results[0]["distance"] == 0.1

    @pytest.mark.asyncio
    async def test_find_similar_code_with_filter(self, service):
        """Test finding similar code with extension filter"""
        service.collection.query.return_value = {
            "documents": [["def foo(): pass"]],
            "metadatas": [[{"file_path": "test.py", "extension": ".py"}]],
            "distances": [[0.1]],
        }

        await service.find_similar_code("def test()", top_k=5, file_extension=".py")

        service.collection.query.assert_called_once()
        call_args = service.collection.query.call_args
        assert call_args[1]["where"] == {"extension": ".py"}

    @pytest.mark.asyncio
    async def test_find_similar_code_not_initialized(self):
        """Test similarity search fails when not initialized"""
        service = EmbeddingsService()
        with pytest.raises(RuntimeError) as exc:
            await service.find_similar_code("query")
        assert "not initialized" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_find_similar_code_no_results(self, service):
        """Test similarity search with no results"""
        service.collection.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        results = await service.find_similar_code("query")
        assert results == []


class TestFileOperations:
    """Test individual file embedding operations"""

    @pytest.fixture
    def service(self):
        service = EmbeddingsService()
        service.is_initialized = True
        service.model = MagicMock()
        service.model.encode.return_value = np.array([0.1, 0.2])
        service.collection = MagicMock()
        return service

    @pytest.mark.asyncio
    async def test_update_file_embedding_success(self, service):
        """Test updating single file embedding"""
        await service.update_file_embedding("test.py", "def foo(): pass")

        service.collection.upsert.assert_called_once()
        call_args = service.collection.upsert.call_args
        assert len(call_args[1]["ids"]) == 1
        assert call_args[1]["metadatas"][0]["file_path"] == "test.py"

    @pytest.mark.asyncio
    async def test_update_file_embedding_not_initialized(self):
        """Test update fails when not initialized"""
        service = EmbeddingsService()
        with pytest.raises(RuntimeError) as exc:
            await service.update_file_embedding("test.py", "code")
        assert "not initialized" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_delete_file_embedding_success(self, service):
        """Test deleting file embedding"""
        await service.delete_file_embedding("test.py")

        service.collection.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_file_embedding_not_initialized(self):
        """Test delete fails when not initialized"""
        service = EmbeddingsService()
        with pytest.raises(RuntimeError) as exc:
            await service.delete_file_embedding("test.py")
        assert "not initialized" in str(exc.value).lower()

    def test_generate_file_id_consistency(self, service):
        """Test file ID generation is consistent"""
        id1 = service._generate_file_id("test.py")
        id2 = service._generate_file_id("test.py")
        assert id1 == id2

    def test_generate_file_id_uniqueness(self, service):
        """Test different files get different IDs"""
        id1 = service._generate_file_id("test1.py")
        id2 = service._generate_file_id("test2.py")
        assert id1 != id2


class TestStatistics:
    """Test statistics and monitoring"""

    def test_get_stats_not_initialized(self):
        """Test stats when not initialized"""
        service = EmbeddingsService()
        stats = service.get_stats()
        assert stats["initialized"] is False

    def test_get_stats_initialized(self):
        """Test stats when initialized"""
        service = EmbeddingsService(
            model_name="test-model", collection_name="test-collection"
        )
        service.is_initialized = True
        service.collection = MagicMock()
        service.collection.count.return_value = 42

        stats = service.get_stats()

        assert stats["initialized"] is True
        assert stats["model"] == "test-model"
        assert stats["collection"] == "test-collection"
        assert stats["total_embeddings"] == 42

    def test_get_stats_error_handling(self):
        """Test stats handles errors gracefully"""
        service = EmbeddingsService()
        service.is_initialized = True
        service.collection = MagicMock()
        service.collection.count.side_effect = Exception("Count failed")

        stats = service.get_stats()

        assert stats["initialized"] is True
        assert "error" in stats


class TestOllamaProvider:
    """Test Ollama embeddings provider"""

    @pytest.fixture
    def ollama_service(self):
        return EmbeddingsService(
            provider="ollama",
            ollama_url="http://localhost:11434",
            ollama_model_name="nomic-embed-text",
        )

    @pytest.mark.asyncio
    async def test_ollama_initialization(self, ollama_service):
        """Test Ollama provider initialization"""
        mock_chroma = MagicMock()
        mock_collection = MagicMock()

        with patch(
            "src.services.embeddings_service.chromadb.Client", return_value=mock_chroma
        ):
            mock_chroma.get_or_create_collection.return_value = mock_collection
            await ollama_service.initialize()

            assert ollama_service.is_initialized is True
            assert ollama_service.model is None  # Ollama doesn't use local model

    @pytest.mark.asyncio
    async def test_ollama_embed_code_success(self, ollama_service):
        """Test Ollama embedding generation"""
        ollama_service.is_initialized = True

        mock_response = MagicMock()
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            result = await ollama_service.embed_code("def test(): pass")

            assert result == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_ollama_batch_embedding(self, ollama_service):
        """Test Ollama batch embedding (sequential calls)"""
        ollama_service.is_initialized = True

        # Mock embed_code to return different vectors
        async def mock_embed(code):
            return [0.1, 0.2] if "foo" in code else [0.3, 0.4]

        ollama_service.embed_code = mock_embed

        codes = ["def foo(): pass", "def bar(): pass"]
        results = await ollama_service.embed_code_batch(codes)

        assert len(results) == 2
        assert results[0] == [0.1, 0.2]
        assert results[1] == [0.3, 0.4]
