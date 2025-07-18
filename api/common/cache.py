"""
Module for caching functionality to improve performance when database is far from client.
"""
import json
import os
from datetime import timedelta
from typing import Any, Optional, Union, Dict, List, Set
import asyncio

import redis
from fastapi import HTTPException

# Get Redis connection string from environment variable or use default
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
# Cache TTL in seconds (default: 10 minutes)
DEFAULT_CACHE_TTL = int(os.environ.get("CACHE_TTL", 600))
# Store products cache TTL (default: 30 minutes)
STORE_PRODUCTS_TTL = int(os.environ.get("STORE_PRODUCTS_TTL", 1800))

# Global Redis client
redis_client = None

def get_redis_client():
    """
    Get or create a Redis client instance.
    """
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis.from_url(
                REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Ping Redis to ensure connection works
            redis_client.ping()
        except redis.exceptions.ConnectionError as e:
            print(f"Warning: Redis connection failed: {e}. Caching disabled.")
            redis_client = None
        except Exception as e:
            print(f"Warning: Redis initialization error: {e}. Caching disabled.")
            redis_client = None

    return redis_client

async def get_cache(key: str) -> Optional[Any]:
    """
    Get a value from cache by key.

    Args:
        key: The cache key to retrieve

    Returns:
        The cached value if found, otherwise None
    """
    client = get_redis_client()
    if not client:
        return None

    try:
        data = client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        print(f"Cache get error: {e}")
        return None

async def set_cache(key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL) -> bool:
    """
    Set a value in cache with optional TTL.

    Args:
        key: The cache key
        value: The value to cache (must be JSON serializable)
        ttl: Time to live in seconds (default: 10 minutes)

    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        serialized = json.dumps(value)
        return client.set(key, serialized, ex=ttl)
    except Exception as e:
        print(f"Cache set error: {e}")
        return False

async def delete_cache(key: str) -> bool:
    """
    Delete a value from cache by key.

    Args:
        key: The cache key to delete

    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if not client:
        return False

    try:
        return client.delete(key) > 0
    except Exception as e:
        print(f"Cache delete error: {e}")
        return False

async def delete_pattern(pattern: str) -> int:
    """
    Delete all keys matching a pattern.

    Args:
        pattern: The pattern to match (e.g., "products:*")

    Returns:
        Number of keys deleted
    """
    client = get_redis_client()
    if not client:
        return 0

    try:
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        print(f"Cache delete pattern error: {e}")
        return 0

def generate_cache_key(prefix: str, params: Dict[str, Any]) -> str:
    """
    Generate a cache key from a prefix and parameters.

    Args:
        prefix: The prefix for the key (e.g., "products")
        params: Dictionary of parameters to include in the key

    Returns:
        A cache key string
    """
    # Sort params to ensure consistent keys
    sorted_params = sorted((k, str(v)) for k, v in params.items() if v is not None)
    param_str = ":".join(f"{k}={v}" for k, v in sorted_params)
    return f"{prefix}:{param_str}" if param_str else prefix

async def cache_store_products(store_id: str, products: List[Dict]) -> bool:
    """
    Cache all products for a store for faster searching.

    Args:
        store_id: The store ID
        products: List of product dictionaries

    Returns:
        True if successful, False otherwise
    """
    cache_key = f"store_products:{store_id}"
    return await set_cache(cache_key, products, STORE_PRODUCTS_TTL)

async def get_cached_store_products(store_id: str) -> Optional[List[Dict]]:
    """
    Get all cached products for a store.

    Args:
        store_id: The store ID

    Returns:
        List of product dictionaries if found, otherwise None
    """
    cache_key = f"store_products:{store_id}"
    return await get_cache(cache_key)

# Background task to pre-warm cache
async def background_cache_warm(store_id: str, fetch_func) -> None:
    """
    Background task to pre-warm cache for a store.

    Args:
        store_id: The store ID
        fetch_func: Function to fetch products from database
    """
    try:
        # Wait a short time before warming cache to avoid blocking
        await asyncio.sleep(1)

        # Fetch products
        products = await fetch_func(store_id)

        # Cache store products
        await cache_store_products(store_id, products)
        print(f"Cache warmed for store {store_id}")
    except Exception as e:
        print(f"Cache warming error for store {store_id}: {e}")
