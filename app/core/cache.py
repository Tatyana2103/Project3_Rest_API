from functools import wraps
from typing import Optional, Any
from app.core.redis_client import redis_client
import json


def cache_key_builder(prefix: str, **kwargs) -> str:
    """Строит ключ для кэша на основе параметров"""
    parts = [prefix]
    for key, value in sorted(kwargs.items()):
        if value is not None:
            parts.append(f"{key}:{value}")
    return ":".join(parts)


async def cache_get_or_set(key: str, func, ttl: int = None):
    """Получает данные из кэша или устанавливает их"""
    cached = await redis_client.get(key)
    if cached:
        return json.loads(cached)
    
    data = await func()
    if data:
        await redis_client.set(key, data, ttl)
    return data


async def invalidate_link_cache(short_code: str = None, user_id: str = None):
    """Инвалидирует кэш ссылок"""
    patterns = []
    if short_code:
        patterns.append(f"link:{short_code}")
        patterns.append(f"link:redirect:{short_code}")
        patterns.append(f"link:stats:{short_code}")
    if user_id:
        patterns.append(f"user_links:{user_id}")
    patterns.append("search:*")
    
    for pattern in patterns:
        await redis_client.delete_pattern(pattern)
