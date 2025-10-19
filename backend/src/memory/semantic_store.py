"""
Semantic Memory using FAISS and ChromaDB
Project Creator: Herman Swanepoel
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

import chromadb
import faiss
import numpy as np
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class SemanticStore:
    """
    Long-term embeddings for code patterns using FAISS and ChromaDB.

    Combines FAISS for fast similarity search with ChromaDB for
    metadata storage and filtering.
    """

    def __init__(
        self,
        dimension: int = 768,
        persist_directory: str = "./data/chroma_db",
        collection_name: str = "code_patterns",
    ):
        """
        Initialize semantic store.

        Args:
            dimension: Embedding dimension
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of ChromaDB collection
        """
        self.dimension = dimension
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # Initialize FAISS index
        self.index = faiss.IndexFlatL2(dimension)
        self.id_to_index: Dict[str, int] = {}
        self.index_to_id: Dict[int, str] = {}
        self.next_index = 0

        # Initialize ChromaDB
        try:
            self.chroma_client = chromadb.Client(
                Settings(persist_directory=persist_directory, anonymized_telemetry=False)
            )
            self.collection = self.chroma_client.get_or_create_collection(name=collection_name)
            logger.info(f"SemanticStore initialized with dimension={dimension}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise

    def add_embedding(
        self,
        embedding: np.ndarray,
        metadata: Dict[str, Any],
        doc_id: Optional[str] = None,
    ) -> str:
        """
        Add code embedding to store.

        Args:
            embedding: Embedding vector
            metadata: Metadata dict (must include 'code', 'language', etc.)
            doc_id: Optional document ID (generated if not provided)

        Returns:
            Document ID
        """
        # Generate ID if not provided
        if doc_id is None:
            code = metadata.get("code", "")
            doc_id = hashlib.sha256(code.encode()).hexdigest()[:16]

        # Check if already exists
        if doc_id in self.id_to_index:
            logger.warning(f"Document {doc_id} already exists, skipping")
            return doc_id

        try:
            # Add to FAISS
            embedding_2d = embedding.reshape(1, -1).astype("float32")
            self.index.add(embedding_2d)

            # Track mapping
            self.id_to_index[doc_id] = self.next_index
            self.index_to_id[self.next_index] = doc_id
            self.next_index += 1

            # Add to ChromaDB
            self.collection.add(embeddings=[embedding.tolist()], metadatas=[metadata], ids=[doc_id])

            logger.debug(f"Added embedding: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Failed to add embedding: {e}")
            raise

    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[float, Dict[str, Any]]]:
        """
        Search for similar code patterns.

        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of (distance, metadata) tuples
        """
        try:
            # Search in FAISS
            query_2d = query_embedding.reshape(1, -1).astype("float32")
            distances, indices = self.index.search(query_2d, min(k * 2, self.index.ntotal))

            # Get metadata from ChromaDB
            results = []
            for dist, idx in zip(distances[0], indices[0], strict=False):
                if idx == -1:  # FAISS returns -1 for empty slots
                    continue

                doc_id = self.index_to_id.get(idx)
                if doc_id is None:
                    continue

                # Get metadata
                chroma_result = self.collection.get(ids=[doc_id], include=["metadatas"])

                if chroma_result["metadatas"]:
                    metadata = chroma_result["metadatas"][0]

                    # Apply filters if provided
                    if filter_metadata:
                        if not all(metadata.get(k) == v for k, v in filter_metadata.items()):
                            continue

                    results.append((float(dist), metadata))

                if len(results) >= k:
                    break

            logger.debug(f"Search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def search_by_metadata(self, where: Dict[str, Any], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search by metadata only (no embedding similarity).

        Args:
            where: Metadata filter dict
            limit: Maximum results

        Returns:
            List of metadata dicts
        """
        try:
            results = self.collection.query(
                query_embeddings=None,
                where=where,
                n_results=limit,
                include=["metadatas"],
            )

            return results.get("metadatas", [[]])[0]
        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            return []

    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Metadata dict or None
        """
        try:
            result = self.collection.get(ids=[doc_id], include=["metadatas", "embeddings"])

            if result["metadatas"]:
                return {
                    "metadata": result["metadatas"][0],
                    "embedding": (result["embeddings"][0] if result["embeddings"] else None),
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            return None

    def delete(self, doc_id: str) -> bool:
        """
        Delete document by ID.

        Args:
            doc_id: Document ID

        Returns:
            True if successful
        """
        try:
            # Remove from ChromaDB
            self.collection.delete(ids=[doc_id])

            # Remove from FAISS mapping
            if doc_id in self.id_to_index:
                idx = self.id_to_index[doc_id]
                del self.id_to_index[doc_id]
                del self.index_to_id[idx]

            logger.debug(f"Deleted document: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {doc_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get store statistics.

        Returns:
            Dict containing statistics
        """
        try:
            collection_count = self.collection.count()
            return {
                "total_embeddings": self.index.ntotal,
                "collection_count": collection_count,
                "dimension": self.dimension,
                "index_size_mb": self.index.ntotal * self.dimension * 4 / (1024 * 1024),
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def save_index(self, path: str) -> bool:
        """
        Save FAISS index to disk.

        Args:
            path: File path

        Returns:
            True if successful
        """
        try:
            faiss.write_index(self.index, path)
            logger.info(f"Saved FAISS index to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
            return False

    def load_index(self, path: str) -> bool:
        """
        Load FAISS index from disk.

        Args:
            path: File path

        Returns:
            True if successful
        """
        try:
            self.index = faiss.read_index(path)
            logger.info(f"Loaded FAISS index from {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load index: {e}")
            return False
