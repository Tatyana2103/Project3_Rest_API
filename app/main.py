from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from app.core.database import engine, AsyncSessionLocal
from app.core.redis_client import redis_client
from app.models import Base
from app.auth.router import router as auth_router
from app.links.router import router as links_router
from app.links.service import LinkService


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Создание таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Инициализация Redis
    await redis_client.init()
    
    # Запуск фоновой задачи для очистки истекших ссылок
    async def cleanup_task():
        while True:
            await asyncio.sleep(60) 
            async with AsyncSessionLocal() as db:
                await LinkService.cleanup_expired_links(db)
    
    task = asyncio.create_task(cleanup_task())
    
    yield
    
    task.cancel()
    await redis_client.close()
    await engine.dispose()


app = FastAPI(
    title="URL Shortener Service",
    description="Service for shortening URLs with analytics",
    version="1.0.0",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
app.include_router(links_router)


@app.get("/")
async def root():
    return {
        "message": "URL Shortener Service",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}