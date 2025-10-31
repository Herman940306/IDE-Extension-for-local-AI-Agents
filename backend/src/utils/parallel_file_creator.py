"""
Parallel File Creation Module – GODMODE Reporting Integrated
Project Creator: Herman Swanepoel

High-performance parallel file creation with:
- Async I/O operations
- FAISS vector indexing
- Redis metadata storage
- GODMODE batch reporting
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

import numpy as np

# Optional dependencies (graceful degradation)
try:
    from sentence_transformers import SentenceTransformer

    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logging.warning("sentence-transformers not available, embeddings disabled")

try:
    import faiss

    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning("faiss not available, vector indexing disabled")

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("redis not available, metadata storage disabled")

logger = logging.getLogger(__name__)


class ParallelFileCreator:
    """
    High-performance parallel file creator with vector indexing.

    Features:
    - Async file I/O with semaphore-based concurrency control
    - Automatic embedding generation and FAISS indexing
    - Redis metadata storage
    - GODMODE batch reporting
    """

    def __init__(
        self,
        base_dir: Path,
        max_workers: int = 8,
        embedding_model: str = "all-MiniLM-L6-v2",
        vector_dim: int = 384,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
    ):
        """
        Initialize parallel file creator.

        Args:
            base_dir: Base directory for file creation
            max_workers: Maximum concurrent workers
            embedding_model: Sentence transformer model name
            vector_dim: Vector dimension for FAISS
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database number
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.max_workers = max_workers
        self.vector_dim = vector_dim

        # Initialize embedding model (opt-in only to avoid slow downloads in tests)
        self.embedding_model = None
        enable_embeddings = os.getenv("PFC_ENABLE_EMBEDDINGS", "false").lower() in (
            "1",
            "true",
            "yes",
        )
        if EMBEDDINGS_AVAILABLE and enable_embeddings:
            try:
                self.embedding_model = SentenceTransformer(embedding_model)
                logger.info("Loaded embedding model: %s", embedding_model)
            except Exception as e:  # pragma: no cover - defensive
                logger.warning("Embedding model load failed, disabling: %s", e)
                self.embedding_model = None
        self._embeddings_enabled = self.embedding_model is not None

        # Initialize FAISS index
        self.faiss_index_file = self.base_dir / "faiss.index"
        enable_faiss = os.getenv("PFC_ENABLE_FAISS", "false").lower() in (
            "1",
            "true",
            "yes",
        )
        self.file_id_map: Dict[int, str] = {}
        if FAISS_AVAILABLE and enable_faiss:
            try:
                if self.faiss_index_file.exists():
                    self.faiss_index = faiss.read_index(str(self.faiss_index_file))
                    logger.info("Loaded existing FAISS index: %s", self.faiss_index_file)
                else:
                    self.faiss_index = faiss.IndexFlatL2(vector_dim)
                    logger.info("Created new FAISS index")
            except Exception as e:  # pragma: no cover - defensive
                logger.warning("FAISS initialisation failed, disabling: %s", e)
                self.faiss_index = None
        else:
            if FAISS_AVAILABLE and not enable_faiss:
                logger.debug("FAISS disabled via PFC_ENABLE_FAISS")
            self.faiss_index = None
        self._faiss_enabled = self.faiss_index is not None

        # Initialize Redis
        # Predeclare with broad type to allow None assignment when disabled
        self.redis_client: Any = None
        enable_redis = os.getenv("PFC_ENABLE_REDIS", "false").lower() in (
            "1",
            "true",
            "yes",
        )
        if REDIS_AVAILABLE and enable_redis:
            try:
                # Use broad type to keep optional dependency flexible under mypy
                self.redis_client = redis.Redis(
                    host=redis_host, port=redis_port, db=redis_db, decode_responses=True
                )
                self.redis_client.ping()
                logger.info("Connected to Redis: %s:%s", redis_host, redis_port)
            except Exception as e:
                logger.warning("Redis connection failed, disabling metadata storage: %s", e)
                self.redis_client = None
        else:
            if REDIS_AVAILABLE and not enable_redis:
                logger.debug("Redis integration disabled via PFC_ENABLE_REDIS")
            self.redis_client = None
        self._redis_enabled = self.redis_client is not None

        # Statistics
        self.total_files_created = 0
        self.total_embeddings_generated = 0
        self.total_errors = 0

    async def create_file(
        self,
        file_name: str,
        content: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> Optional[Path]:
        """
        Create a single file with embedding and metadata storage.

        Args:
            file_name: Name of file to create
            content: File content
            loop: Event loop (optional)

        Returns:
            Path to created file or None on failure
        """
        if loop is None:
            loop = asyncio.get_event_loop()

        file_path = self.base_dir / file_name

        try:
            # Write file
            success_write = await loop.run_in_executor(None, self._write_file, file_path, content)

            if not success_write:
                return None

            # Generate embedding
            vector = None
            if self.embedding_model is not None:
                vector = await loop.run_in_executor(None, self._embed_file, file_path)

            # Store in FAISS
            if vector is not None and self.faiss_index is not None:
                await loop.run_in_executor(None, self._store_in_faiss, file_name, vector)

            # Store metadata in Redis
            if self.redis_client is not None:
                await loop.run_in_executor(None, self._store_in_redis, file_path)

            self.total_files_created += 1
            return file_path

        except Exception as e:
            logger.error(f"Error creating file {file_name}: {e}")
            self.total_errors += 1
            return None

    async def create_files_parallel(self, file_tasks: List[Dict[str, str]]) -> List[Optional[Path]]:
        """
        Create multiple files in parallel.

        Args:
            file_tasks: List of dicts with 'name' and 'content' keys

        Returns:
            List of created file paths (None for failures)
        """
        start_time = time.time()
        loop = asyncio.get_event_loop()
        semaphore = asyncio.Semaphore(self.max_workers)

        async def sem_task(task):
            async with semaphore:
                return await self.create_file(task["name"], task["content"], loop=loop)

        # Execute all tasks
        tasks = [sem_task(task) for task in file_tasks]
        raw_results: List[Union[Optional[Path], BaseException]] = cast(
            List[Union[Optional[Path], BaseException]],
            await asyncio.gather(*tasks, return_exceptions=True),
        )

        # Normalize exceptions to None for reporting and return type
        results: List[Optional[Path]] = [
            r if isinstance(r, (Path, type(None))) else None for r in raw_results
        ]

        # Save FAISS index
        if self.faiss_index is not None:
            self._save_faiss_index()

        # Generate report
        elapsed = time.time() - start_time
        self._report_batch_results(results, elapsed)

        return results

    def _write_file(self, file_path: Path, content: str) -> bool:
        """Write file to disk"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.debug(f"File written: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error writing file {file_path}: {e}")
            return False

    def _embed_file(self, file_path: Path) -> Optional[np.ndarray]:
        """Generate embedding for file content"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            # mypy: embedding_model is checked before calling this function
            assert self.embedding_model is not None
            vector = self.embedding_model.encode(content)
            self.total_embeddings_generated += 1
            logger.debug(f"Embedding generated for: {file_path}")
            return np.array(vector, dtype="float32")
        except Exception as e:
            logger.error(f"Error embedding file {file_path}: {e}")
            return None

    def _store_in_faiss(self, file_name: str, vector: np.ndarray) -> bool:
        """Store vector in FAISS index"""
        try:
            assert self.faiss_index is not None
            self.faiss_index.add(np.expand_dims(vector, axis=0))
            self.file_id_map[self.faiss_index.ntotal - 1] = file_name
            logger.debug(f"Stored in FAISS: {file_name}")
            return True
        except Exception as e:
            logger.error(f"Error storing {file_name} in FAISS: {e}")
            return False

    def _store_in_redis(self, file_path: Path) -> bool:
        """Store file metadata in Redis"""
        try:
            metadata = {
                "status": "stored",
                "timestamp": time.time(),
                "size_bytes": file_path.stat().st_size,
                "path": str(file_path),
            }
            assert self.redis_client is not None
            self.redis_client.set(file_path.name, json.dumps(metadata))
            logger.debug(f"Metadata stored in Redis: {file_path.name}")
            return True
        except Exception as e:
            logger.error(f"Error storing {file_path.name} in Redis: {e}")
            return False

    def _save_faiss_index(self):
        """Persist FAISS index to disk"""
        try:
            faiss.write_index(self.faiss_index, str(self.faiss_index_file))
            logger.info(f"FAISS index persisted: {self.faiss_index_file}")
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")

    def _report_batch_results(
        self, results: List[Optional[Path]], elapsed: float
    ) -> Dict[str, Any]:
        """
        Generate GODMODE batch report.

        Args:
            results: List of results from batch operation
            elapsed: Elapsed time in seconds

        Returns:
            Summary dict with severity counts
        """
        summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}

        success_count = 0
        for res in results:
            if res is None:
                summary["HIGH"] += 1
            else:
                summary["MEDIUM"] += 1
                success_count += 1

        # Calculate metrics
        total = len(results)
        success_rate = (success_count / total * 100) if total > 0 else 0
        throughput = total / elapsed if elapsed > 0 else 0

        logger.info("=" * 60)
        logger.info("🎯 GODMODE Parallel File Creation Summary")
        logger.info("=" * 60)
        logger.info(f"Total Files: {total}")
        logger.info(f"Success: {success_count} ({success_rate:.1f}%)")
        logger.info(f"Failures: {total - success_count}")
        logger.info(f"Elapsed: {elapsed:.2f}s")
        logger.info(f"Throughput: {throughput:.1f} files/sec")
        logger.info("-" * 60)
        logger.info("Severity Breakdown:")
        for severity, count in summary.items():
            if count > 0:
                logger.info(f"  {severity}: {count}")
        logger.info("=" * 60)

        return {
            **summary,
            "total": total,
            "success_count": success_count,
            "success_rate": success_rate,
            "elapsed_seconds": elapsed,
            "throughput": throughput,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get creator statistics"""
        return {
            "total_files_created": self.total_files_created,
            "total_embeddings_generated": self.total_embeddings_generated,
            "total_errors": self.total_errors,
            "faiss_index_size": self.faiss_index.ntotal if self.faiss_index else 0,
            "embeddings_enabled": self._embeddings_enabled,
            "faiss_enabled": self._faiss_enabled,
            "redis_enabled": self._redis_enabled,
        }


# Convenience function
async def create_files_parallel(
    file_tasks: List[Dict[str, str]],
    base_dir: Path = Path("projects/output_files"),
    max_workers: int = 8,
) -> List[Optional[Path]]:
    """
    Convenience function for parallel file creation.

    Args:
        file_tasks: List of dicts with 'name' and 'content' keys
        base_dir: Base directory for files
        max_workers: Maximum concurrent workers

    Returns:
        List of created file paths
    """
    creator = ParallelFileCreator(base_dir=base_dir, max_workers=max_workers)
    return await creator.create_files_parallel(file_tasks)


# Example usage
if __name__ == "__main__":

    async def main():
        file_tasks = [
            {"name": f"file_{i}.txt", "content": f"Content for file {i}"} for i in range(50)
        ]

        creator = ParallelFileCreator(base_dir=Path("projects/output_files"), max_workers=8)

        await creator.create_files_parallel(file_tasks)
        stats = creator.get_stats()

        print("\nFinal Statistics:")
        print(json.dumps(stats, indent=2))

    asyncio.run(main())
