"""
Semantic code search service with caching and relevance scoring
Project Creator: Herman Swanepoel
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from collections import OrderedDict
import time
import hashlib

from src.services.embeddings_service import EmbeddingsService

logger = logging.getLogger(__name__)


class SearchCache:
    """TTL cache for search results"""
    
    def __init__(self, maxsize: int = 100, ttl: float = 300.0):
        """
        Initialize search cache
        
        Args:
            maxsize: Maximum cache size
            ttl: Time to live in seconds
        """
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: Dict[str, float] = {}
        self.maxsize = maxsize
        self.ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached result if not expired"""
        if key in self.cache:
            if time.time() - self.timestamps[key] < self.ttl:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                return self.cache[key]
            else:
                # Expired, remove
                del self.cache[key]
                del self.timestamps[key]
        return None
    
    def put(self, key: str, value: Any) -> None:
        """Store result in cache"""
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        self.timestamps[key] = time.time()
        
        # Remove oldest if over limit
        while len(self.cache) > self.maxsize:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
            del self.timestamps[oldest_key]
    
    def clear(self) -> None:
        """Clear cache"""
        self.cache.clear()
        self.timestamps.clear()


class SemanticSearchService:
    """
    Semantic code search with caching and relevance scoring
    """
    
    def __init__(self, embeddings_service: EmbeddingsService):
        """
        Initialize semantic search service
        
        Args:
            embeddings_service: Embeddings service instance
        """
        self.embeddings_service = embeddings_service
        self.search_cache = SearchCache(maxsize=100, ttl=300.0)  # 5 min TTL
        self.embedding_cache = SearchCache(maxsize=500, ttl=600.0)  # 10 min TTL
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        file_extension: Optional[str] = None,
        min_relevance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic code search with caching
        
        Args:
            query: Search query
            top_k: Number of results to return
            file_extension: Filter by file extension
            min_relevance: Minimum relevance score (0-1)
            
        Returns:
            List of search results with relevance scores
        """
        # Generate cache key
        cache_key = self._generate_cache_key(query, top_k, file_extension, min_relevance)
        
        # Check cache
        cached_result = self.search_cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"Cache hit for query: {query[:50]}")
            return cached_result
        
        # Perform search
        results = await self.embeddings_service.find_similar_code(
            query=query,
            top_k=top_k * 2,  # Get more results for filtering
            file_extension=file_extension
        )
        
        # Calculate relevance scores and filter
        scored_results = []
        for result in results:
            relevance = self._calculate_relevance(result, query)
            if relevance >= min_relevance:
                result['relevance'] = relevance
                scored_results.append(result)
        
        # Sort by relevance and limit
        scored_results.sort(key=lambda x: x['relevance'], reverse=True)
        final_results = scored_results[:top_k]
        
        # Cache results
        self.search_cache.put(cache_key, final_results)
        
        logger.debug(f"Search completed: {len(final_results)} results for '{query[:50]}'")
        return final_results
    
    async def search_by_function(
        self,
        function_name: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar functions by name
        
        Args:
            function_name: Function name to search for
            top_k: Number of results
            
        Returns:
            List of similar functions
        """
        query = f"function {function_name}"
        return await self.search(query, top_k=top_k)
    
    async def search_by_class(
        self,
        class_name: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar classes by name
        
        Args:
            class_name: Class name to search for
            top_k: Number of results
            
        Returns:
            List of similar classes
        """
        query = f"class {class_name}"
        return await self.search(query, top_k=top_k)
    
    async def search_by_concept(
        self,
        concept: str,
        language: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for code implementing a concept
        
        Args:
            concept: Concept description (e.g., "authentication", "database connection")
            language: Programming language filter
            top_k: Number of results
            
        Returns:
            List of relevant code snippets
        """
        file_ext = self._language_to_extension(language) if language else None
        return await self.search(concept, top_k=top_k, file_extension=file_ext)
    
    async def find_usage_examples(
        self,
        api_or_function: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find usage examples of an API or function
        
        Args:
            api_or_function: API or function name
            top_k: Number of examples
            
        Returns:
            List of usage examples
        """
        query = f"using {api_or_function} example"
        return await self.search(query, top_k=top_k, min_relevance=0.3)
    
    def _calculate_relevance(self, result: Dict[str, Any], query: str) -> float:
        """
        Calculate relevance score for search result
        
        Args:
            result: Search result from embeddings service
            query: Original query
            
        Returns:
            Relevance score (0-1)
        """
        # Start with distance-based score
        distance = result.get('distance', 1.0)
        base_score = max(0.0, 1.0 - distance)
        
        # Boost score based on metadata
        metadata = result.get('metadata', {})
        boost = 1.0
        
        # Boost if query terms appear in file name
        file_name = metadata.get('file_name', '').lower()
        query_lower = query.lower()
        if any(term in file_name for term in query_lower.split()):
            boost *= 1.2
        
        # Boost smaller files (more focused)
        file_size = metadata.get('size', 10000)
        if file_size < 1000:
            boost *= 1.1
        elif file_size > 10000:
            boost *= 0.9
        
        # Calculate final score
        relevance = min(1.0, base_score * boost)
        return round(relevance, 3)
    
    def _generate_cache_key(
        self,
        query: str,
        top_k: int,
        file_extension: Optional[str],
        min_relevance: float
    ) -> str:
        """Generate cache key for search parameters"""
        key_str = f"{query}|{top_k}|{file_extension}|{min_relevance}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _language_to_extension(self, language: str) -> str:
        """Convert language name to file extension"""
        lang_map = {
            'python': '.py',
            'javascript': '.js',
            'typescript': '.ts',
            'java': '.java',
            'go': '.go',
            'rust': '.rs',
            'cpp': '.cpp',
            'c': '.c',
            'csharp': '.cs',
            'ruby': '.rb',
            'php': '.php',
            'swift': '.swift',
            'kotlin': '.kt'
        }
        return lang_map.get(language.lower(), '')
    
    def clear_cache(self) -> None:
        """Clear all caches"""
        self.search_cache.clear()
        self.embedding_cache.clear()
        logger.info("Search caches cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "search_cache_size": len(self.search_cache.cache),
            "embedding_cache_size": len(self.embedding_cache.cache),
            "search_cache_maxsize": self.search_cache.maxsize,
            "search_cache_ttl": self.search_cache.ttl
        }
