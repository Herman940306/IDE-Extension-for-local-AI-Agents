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
    
    async def find_similar_code(
        self,
        code_snippet: str,
        top_k: int = 5,
        exclude_file: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find code similar to a given snippet
        
        Args:
            code_snippet: Code snippet to find similar code for
            top_k: Number of results
            exclude_file: File to exclude from results
            
        Returns:
            List of similar code snippets
        """
        results = await self.search(code_snippet, top_k=top_k * 2)
        
        # Filter out excluded file
        if exclude_file:
            results = [r for r in results if r.get('metadata', {}).get('file_path') != exclude_file]
        
        return results[:top_k]
    
    async def search_with_context(
        self,
        query: str,
        context_files: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search with context from specific files
        
        Args:
            query: Search query
            context_files: List of file paths to prioritize
            top_k: Number of results
            
        Returns:
            List of search results with context-aware ranking
        """
        results = await self.search(query, top_k=top_k * 2)
        
        # Boost results from context files
        for result in results:
            file_path = result.get('metadata', {}).get('file_path', '')
            if file_path in context_files:
                result['relevance'] = min(1.0, result.get('relevance', 0.5) * 1.5)
        
        # Re-sort and limit
        results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        return results[:top_k]
    
    async def search_by_error_message(
        self,
        error_message: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for code related to an error message
        
        Args:
            error_message: Error message text
            top_k: Number of results
            
        Returns:
            List of relevant code that might help fix the error
        """
        # Extract key terms from error message
        query = f"fix error {error_message}"
        return await self.search(query, top_k=top_k, min_relevance=0.2)
    
    async def search_by_file_type(
        self,
        query: str,
        file_types: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search within specific file types
        
        Args:
            query: Search query
            file_types: List of file extensions (e.g., ['.py', '.js'])
            top_k: Number of results
            
        Returns:
            List of search results from specified file types
        """
        all_results = []
        
        for file_type in file_types:
            results = await self.search(query, top_k=top_k, file_extension=file_type)
            all_results.extend(results)
        
        # Remove duplicates and sort by relevance
        seen = set()
        unique_results = []
        for result in all_results:
            file_path = result.get('metadata', {}).get('file_path', '')
            if file_path not in seen:
                seen.add(file_path)
                unique_results.append(result)
        
        unique_results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        return unique_results[:top_k]
    
    async def get_related_files(
        self,
        file_path: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find files related to a given file based on semantic similarity
        
        Args:
            file_path: Path to file
            top_k: Number of related files
            
        Returns:
            List of related files with relevance scores
        """
        # Use file path as query to find similar files
        query = f"file similar to {file_path}"
        results = await self.search(query, top_k=top_k + 1)
        
        # Exclude the file itself
        results = [r for r in results if r.get('metadata', {}).get('file_path') != file_path]
        
        return results[:top_k]
    
    def _calculate_relevance(self, result: Dict[str, Any], query: str) -> float:
        """
        Calculate relevance score for search result with advanced ranking
        
        Args:
            result: Search result from embeddings service
            query: Original query
            
        Returns:
            Relevance score (0-1)
        """
        # Start with distance-based score (cosine similarity)
        distance = result.get('distance', 1.0)
        base_score = max(0.0, 1.0 - distance)
        
        # Boost score based on metadata
        metadata = result.get('metadata', {})
        boost = 1.0
        
        # 1. File name relevance (20% boost)
        file_name = metadata.get('file_name', '').lower()
        file_path = metadata.get('file_path', '').lower()
        query_lower = query.lower()
        query_terms = set(query_lower.split())
        
        # Exact match in filename
        if query_lower in file_name:
            boost *= 1.3
        # Partial match
        elif any(term in file_name for term in query_terms if len(term) > 2):
            boost *= 1.2
        
        # 2. File size relevance (focused vs comprehensive)
        file_size = metadata.get('size', 10000)
        if file_size < 500:  # Very focused
            boost *= 1.15
        elif file_size < 2000:  # Moderately focused
            boost *= 1.1
        elif file_size > 10000:  # Large file, less focused
            boost *= 0.9
        elif file_size > 50000:  # Very large
            boost *= 0.8
        
        # 3. File type relevance
        language = metadata.get('language', '')
        if language in ['python', 'javascript', 'typescript']:  # Common languages
            boost *= 1.05
        
        # 4. Recency boost (if timestamp available)
        timestamp = metadata.get('timestamp', 0)
        if timestamp > 0:
            age_days = (time.time() - timestamp) / 86400
            if age_days < 7:  # Recent changes
                boost *= 1.1
            elif age_days < 30:
                boost *= 1.05
        
        # 5. Code quality indicators
        # Boost if file has good structure (classes, functions)
        has_classes = metadata.get('has_classes', False)
        has_functions = metadata.get('has_functions', False)
        if has_classes and has_functions:
            boost *= 1.1
        elif has_functions:
            boost *= 1.05
        
        # 6. Path depth (prefer files closer to root for common utilities)
        path_depth = file_path.count('/')
        if path_depth <= 2:  # Root level utilities
            boost *= 1.05
        
        # Calculate final score with diminishing returns on boost
        # Use logarithmic scaling to prevent extreme boosts
        import math
        adjusted_boost = 1.0 + math.log(boost) if boost > 1.0 else boost
        relevance = min(1.0, base_score * adjusted_boost)
        
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
    
    async def batch_search(
        self,
        queries: List[str],
        top_k: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Perform multiple searches in parallel
        
        Args:
            queries: List of search queries
            top_k: Number of results per query
            
        Returns:
            Dictionary mapping queries to results
        """
        tasks = [self.search(query, top_k=top_k) for query in queries]
        results = await asyncio.gather(*tasks)
        
        return {query: result for query, result in zip(queries, results)}
    
    async def rank_candidates(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Rank a list of candidate results by relevance to query
        
        Args:
            query: Search query
            candidates: List of candidate results
            
        Returns:
            Ranked list of candidates
        """
        # Calculate relevance for each candidate
        for candidate in candidates:
            relevance = self._calculate_relevance(candidate, query)
            candidate['relevance'] = relevance
        
        # Sort by relevance
        candidates.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        
        return candidates
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "search_cache_size": len(self.search_cache.cache),
            "embedding_cache_size": len(self.embedding_cache.cache),
            "search_cache_maxsize": self.search_cache.maxsize,
            "search_cache_ttl": self.search_cache.ttl,
            "cache_hit_rate": self._calculate_cache_hit_rate()
        }
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate (placeholder for future implementation)"""
        # This would require tracking hits/misses
        return 0.0
