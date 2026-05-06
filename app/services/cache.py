import threading

from cachetools import TTLCache

_lock = threading.Lock()

# TTL=60s, maxsize=1000 entries.
_cache: TTLCache = TTLCache(maxsize=1000, ttl=60)


def get_cache() -> TTLCache:
    """Return the shared cache instance."""
    return _cache


def cache_get(key: str):
    """
    Retrieve a value from the cache.
    Returns None if the key is missing or expired.
    """
    with _lock:
        return _cache.get(key)


def cache_set(key: str, value) -> None:
    """Store a value in the cache."""
    with _lock:
        _cache[key] = value


def cache_invalidate() -> None:
    """
    Clear the entire cache.
    """
    with _lock:
        _cache.clear()
