from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):

    DATABASE_URL: str = "postgresql+asyncpg://user:password@db:5432/urlshortener"
    

    REDIS_URL: str = "redis://redis:6379"
    
    # Security
    SECRET_KEY: str = "tate21"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    BASE_URL: str = "http://localhost:8000"
    
    CACHE_TTL: int = 3600  # 1 hour
    
    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()