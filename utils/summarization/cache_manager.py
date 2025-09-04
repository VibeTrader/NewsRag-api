import time
from typing import Dict, Any, Optional, Tuple
from loguru import logger

class CacheManager:
    """Efficient in-memory cache with TTL and size management."""
    
    def __init__(self, max_size: int = 100, default_ttl: int = 1800):
        """Initialize the cache.
        
        Args:
            max_size: Maximum number of items in cache
            default_ttl: Default TTL in seconds (30 minutes)
        """
        self.cache = {}
        self.access_times = {}  # Track last access time for LRU eviction
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0
        
    def get(self, key: str) -> Optional[Any]:
        """Get an item from the cache with automatic expiration."""
        if key not in self.cache:
            self.misses += 1
            return None
            
        entry, expiry = self.cache[key]
        current_time = time.time()
        
        # Check if entry has expired
        if current_time > expiry:
            self.delete(key)
            self.misses += 1
            return None
            
        # Update access time for LRU
        self.access_times[key] = current_time
        self.hits += 1
        return entry
        
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Add or update an item in the cache."""
        # Evict items if cache is full
        if len(self.cache) >= self.max_size and key not in self.cache:
            self._evict()
            
        # Set expiry time
        expiry = time.time() + (ttl if ttl is not None else self.default_ttl)
        
        # Update cache
        self.cache[key] = (value, expiry)
        self.access_times[key] = time.time()
        
    def delete(self, key: str) -> None:
        """Remove an item from the cache."""
        if key in self.cache:
            del self.cache[key]
        if key in self.access_times:
            del self.access_times[key]
            
    def clear(self) -> None:
        """Clear the entire cache."""
        self.cache.clear()
        self.access_times.clear()
        
    def _evict(self) -> None:
        """Evict items based on LRU policy."""
        if not self.access_times:
            return
            
        # Find least recently used item
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
        self.delete(lru_key)
        logger.debug(f"Cache eviction: removed key {lru_key}")
        
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": f"{hit_rate:.2%}",
            "hits": self.hits,
            "misses": self.misses
        }