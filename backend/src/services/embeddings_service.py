"""
Code embeddings service using Sentence Transformers
Project Creator: Herman Swanepoel
"""

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

# Avoid heavy import at module load; will be imported lazily in initialize()
SentenceTransformer = None  # type: ignore

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """
    Service for generating and managing code embeddings
    Uses CodeBERT for semantic code understanding
    """

    def __init__(
        self,
        model_name: str = "microsoft/codebert-base",
        chroma_persist_dir: str = "./data/chroma",
        collection_name: str = "code_embeddings",
        provider: str = "sentence-transformers",
        ollama_url: str = "http://localhost:11434",
        ollama_model_name: str = "nomic-embed-text",
    ):
        """
        Initialize embeddings service

        Args:
            model_name: Sentence transformer model to use
            chroma_persist_dir: Directory for ChromaDB persistence
            chroma_persist_dir: Directory for ChromaDB persistence
            collection_name: Name of the ChromaDB collection
        """
        self.model_name = model_name
        self.chroma_persist_dir = chroma_persist_dir
        self.collection_name = collection_name
        self.model: Optional[Any] = None
        # Use broad Any types for optional third-party clients in type checking
        self.chroma_client: Optional[Any] = None
        self.collection: Optional[Any] = None
        self.is_initialized = False
        self.provider = provider
        self.ollama_url = ollama_url
        self.ollama_model_name = ollama_model_name

    async def initialize(self) -> None:
        """Initialize the embeddings model and vector store"""
        try:
            logger.info(f"Loading embeddings model: {self.model_name}")

            if self.provider == "sentence-transformers":
                # Import lazily to avoid heavy import at app startup
                global SentenceTransformer  # type: ignore
                if SentenceTransformer is None:  # type: ignore
                    from sentence_transformers import SentenceTransformer as _ST

                    SentenceTransformer = _ST  # type: ignore

                # Load model in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                self.model = await loop.run_in_executor(
                    None, lambda: SentenceTransformer(self.model_name)
                )
            else:
                # Ollama provider: no local model to load
                self.model = None

            # Initialize ChromaDB
            self.chroma_client = chromadb.Client(
                Settings(
                    persist_directory=self.chroma_persist_dir,
                    anonymized_telemetry=False,
                )
            )

            # Get or create collection
            # mypy: chroma_client is initialized above; keep assert for clarity
            assert self.chroma_client is not None
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Code embeddings for semantic search"},
            )

            self.is_initialized = True
            logger.info("✓ Embeddings service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize embeddings service: {e}")
            raise

    async def embed_code(self, code: str, metadata: Optional[Dict[str, Any]] = None) -> List[float]:
        """
        Generate embedding for code snippet

        Args:
            code: Code to embed
            metadata: Optional metadata

        Returns:
            Embedding vector
        """
        if not self.is_initialized:
            raise RuntimeError("Embeddings service not initialized")

        try:
            if self.provider == "sentence-transformers":
                if not self.model:
                    raise RuntimeError("Embeddings model not loaded")
                # Generate embedding in thread pool
                loop = asyncio.get_event_loop()
                # Guard for type checker and capture to local var for executor
                assert self.model is not None
                model = self.model
                embedding = await loop.run_in_executor(
                    None, lambda: model.encode(code, convert_to_numpy=True)
                )
                return embedding.tolist()
            else:
                # Use Ollama embeddings API
                import httpx

                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(
                        f"{self.ollama_url}/api/embeddings",
                        json={"model": self.ollama_model_name, "prompt": code},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    # Ollama returns { embedding: [...] }
                    return data.get("embedding", [])

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def embed_code_batch(self, code_snippets: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple code snippets in batch (3x faster)

        Args:
            code_snippets: List of code to embed

        Returns:
            List of embedding vectors
        """
        if not self.is_initialized:
            raise RuntimeError("Embeddings service not initialized")

        try:
            if self.provider == "sentence-transformers":
                if not self.model:
                    raise RuntimeError("Embeddings model not loaded")
                # Batch encoding is significantly faster than individual encoding
                loop = asyncio.get_event_loop()
                # Guard for type checker and capture to local var
                assert self.model is not None
                model = self.model
                embeddings = await loop.run_in_executor(
                    None,
                    lambda: model.encode(code_snippets, convert_to_numpy=True, batch_size=32),
                )
                return [emb.tolist() for emb in embeddings]
            else:
                # Ollama embeddings API doesn't support batch in one call
                # Do sequential calls (kept simple; could parallelize if needed)
                results: List[List[float]] = []
                for code in code_snippets:
                    vec = await self.embed_code(code)
                    results.append(vec)
                return results

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise

    async def embed_codebase(
        self,
        workspace_path: str,
        file_extensions: List[str] = None,
    ) -> int:
        """
        Generate embeddings for entire codebase

        Args:
            workspace_path: Path to workspace
            file_extensions: File extensions to process

        Returns:
            Number of files processed
        """
        if file_extensions is None:
            file_extensions = [".py", ".ts", ".js", ".tsx", ".jsx"]
        if not self.is_initialized:
            raise RuntimeError("Embeddings service not initialized")

        workspace = Path(workspace_path)
        if not workspace.exists():
            raise ValueError(f"Workspace path does not exist: {workspace_path}")

        files_processed = 0

        try:
            # Find all code files
            code_files: List[Path] = []
            for ext in file_extensions:
                code_files.extend(workspace.rglob(f"*{ext}"))

            logger.info(f"Found {len(code_files)} code files to process")

            # Process files in batches
            batch_size = 10
            for i in range(0, len(code_files), batch_size):
                batch = code_files[i : i + batch_size]
                await self._process_file_batch(batch)
                files_processed += len(batch)

                if files_processed % 50 == 0:
                    logger.info(f"Processed {files_processed}/{len(code_files)} files")

            logger.info(f"✓ Codebase embedding complete: {files_processed} files")
            return files_processed

        except Exception as e:
            logger.error(f"Failed to embed codebase: {e}")
            raise

    async def _process_file_batch(self, files: List[Path]) -> None:
        """Process a batch of files using batch embedding (3x faster)"""
        try:
            # Read all file contents
            contents = []
            file_ids = []
            metadatas = []
            valid_files = []

            for file_path in files:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    contents.append(content)
                    file_ids.append(self._generate_file_id(str(file_path)))
                    metadatas.append(
                        {
                            "file_path": str(file_path),
                            "file_name": file_path.name,
                            "extension": file_path.suffix,
                            "size": len(content),
                        }
                    )
                    valid_files.append(file_path)
                except Exception as e:
                    logger.warning(f"Failed to read {file_path}: {e}")

            if not contents:
                return

            # Generate embeddings in batch (much faster)
            embeddings = await self.embed_code_batch(contents)

            # Store all in ChromaDB
            # Guard collection for type checker
            assert self.collection is not None
            self.collection.upsert(
                ids=file_ids,
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas,
            )

        except Exception as e:
            logger.error(f"Failed to process file batch: {e}")
            # Fallback to individual processing
            for file_path in files:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    file_id = self._generate_file_id(str(file_path))
                    embedding = await self.embed_code(content)

                    assert self.collection is not None
                    self.collection.upsert(
                        ids=[file_id],
                        embeddings=[embedding],
                        documents=[content],
                        metadatas=[
                            {
                                "file_path": str(file_path),
                                "file_name": file_path.name,
                                "extension": file_path.suffix,
                                "size": len(content),
                            }
                        ],
                    )
                except Exception as e2:
                    logger.warning(f"Failed to process {file_path}: {e2}")

    async def find_similar_code(
        self, query: str, top_k: int = 5, file_extension: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar code using semantic search

        Args:
            query: Search query
            top_k: Number of results to return
            file_extension: Filter by file extension

        Returns:
            List of similar code snippets with metadata
        """
        if not self.is_initialized:
            raise RuntimeError("Embeddings service not initialized")

        try:
            # Generate query embedding
            query_embedding = await self.embed_code(query)

            # Build where clause for filtering
            where = None
            if file_extension:
                where = {"extension": file_extension}

            # Search in ChromaDB
            assert self.collection is not None
            results = self.collection.query(
                query_embeddings=[query_embedding], n_results=top_k, where=where
            )

            # Format results
            similar_code = []
            if results and results["documents"]:
                for i in range(len(results["documents"][0])):
                    similar_code.append(
                        {
                            "code": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i],
                            "distance": (
                                results["distances"][0][i] if "distances" in results else None
                            ),
                        }
                    )

            return similar_code

        except Exception as e:
            logger.error(f"Failed to search similar code: {e}")
            raise

    async def update_file_embedding(self, file_path: str, content: str) -> None:
        """
        Update embedding for a single file (incremental update)

        Args:
            file_path: Path to file
            content: File content
        """
        if not self.is_initialized:
            raise RuntimeError("Embeddings service not initialized")

        try:
            file_id = self._generate_file_id(file_path)
            embedding = await self.embed_code(content)

            path_obj = Path(file_path)
            assert self.collection is not None
            self.collection.upsert(
                ids=[file_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[
                    {
                        "file_path": file_path,
                        "file_name": path_obj.name,
                        "extension": path_obj.suffix,
                        "size": len(content),
                    }
                ],
            )

            logger.debug(f"Updated embedding for {file_path}")

        except Exception as e:
            logger.error(f"Failed to update file embedding: {e}")
            raise

    async def delete_file_embedding(self, file_path: str) -> None:
        """
        Delete embedding for a file

        Args:
            file_path: Path to file
        """
        if not self.is_initialized:
            raise RuntimeError("Embeddings service not initialized")

        try:
            file_id = self._generate_file_id(file_path)
            assert self.collection is not None
            self.collection.delete(ids=[file_id])
            logger.debug(f"Deleted embedding for {file_path}")

        except Exception as e:
            logger.error(f"Failed to delete file embedding: {e}")
            raise

    def _generate_file_id(self, file_path: str) -> str:
        """Generate unique ID for file"""
        return hashlib.md5(file_path.encode(), usedforsecurity=False).hexdigest()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about embeddings

        Returns:
            Statistics dictionary
        """
        if not self.is_initialized or not self.collection:
            return {"initialized": False}

        try:
            assert self.collection is not None
            count = self.collection.count()
            return {
                "initialized": True,
                "model": self.model_name,
                "collection": self.collection_name,
                "total_embeddings": count,
                "persist_directory": self.chroma_persist_dir,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"initialized": True, "error": str(e)}
