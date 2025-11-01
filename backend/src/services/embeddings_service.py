"""
Code embeddings service using Sentence Transformers
Project Creator: Herman Swanepoel
"""

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

# Optional dependency: chromadb. Import lazily/defensively so the backend can
# start in a minimal environment where vector DB is not installed.
try:  # pragma: no cover - environment dependent
    import importlib

    chromadb = importlib.import_module("chromadb")  # type: ignore
    from chromadb.config import Settings  # type: ignore

    CHROMADB_AVAILABLE = True
except Exception:  # pragma: no cover - handled gracefully at runtime
    chromadb = None  # type: ignore
    Settings = None  # type: ignore
    CHROMADB_AVAILABLE = False

# Avoid heavy import at module load; will be imported lazily in initialize()
SentenceTransformer = None  # type: ignore

logger = logging.getLogger(__name__)

# Directories we should never index for embeddings
EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".idea",
    ".vscode",
    "dist",
    "build",
    ".pytest_cache",
}


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
    ) -> None:
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
        self.provider = self._resolve_provider(provider)
        self.ollama_url = ollama_url
        self.ollama_model_name = ollama_model_name

    async def _call_ollama_embeddings(
        self,
        text: str,
        *,
        timeout: float = 45.0,
        max_attempts: int = 3,
    ) -> List[float]:
        """Invoke Ollama's embeddings endpoint with retries and backoff."""

        import httpx

        last_error: Optional[Exception] = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(1, max_attempts + 1):
                try:
                    # Ollama's native /api/embeddings expects a single string in
                    # the "prompt" field. Some versions/libraries also support
                    # "input" (array) and return "embeddings". To maximize
                    # compatibility, send only "prompt" and accept both response
                    # shapes ("embedding" or "embeddings").
                    response = await client.post(
                        f"{self.ollama_url}/api/embeddings",
                        json={
                            "model": self.ollama_model_name,
                            "prompt": text,
                        },
                    )
                    status_code = getattr(response, "status_code", None)
                    if isinstance(status_code, (int, float)) and status_code >= 400:
                        body = await response.aread()
                        raise RuntimeError(
                            "Ollama embeddings error " f"{int(status_code)}: {body[:500]!r}"
                        )
                    data = response.json()
                    embedding = data.get("embedding")

                    # Some Ollama builds (or OpenAI-compatible routes) return
                    # an array-of-arrays under "embeddings" when "input" is
                    # used. Support that shape by taking the first vector.
                    if embedding is None and isinstance(data.get("embeddings"), list):
                        emb_list = data.get("embeddings")
                        if emb_list and isinstance(emb_list[0], list):
                            embedding = emb_list[0]

                    if not isinstance(embedding, list) or not embedding:
                        raise RuntimeError("Ollama returned empty embedding array")
                    return [float(x) for x in embedding]
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    last_error = exc
                    if attempt == max_attempts:
                        break
                    logger.warning(
                        "ollama_embed_retry",
                        extra={
                            "attempt": attempt,
                            "max_attempts": max_attempts,
                            "reason": str(exc),
                        },
                    )
                    await asyncio.sleep(min(4.0, 1.5 * attempt))

        assert last_error is not None
        raise RuntimeError(
            "Ollama embeddings failed after " f"{max_attempts} attempts: {last_error}"
        ) from last_error

    @staticmethod
    def _resolve_provider(raw_provider: Any) -> str:
        """Coerce DI-provided provider configs into a simple string."""

        provider_value = raw_provider
        try:  # dependency_injector is optional during tests
            from dependency_injector import providers as di_providers  # type: ignore

            if isinstance(provider_value, di_providers.Provider):
                provider_value = provider_value()
        except Exception:  # pragma: no cover - defensive guard
            pass

        if hasattr(provider_value, "provider"):
            provider_value = provider_value.provider

        if not isinstance(provider_value, str):
            provider_value = str(provider_value)

        return provider_value

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
                # Cast lazily assigned SentenceTransformer (type checker appeasement)
                ST = cast(Any, SentenceTransformer)

                def _load_model() -> Any:
                    try:
                        return ST(self.model_name)
                    except TypeError as exc:
                        logger.debug(
                            "sentence_transformer_fallback",
                            extra={"error": str(exc)},
                        )
                        return ST()

                self.model = await loop.run_in_executor(None, _load_model)
            else:
                # Ollama provider: no local model to load
                self.model = None

            # Initialize ChromaDB if available; otherwise run in ephemeral/no-op mode
            if CHROMADB_AVAILABLE and chromadb is not None and Settings is not None:
                self.chroma_client = chromadb.Client(  # type: ignore[call-arg]
                    Settings(  # type: ignore[call-arg]
                        persist_directory=self.chroma_persist_dir,
                        anonymized_telemetry=False,
                    )
                )

                # Get or create collection
                assert self.chroma_client is not None
                self.collection = self.chroma_client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"description": "Code embeddings for semantic search"},
                )
            else:
                # Operate without persistent vector DB
                self.chroma_client = None
                self.collection = None
                logger.warning(
                    "chroma_unavailable",
                    extra={
                        "detail": ("ChromaDB not installed; embeddings persistence disabled"),
                        "persist_dir": self.chroma_persist_dir,
                    },
                )

            self.is_initialized = True
            logger.info("✓ Embeddings service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize embeddings service: {e}")
            raise

    async def embed_code(
        self,
        code: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[float]:
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
            # Clip very large inputs to keep requests fast and within model limits
            if len(code) > 8000:
                code = code[:8000]

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
                if hasattr(embedding, "tolist"):
                    return embedding.tolist()
                return list(embedding)
            else:
                # Use Ollama embeddings API
                return await self._call_ollama_embeddings(code)

        except Exception as e:
            # Log full exception info for better diagnostics
            logger.exception("Failed to generate embedding: %r", e)
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
                if hasattr(embeddings, "tolist"):
                    embeddings_list = embeddings.tolist()
                else:
                    embeddings_list = list(embeddings)
                return [
                    emb.tolist() if hasattr(emb, "tolist") else list(emb) for emb in embeddings_list
                ]
            else:
                # Ollama embeddings API doesn't support batch in one call
                # Do sequential calls (kept simple; could parallelize if needed)
                results: List[List[float]] = []
                for code in code_snippets:
                    vec = await self.embed_code(code)
                    results.append(vec)
                return results

        except Exception as e:
            logger.exception("Failed to generate batch embeddings: %r", e)
            raise

    async def embed_codebase(
        self,
        workspace_path: str,
        file_extensions: Optional[List[str]] = None,
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
                for p in workspace.rglob(f"*{ext}"):
                    # Skip excluded directories anywhere in the path
                    if any(part in EXCLUDED_DIRS for part in p.parts):
                        continue
                    code_files.append(p)

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
            logger.exception("Failed to embed codebase: %r", e)
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
                    # Skip very large files (>500KB) to avoid timeouts and memory churn
                    try:
                        if file_path.stat().st_size > 500_000:
                            logger.debug("skip_large_file", extra={"path": str(file_path)})
                            continue
                    except Exception:
                        # If stat fails, fall back to read and let errors surface below
                        pass

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

            # Store all in ChromaDB if available; otherwise no-op
            if self.collection is not None:
                self.collection.upsert(
                    ids=file_ids,
                    embeddings=embeddings,
                    documents=contents,
                    metadatas=metadatas,
                )

        except Exception as e:
            logger.exception("Failed to process file batch: %r", e)
            # Fallback to individual processing
            for file_path in files:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    file_id = self._generate_file_id(str(file_path))
                    embedding = await self.embed_code(content)

                    if self.collection is not None:
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
                    logger.warning("Failed to process %s: %r", file_path, e2)

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

            # Search in ChromaDB if available; otherwise return empty
            if self.collection is None:
                return []

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
            if self.collection is not None:
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
            if self.collection is not None:
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
        if not self.is_initialized:
            return {"initialized": False}

        try:
            count = self.collection.count() if self.collection is not None else 0
            return {
                "initialized": True,
                "model": self.model_name,
                "collection": self.collection_name,
                "total_embeddings": count,
                "persist_directory": self.chroma_persist_dir,
                "chroma_available": CHROMADB_AVAILABLE,
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"initialized": True, "error": str(e)}
