import secrets
import string
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, delete
from sqlalchemy.orm import selectinload
from app.models import Link, User
from app.schemas import LinkCreate, LinkUpdate
from app.config import get_settings
from app.core.cache import cache_key_builder, redis_client
import json

settings = get_settings()


class LinkService:
    @staticmethod
    def generate_short_code(length: int = 6) -> str:
        """Генерирует случайный короткий код"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    async def is_code_available(code: str, db: AsyncSession) -> bool:
        """Проверяет доступность короткого кода"""
        result = await db.execute(
            select(Link).where(Link.short_code == code)
        )
        return result.scalar_one_or_none() is None
    
    @staticmethod
    async def cleanup_expired_links(db: AsyncSession):
        """Удаляет истекшие ссылки"""
        now = datetime.utcnow()
        await db.execute(
            delete(Link).where(
                and_(
                    Link.expires_at.isnot(None),
                    Link.expires_at < now
                )
            )
        )
        await db.commit()
    
    @staticmethod
    async def create_link(
        link_data: LinkCreate,
        db: AsyncSession,
        user: Optional[User] = None
    ) -> Link:
        """Создает новую короткую ссылку"""
        # Проверка кастомного алиаса
        short_code = link_data.custom_alias
        if short_code:
            if not await LinkService.is_code_available(short_code, db):
                raise ValueError("Custom alias already in use")
        else:
            # Генерация уникального кода
            for _ in range(10):  # Максимум 10 попыток
                short_code = LinkService.generate_short_code()
                if await LinkService.is_code_available(short_code, db):
                    break
            else:
                raise ValueError("Could not generate unique short code")
        
        # Создание ссылки
        new_link = Link(
            short_code=short_code,
            original_url=str(link_data.original_url),
            custom_alias=link_data.custom_alias,
            expires_at=link_data.expires_at,
            user_id=user.id if user else None
        )
        
        db.add(new_link)
        await db.commit()
        await db.refresh(new_link)
        
        # Инвалидация кэша
        if user:
            await redis_client.delete_pattern(f"user_links:{user.id}")
        
        return new_link
    
    @staticmethod
    async def get_link_by_code(
        short_code: str,
        db: AsyncSession,
        increment_clicks: bool = False
    ) -> Optional[Link]:
        """Получает ссылку по короткому коду"""
        # Проверка кэша
        cache_key = cache_key_builder("link:redirect", short_code=short_code)
        cached = await redis_client.get(cache_key)
        
        if cached and not increment_clicks:
            data = json.loads(cached)
            # Проверка на истечение
            if data.get('expires_at'):
                expires_at = datetime.fromisoformat(data['expires_at'])
                if expires_at < datetime.utcnow():
                    await redis_client.delete(cache_key)
                    return None
            return data
        
        # Поиск в БД
        result = await db.execute(
            select(Link).where(
                and_(
                    Link.short_code == short_code,
                    Link.is_active == True
                )
            )
        )
        link = result.scalar_one_or_none()
        
        if link:
            # Проверка истечения
            if link.expires_at and link.expires_at < datetime.utcnow():
                await db.delete(link)
                await db.commit()
                return None
            
            if increment_clicks:
                link.clicks += 1
                link.last_accessed = datetime.utcnow()
                await db.commit()
                await db.refresh(link)
            
            # Кэширование
            link_data = {
                'id': link.id,
                'short_code': link.short_code,
                'original_url': link.original_url,
                'expires_at': link.expires_at.isoformat() if link.expires_at else None
            }
            await redis_client.set(cache_key, link_data)
            
            return link
        
        return None
    
    @staticmethod
    async def update_link(
        short_code: str,
        link_update: LinkUpdate,
        db: AsyncSession,
        user: User
    ) -> Optional[Link]:
        """Обновляет оригинальный URL ссылки"""
        result = await db.execute(
            select(Link).where(
                and_(
                    Link.short_code == short_code,
                    Link.user_id == user.id
                )
            )
        )
        link = result.scalar_one_or_none()
        
        if not link:
            return None
        
        link.original_url = str(link_update.original_url)
        await db.commit()
        await db.refresh(link)
        
        # Инвалидация кэша
        await redis_client.delete_pattern(f"link:*{short_code}*")
        
        return link
    
    @staticmethod
    async def delete_link(
        short_code: str,
        db: AsyncSession,
        user: User
    ) -> bool:
        """Удаляет ссылку"""
        result = await db.execute(
            select(Link).where(
                and_(
                    Link.short_code == short_code,
                    Link.user_id == user.id
                )
            )
        )
        link = result.scalar_one_or_none()
        
        if not link:
            return False
        
        await db.delete(link)
        await db.commit()
        
        # Инвалидация кэша
        await redis_client.delete_pattern(f"link:*{short_code}*")
        await redis_client.delete_pattern(f"user_links:{user.id}")
        
        return True
    
    @staticmethod
    async def get_link_stats(
        short_code: str,
        db: AsyncSession,
        user: Optional[User] = None
    ) -> Optional[Link]:
        """Получает статистику по ссылке"""
        # Проверка кэша для публичных ссылок
        if not user:
            cache_key = cache_key_builder("link:stats", short_code=short_code)
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        
        # Поиск в БД
        query = select(Link).where(Link.short_code == short_code)
        
        # Если пользователь не владелец, проверяем публичный доступ
        if user:
            query = query.where(Link.user_id == user.id)
        
        result = await db.execute(query)
        link = result.scalar_one_or_none()
        
        if link and not user:
            # Кэшируем публичную статистику
            stats_data = {
                'id': link.id,
                'short_code': link.short_code,
                'original_url': link.original_url,
                'created_at': link.created_at.isoformat(),
                'clicks': link.clicks,
                'last_accessed': link.last_accessed.isoformat() if link.last_accessed else None,
                'expires_at': link.expires_at.isoformat() if link.expires_at else None
            }
            cache_key = cache_key_builder("link:stats", short_code=short_code)
            await redis_client.set(cache_key, stats_data)
        
        return link
    
    @staticmethod
    async def search_by_original_url(
        original_url: str,
        db: AsyncSession,
        user: Optional[User] = None
    ) -> List[Link]:
        """Поиск ссылок по оригинальному URL"""
        # Проверка кэша
        cache_key = cache_key_builder("search", url=original_url, user_id=user.id if user else "public")
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Поиск в БД
        query = select(Link).where(Link.original_url.contains(original_url))
        
        if user:
            query = query.where(Link.user_id == user.id)
        
        result = await db.execute(query)
        links = result.scalars().all()
        
        # Кэширование результатов
        links_data = [
            {
                'id': link.id,
                'short_code': link.short_code,
                'original_url': link.original_url,
                'short_url': f"{settings.BASE_URL}/{link.short_code}",
                'created_at': link.created_at.isoformat(),
                'clicks': link.clicks
            }
            for link in links
        ]
        await redis_client.set(cache_key, links_data)
        
        return links
    
    @staticmethod
    async def get_user_links(
        user: User,
        db: AsyncSession
    ) -> List[Link]:
        """Получает все ссылки пользователя"""
        # Проверка кэша
        cache_key = cache_key_builder("user_links", user_id=user.id)
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Поиск в БД
        result = await db.execute(
            select(Link).where(Link.user_id == user.id)
        )
        links = result.scalars().all()
        
        # Кэширование
        links_data = [
            {
                'id': link.id,
                'short_code': link.short_code,
                'original_url': link.original_url,
                'short_url': f"{settings.BASE_URL}/{link.short_code}",
                'created_at': link.created_at.isoformat(),
                'clicks': link.clicks,
                'expires_at': link.expires_at.isoformat() if link.expires_at else None
            }
            for link in links
        ]
        await redis_client.set(cache_key, links_data)
        
        return links