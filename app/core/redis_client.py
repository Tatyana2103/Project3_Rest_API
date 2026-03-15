import redis.asyncio as redis
from app.config import get_settings
import json
from typing import Optional, Any
from datetime import datetime

settings = get_settings()


class RedisClient:
    def __init__(self):
        self.client = None
    
    async def init(self):
        self.client = await redis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
    
    async def close(self):
        if self.client:
            await self.client.close()
    
    async def get(self, key: str) -> Optional[str]:
        return await self.client.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = settings.CACHE_TTL):
        if isinstance(value, (dict, list)):
            value = json.dumps(value, default=self.json_serializer)
        await self.client.setex(key, ttl, value)
    
    async def delete(self, key: str):
        await self.client.delete(key)
    
    async def delete_pattern(self, pattern: str):
        keys = await self.client.keys(pattern)
        if keys:
            await self.client.delete(*keys)
    
    def json_serializer(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")


redis_client = RedisClient()


async def get_redis():
    return redis_client