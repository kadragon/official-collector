"""
Embedding cache module for reducing duplicate API calls

Provides in-memory LRU cache for embeddings to avoid redundant OpenAI API calls.
"""

import hashlib
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass
from collections import OrderedDict

logger = logging.getLogger(__name__)


@dataclass
class CachedEmbedding:
    """Cached embedding entry"""

    text: str
    embedding: List[float]
    identifier: str


class EmbeddingCache:
    """
    LRU cache for embeddings.

    Stores embeddings in memory to avoid duplicate API calls for the same text.
    Uses LRU (Least Recently Used) eviction policy.
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize embedding cache.

        Args:
            max_size: Maximum number of embeddings to cache (default: 1000)
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, CachedEmbedding] = OrderedDict()
        self._hit_count = 0
        self._miss_count = 0

    def _get_key(self, text: str) -> str:
        """Generate cache key from text using SHA256 hash"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[List[float]]:
        """
        Get embedding from cache.

        Args:
            text: Text to look up

        Returns:
            Cached embedding if found, None otherwise
        """
        key = self._get_key(text)

        if key in self._cache:
            # Move to end (mark as recently used)
            self._cache.move_to_end(key)
            self._hit_count += 1

            cached = self._cache[key]
            logger.debug(
                "Embedding cache HIT: %s (size: %d)",
                cached.identifier[:50],
                len(self._cache),
            )
            return cached.embedding

        self._miss_count += 1
        logger.debug("Embedding cache MISS: %s", text[:50])
        return None

    def put(self, text: str, embedding: List[float], identifier: str = "") -> None:
        """
        Store embedding in cache.

        Args:
            text: Original text
            embedding: Embedding vector
            identifier: Optional identifier for logging
        """
        key = self._get_key(text)

        # Update existing entry
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = CachedEmbedding(text, embedding, identifier)
            logger.debug("Embedding cache UPDATE: %s", identifier[:50])
            return

        # Add new entry
        self._cache[key] = CachedEmbedding(text, embedding, identifier)

        # Evict oldest if over limit
        if len(self._cache) > self.max_size:
            evicted_key, evicted_entry = self._cache.popitem(last=False)
            logger.debug(
                "Embedding cache EVICT: %s (size: %d -> %d)",
                evicted_entry.identifier[:50],
                len(self._cache) + 1,
                len(self._cache),
            )

        logger.debug(
            "Embedding cache PUT: %s (size: %d)", identifier[:50], len(self._cache)
        )

    def clear(self) -> None:
        """Clear all cached embeddings"""
        size = len(self._cache)
        self._cache.clear()
        self._hit_count = 0
        self._miss_count = 0
        logger.info("Embedding cache cleared (%d entries removed)", size)

    def get_stats(self) -> Dict[str, int | float]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (size, hits, misses, hit_rate)
        """
        total = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total * 100) if total > 0 else 0.0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hit_count,
            "misses": self._miss_count,
            "total_requests": total,
            "hit_rate_percent": hit_rate,
        }


# Global cache instance
_embedding_cache: Optional[EmbeddingCache] = None


def get_embedding_cache() -> EmbeddingCache:
    """Get global embedding cache instance (singleton)"""
    global _embedding_cache
    if _embedding_cache is None:
        _embedding_cache = EmbeddingCache()
    return _embedding_cache


def init_embedding_cache(max_size: int = 1000) -> EmbeddingCache:
    """
    Initialize global embedding cache with custom settings.

    Args:
        max_size: Maximum number of embeddings to cache

    Returns:
        Configured EmbeddingCache instance
    """
    global _embedding_cache
    _embedding_cache = EmbeddingCache(max_size=max_size)
    logger.info("Embedding cache initialized (max_size: %d)", max_size)
    return _embedding_cache
