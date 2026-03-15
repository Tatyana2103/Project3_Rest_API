from fastapi import Request, HTTPException, status
from app.core.redis_client import redis_client


async def rate_limiter(request: Request):
    """ rate limiter для API"""
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"
    
    current = await redis_client.get(key)
    if current and int(current) > 100: 
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )
    
    await redis_client.client.incr(key)
    await redis_client.client.expire(key, 60)