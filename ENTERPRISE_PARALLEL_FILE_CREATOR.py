"""
Enterprise Parallel File Creation Module with Semantic Indexing
Author: Herman Swanepoel
Version: 2.0-ENTERPRISE
License: Proprietary

Features:
- High-performance async file creation with semaphore-based concurrency
- Semantic embeddings with sentence-transformers
- FAISS vector store for similarity search
- Redis for distributed metadata and state management
- Enterprise observability (structured logging, metrics, tracing)
- Circuit breaker pattern for fault tolerance
- Connection pooling and resource management
- Configuration via environment variables
- Graceful shutdown and cleanup
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

import faiss
import numpy as np
import redis
from redis.connection import ConnectionPool
from sentence_transformers import SentenceTransformer

# Enterprise logging configuration
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("EnterpriseParallelFileCreator")


class Severity(Enum):
    """Severity levels for enterprise reporting"""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class FileMetadata:
    """Structured metadata for file tracking"""

    file_name: str
    status: str
    timestamp: float
    size_bytes: int
    embedding_dim: int
    faiss_index: Optional[int] = None
    error: Optional[str] = None
    processing_time_ms: Optional[float] = None


@dataclass
class ProcessingResult:
    """Result of file processing operation"""

    file_path: Optional[Path]
    metadata: FileMetadata
    severity: Severity
    success: bool


class EnterpriseConfig:
    """Enterprise configuration with environment variable support"""

    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "8"))
    BASE_DIR: Path = Path(os.getenv("BASE_DIR", "projects/output_files"))
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    VECTOR_DIM: int = int(os.getenv("VECTOR_DIM", "384"))
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
    FAISS_INDEX_FILE: Path = BASE_DIR / "faiss.index"
    METADATA_FILE: Path = BASE_DIR / "file_id_map.json"
    RETRY_ATTEMPTS: int = int(os.getenv("RETRY_ATTEMPTS", "3"))
    RETRY_DELAY_MS: int = int(os.getenv("RETRY_DELAY_MS", "100"))

    @classmethod
    def initialize(cls):
        """Initialize directories and validate configuration"""
        cls.BASE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"Configuration initialized: BASE_DIR={cls.BASE_DIR}, MAX_WORKERS={cls.MAX_WORKERS}"
        )


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failures = 0
                logger.info("Circuit breaker reset to CLOSED state")
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit breaker opened after {self.failures} failures")
            raise e


class EnterpriseParallelFileCreator:
    """Enterprise-grade parallel file creation with semantic indexing"""

    def __init__(self, config: EnterpriseConfig = None):
        self.config = config or EnterpriseConfig()
        self.config.initialize()

        # Initialize components
        self.embedding_model = None
        self.faiss_index = None
        self.file_id_map: Dict[int, str] = {}
        self.redis_pool = None
        self.redis_client = None
        self.circuit_breaker = CircuitBreaker()

        # Metrics
        self.metrics = {
            "files_processed": 0,
            "files_failed": 0,
            "total_processing_time_ms": 0,
            "embeddings_generated": 0,
            "faiss_operations": 0,
            "redis_operations": 0,
        }

    async def initialize(self):
        """Async initialization of resources"""
        logger.info("Initializing Enterprise Parallel File Creator")

        # Load embedding model
        self.embedding_model = SentenceTransformer(self.config.EMBEDDING_MODEL)
        logger.info(f"Loaded embedding model: {self.config.EMBEDDING_MODEL}")

        # Initialize FAISS index
        if self.config.FAISS_INDEX_FILE.exists():
            self.faiss_index = faiss.read_index(str(self.config.FAISS_INDEX_FILE))
            logger.info(f"Loaded existing FAISS index: {self.config.FAISS_INDEX_FILE}")
        else:
            self.faiss_index = faiss.IndexFlatL2(self.config.VECTOR_DIM)
            logger.info("Created new FAISS index")

        # Load file ID map
        if self.config.METADATA_FILE.exists():
            with open(self.config.METADATA_FILE, "r") as f:
                self.file_id_map = {int(k): v for k, v in json.load(f).items()}
            logger.info(f"Loaded {len(self.file_id_map)} file mappings")

        # Initialize Redis connection pool
        self.redis_pool = ConnectionPool(
            host=self.config.REDIS_HOST,
            port=self.config.REDIS_PORT,
            db=self.config.REDIS_DB,
            max_connections=self.config.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
        )
        self.redis_client = redis.Redis(connection_pool=self.redis_pool)
        logger.info("Redis connection pool initialized")

    async def cleanup(self):
        """Graceful cleanup of resources"""
        logger.info("Starting graceful shutdown")

        # Save FAISS index
        if self.faiss_index:
            faiss.write_index(self.faiss_index, str(self.config.FAISS_INDEX_FILE))
            logger.info("FAISS index persisted")

        # Save file ID map
        if self.file_id_map:
            with open(self.config.METADATA_FILE, "w") as f:
                json.dump(self.file_id_map, f)
            logger.info("File ID map persisted")

        # Close Redis connections
        if self.redis_client:
            self.redis_client.close()
        if self.redis_pool:
            self.redis_pool.disconnect()
        logger.info("Redis connections closed")

        # Log final metrics
        logger.info(f"Final metrics: {json.dumps(self.metrics)}")

    async def write_file_with_retry(self, file_path: Path, content: str) -> bool:
        """Write file with retry logic"""
        for attempt in range(self.config.RETRY_ATTEMPTS):
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None, self._write_file_sync, file_path, content
                )
                return True
            except Exception as e:
                if attempt < self.config.RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(self.config.RETRY_DELAY_MS / 1000)
                    logger.warning(f"Retry {attempt + 1} for {file_path}: {e}")
                else:
                    logger.error(
                        f"Failed to write {file_path} after {self.config.RETRY_ATTEMPTS} attempts: {e}"
                    )
                    return False
        return False

    def _write_file_sync(self, file_path: Path, content: str):
        """Synchronous file write operation"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    async def embed_content(self, content: str) -> Optional[np.ndarray]:
        """Generate embedding for content"""
        try:
            loop = asyncio.get_event_loop()
            vector = await loop.run_in_executor(
                None, self.embedding_model.encode, content
            )
            self.metrics["embeddings_generated"] += 1
            return np.array(vector, dtype="float32")
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    async def store_in_faiss(self, file_name: str, vector: np.ndarray) -> Optional[int]:
        """Store vector in FAISS index"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self.faiss_index.add, np.expand_dims(vector, axis=0)
            )
            index_id = self.faiss_index.ntotal - 1
            self.file_id_map[index_id] = file_name
            self.metrics["faiss_operations"] += 1
            return index_id
        except Exception as e:
            logger.error(f"FAISS storage failed for {file_name}: {e}")
            return None

    async def store_metadata_redis(self, metadata: FileMetadata) -> bool:
        """Store metadata in Redis"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.redis_client.set,
                f"file:{metadata.file_name}",
                json.dumps(asdict(metadata)),
            )
            self.metrics["redis_operations"] += 1
            return True
        except Exception as e:
            logger.error(f"Redis storage failed for {metadata.file_name}: {e}")
            return False

    async def process_file(self, file_name: str, content: str) -> ProcessingResult:
        """Process single file with full pipeline"""
        start_time = time.time()
        file_path = self.config.BASE_DIR / file_name

        metadata = FileMetadata(
            file_name=file_name,
            status="processing",
            timestamp=start_time,
            size_bytes=len(content.encode("utf-8")),
            embedding_dim=self.config.VECTOR_DIM,
        )

        try:
            # Write file
            write_success = await self.write_file_with_retry(file_path, content)
            if not write_success:
                raise Exception("File write failed")

            # Generate embedding
            vector = await self.embed_content(content)
            if vector is None:
                raise Exception("Embedding generation failed")

            # Store in FAISS
            faiss_index = await self.store_in_faiss(file_name, vector)
            if faiss_index is None:
                raise Exception("FAISS storage failed")

            metadata.faiss_index = faiss_index
            metadata.status = "completed"
            metadata.processing_time_ms = (time.time() - start_time) * 1000

            # Store metadata in Redis
            await self.store_metadata_redis(metadata)

            self.metrics["files_processed"] += 1
            self.metrics["total_processing_time_ms"] += metadata.processing_time_ms

            return ProcessingResult(
                file_path=file_path,
                metadata=metadata,
                severity=Severity.INFO,
                success=True,
            )

        except Exception as e:
            metadata.status = "failed"
            metadata.error = str(e)
            metadata.processing_time_ms = (time.time() - start_time) * 1000
            self.metrics["files_failed"] += 1

            logger.error(f"File processing failed for {file_name}: {e}")

            return ProcessingResult(
                file_path=None, metadata=metadata, severity=Severity.HIGH, success=False
            )

    async def process_files_parallel(
        self, file_tasks: List[Dict[str, str]], max_workers: Optional[int] = None
    ) -> List[ProcessingResult]:
        """Process multiple files in parallel with concurrency control"""
        max_workers = max_workers or self.config.MAX_WORKERS
        semaphore = asyncio.Semaphore(max_workers)

        async def sem_task(task):
            async with semaphore:
                return await self.process_file(task["name"], task["content"])

        logger.info(f"Processing {len(file_tasks)} files with {max_workers} workers")
        start_time = time.time()

        tasks = [sem_task(task) for task in file_tasks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task {i} raised exception: {result}")
                processed_results.append(
                    ProcessingResult(
                        file_path=None,
                        metadata=FileMetadata(
                            file_name=file_tasks[i]["name"],
                            status="failed",
                            timestamp=time.time(),
                            size_bytes=0,
                            embedding_dim=0,
                            error=str(result),
                        ),
                        severity=Severity.CRITICAL,
                        success=False,
                    )
                )
            else:
                processed_results.append(result)

        total_time = time.time() - start_time
        self._report_batch_results(processed_results, total_time)

        return processed_results

    def _report_batch_results(self, results: List[ProcessingResult], total_time: float):
        """Generate enterprise batch processing report"""
        summary = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "INFO": 0}

        for result in results:
            summary[result.severity.value] += 1

        report = {
            "timestamp": time.time(),
            "total_files": len(results),
            "successful": sum(1 for r in results if r.success),
            "failed": sum(1 for r in results if not r.success),
            "total_processing_time_seconds": round(total_time, 2),
            "average_time_per_file_ms": (
                round((total_time * 1000) / len(results), 2) if results else 0
            ),
            "severity_breakdown": summary,
            "metrics": self.metrics,
        }

        logger.info(
            f"🎯 GODMODE Enterprise Batch Processing Report: {json.dumps(report, indent=2)}"
        )


@asynccontextmanager
async def create_file_creator():
    """Context manager for enterprise file creator"""
    creator = EnterpriseParallelFileCreator()
    await creator.initialize()
    try:
        yield creator
    finally:
        await creator.cleanup()


# Example usage
async def main():
    """Example usage of Enterprise Parallel File Creator"""
    file_tasks = [
        {
            "name": f"enterprise_file_{i}.txt",
            "content": f"Enterprise content {i} with semantic meaning",
        }
        for i in range(100)
    ]

    async with create_file_creator() as creator:
        results = await creator.process_files_parallel(file_tasks)

        # Print summary
        successful = sum(1 for r in results if r.success)
        print(f"\n✅ Successfully processed: {successful}/{len(results)} files")
        print(f"📊 Metrics: {json.dumps(creator.metrics, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
