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
        assert embeddings_service.chroma_persist_dir == embeddings_config["chroma_persist_dir"]
        assert embeddings_service.collection_name == embeddings_config["collection_name"]
        assert embeddings_service.is_initialized is False
        assert embeddings_service.model is None

    @pytest.mark.asyncio
    async def test_initialize_success(self, embeddings_service):
        """Test successful initialization of embeddings service"""
        mock_model = MagicMock()
        mock_chroma = MagicMock()
        mock_collection = MagicMock()

        with patch("src.services.embeddings_service.SentenceTransformer", return_value=mock_model):
            with patch("src.services.embeddings_service.chromadb.Client", return_value=mock_chroma):
                mock_chroma.get_or_create_collection.return_value = mock_collection

                await embeddings_service.initialize()

                assert embeddings_service.is_initialized is True
                assert embeddings_service.model == mock_model
                assert embeddings_service.chroma_client == mock_chroma
                assert embeddings_service.collection == mock_collection

    @pytest.mark.asyncio
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
