"""
Context Engine - Semantic Search and Memory Persistence
Project Creator: Herman Swanepoel

Uses nomic-embed-text for embeddings, semantic search, and context recall.
Maintains session memory with vector similarity matching.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ContextEngine:
    """
    Context management with semantic search using embeddings.

    Features:
    - Generate embeddings using nomic-embed-text
    - Store and retrieve context by semantic similarity
    - Persistent cache for session memory
    - Cosine similarity matching
    """

    def __init__(self, llm_manager: Any = None, cache_path: Optional[Path] = None) -> None:
        """
        Initialize context engine with LLM manager.

        Args:
            llm_manager: LLM Manager for embedding generation
            cache_path: Path to embedding cache file
        """
        self.llm_manager = llm_manager
        self.embed_model = "nomic-embed-text"
        self.cache_path = cache_path or Path(".aura_embed_cache.json")
        self.embed_db: Dict[str, List[float]] = {}

        # Load existing cache
        self._load_cache()
        logger.info("Context Engine initialized with %d cached embeddings", len(self.embed_db))

    def _load_cache(self) -> None:
        """Load embeddings from cache file."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r") as f:
                    self.embed_db = json.load(f)
                logger.info("Loaded %d embeddings from cache", len(self.embed_db))
            except Exception as e:
                logger.warning("Failed to load embed cache: %s", e)
                self.embed_db = {}
        else:
            self.embed_db = {}

    def _persist_cache(self) -> None:
        """Persist embeddings to cache file."""
        try:
            with open(self.cache_path, "w") as f:
                json.dump(self.embed_db, f)
            logger.debug("Persisted %d embeddings to cache", len(self.embed_db))
        except Exception as e:
            logger.error("Failed to persist embed cache: %s", e)

    async def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector (list of floats) or None if failed
        """
        if not self.llm_manager:
            logger.warning("Embedding skipped: no LLM manager available")
            return None

        try:
            # Use LLM manager to generate embedding
            # Note: Ollama's nomic-embed-text returns raw vector output
            response_text = await self.llm_manager.generate(
                prompt=text,
                system_prompt="",  # No system prompt needed for embeddings
                model=self.embed_model,
                temperature=0.0,
                max_tokens=0,  # Not applicable for embeddings
            )

            # Parse vector from response
            vector = self._parse_embedding_response(response_text)

            if vector:
                logger.debug("Generated embedding of dimension %d", len(vector))
                return vector
            else:
                logger.warning("Failed to parse embedding from response")
                return None

        except Exception as e:
            logger.error("Embedding generation failed: %s", e)
            return None

    def _parse_embedding_response(self, response: str) -> Optional[List[float]]:
        """
        Parse embedding vector from model response.

        Args:
            response: Raw model output

        Returns:
            Parsed vector or None if parsing failed
        """
        try:
            # Try JSON parsing first
            if response.startswith("["):
                return json.loads(response)

            # Try comma-separated values
            text = response.strip().replace("\n", " ")
            parts = [p.strip() for p in text.split(",") if p.strip()]

            vector = []
            for part in parts:
                try:
                    vector.append(float(part))
                except ValueError:
                    # Skip non-numeric parts
                    continue

            if len(vector) > 50:  # Sanity check for embedding dimension
                return vector
            else:
                return None

        except Exception as e:
            logger.debug("Embedding parse error: %s", e)
            return None

    async def add_context(self, key: str, text: str, force: bool = False) -> bool:
        """
        Add text to context database with embedding.

        Args:
            key: Unique identifier for this context
            text: Text content to embed and store
            force: Force re-embedding even if key exists

        Returns:
            True if successfully added/updated
        """
        if key in self.embed_db and not force:
            logger.debug("Context key %s already exists (skip)", key)
            return True

        vector = await self.embed_text(text)
        if vector:
            self.embed_db[key] = vector
            self._persist_cache()
            logger.info("Added context: %s", key)
            return True
        else:
            logger.warning("Failed to add context: %s", key)
            return False

    def cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec_a: First vector
            vec_b: Second vector

        Returns:
            Similarity score (0.0 to 1.0)
        """
        try:
            # Calculate magnitudes
            mag_a = sum(x * x for x in vec_a) ** 0.5
            mag_b = sum(x * x for x in vec_b) ** 0.5

            if mag_a == 0 or mag_b == 0:
                return 0.0

            # Calculate dot product
            dot_product = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))

            # Cosine similarity
            similarity = dot_product / (mag_a * mag_b)

            return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]

        except Exception as e:
            logger.error("Cosine similarity calculation failed: %s", e)
            return 0.0

    async def retrieve_similar(
        self, query: str, top_k: int = 3, min_similarity: float = 0.5
    ) -> List[Tuple[str, float]]:
        """
        Retrieve most similar contexts to query.

        Args:
            query: Query text to search for
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (key, similarity_score) tuples, sorted by similarity
        """
        query_vector = await self.embed_text(query)
        if not query_vector:
            logger.warning("Failed to embed query for similarity search")
            return []

        # Calculate similarities
        scored: List[Tuple[str, float]] = []
        for key, stored_vector in self.embed_db.items():
            try:
                similarity = self.cosine_similarity(query_vector, stored_vector)
                if similarity >= min_similarity:
                    scored.append((key, similarity))
            except Exception as e:
                logger.debug("Similarity calc failed for %s: %s", key, e)
                continue

        # Sort by similarity (descending)
        scored.sort(key=lambda x: x[1], reverse=True)

        # Return top_k results
        results = scored[:top_k]
        logger.info("Retrieved %d similar contexts for query (top_k=%d)", len(results), top_k)
        return results

    async def get_context_snippets(self, query: str, top_k: int = 3) -> List[str]:
        """
        Get formatted context snippets for a query.

        Args:
            query: Query text
            top_k: Number of snippets to return

        Returns:
            List of formatted context strings
        """
        similar = await self.retrieve_similar(query, top_k=top_k)
        snippets = []

        for key, similarity in similar:
            snippets.append(f"Context match ({similarity:.2f}): {key}")

        return snippets

    def clear_cache(self):
        """Clear all embeddings from memory and cache."""
        self.embed_db.clear()
        self._persist_cache()
        logger.info("Context cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the context engine."""
        return {
            "total_embeddings": len(self.embed_db),
            "cache_path": str(self.cache_path),
            "embed_model": self.embed_model,
        }
