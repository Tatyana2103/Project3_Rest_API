from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from fastapi.responses import RedirectResponse

from app.core.database import get_db
from app.core.redis_client import get_redis, RedisClient
from app.links.service import LinkService
from app.auth.utils import get_current_active_user, get_current_user
from app.models import User
from app.schemas import (
    LinkCreate, LinkResponse, LinkUpdate,
    LinkStats, LinkSearch
)
from app.config import get_settings

router = APIRouter(prefix="/links", tags=["links"])
settings = get_settings()


@router.post("/shorten", response_model=LinkResponse)
async def create_short_link(
    link_data: LinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    redis: RedisClient = Depends(get_redis)
):
    """
    Создает короткую ссылку
    - Доступно всем пользователям
    - Можно указать кастомный alias
    - Можно указать время жизни
    """
    try:
        link = await LinkService.create_link(
            link_data=link_data,
            db=db,
            user=current_user
        )
        
        return {
            **link.__dict__,
            "short_url": f"{settings.BASE_URL}/{link.short_code}"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{short_code}")
async def redirect_to_original(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis)
):
    """
    Перенаправляет на оригинальный URL
    - Доступно всем
    - Считает клики
    """
    link = await LinkService.get_link_by_code(
        short_code=short_code,
        db=db,
        increment_clicks=True
    )
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found or expired"
        )
    
    return RedirectResponse(url=link.original_url)


@router.get("/{short_code}/stats", response_model=LinkStats)
async def get_link_stats(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    redis: RedisClient = Depends(get_redis)
):
    """
    Получает статистику по ссылке
    - Доступно всем (публичная статистика)
    - Для приватных ссылок нужно быть владельцем
    """
    link = await LinkService.get_link_stats(
        short_code=short_code,
        db=db,
        user=current_user
    )
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found"
        )
    
    return {
        **link.__dict__,
        "short_url": f"{settings.BASE_URL}/{link.short_code}"
    }


@router.put("/{short_code}", response_model=LinkResponse)
async def update_link(
    short_code: str,
    link_update: LinkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    redis: RedisClient = Depends(get_redis)
):
    """
    Обновляет оригинальный URL ссылки
    - Только для авторизованных пользователей
    - Только владелец может обновить
    """
    link = await LinkService.update_link(
        short_code=short_code,
        link_update=link_update,
        db=db,
        user=current_user
    )
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found or you don't have permission"
        )
    
    return {
        **link.__dict__,
        "short_url": f"{settings.BASE_URL}/{link.short_code}"
    }


@router.delete("/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    short_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    redis: RedisClient = Depends(get_redis)
):
    """
    Удаляет ссылку
    - Только для авторизованных пользователей
    - Только владелец может удалить
    """
    deleted = await LinkService.delete_link(
        short_code=short_code,
        db=db,
        user=current_user
    )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found or you don't have permission"
    )


@router.get("/search", response_model=List[LinkSearch])
async def search_links(
    original_url: str = Query(..., description="Original URL to search"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    redis: RedisClient = Depends(get_redis)
):
    """
    Поиск ссылок по оригинальному URL
    - Доступно всем (публичные ссылки)
    - Авторизованные пользователи видят и свои ссылки
    """
    links = await LinkService.search_by_original_url(
        original_url=original_url,
        db=db,
        user=current_user
    )
    
    return [
        {
            "original_url": link.original_url,
            "short_code": link.short_code,
            "short_url": f"{settings.BASE_URL}/{link.short_code}",
            "created_at": link.created_at,
            "clicks": link.clicks
        }
        for link in links
    ]


@router.get("/user/me", response_model=List[LinkResponse])
async def get_my_links(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    redis: RedisClient = Depends(get_redis)
):
    """
    Получает все ссылки текущего пользователя
    - Только для авторизованных
    """
    links = await LinkService.get_user_links(
        user=current_user,
        db=db
    )
    
    return [
        {
            **link.__dict__,
            "short_url": f"{settings.BASE_URL}/{link.short_code}"
        }
        for link in links
    ]