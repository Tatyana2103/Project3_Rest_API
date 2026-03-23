# tests/unit/test_link_service.py
import pytest
from datetime import datetime, timedelta
from app.links.service import LinkService
from app.schemas import LinkCreate, LinkUpdate
from app.models import Link, User


class TestLinkService:
    
    def test_generate_short_code_length(self):
        """Тест генерации короткого кода правильной длины"""
        code = LinkService.generate_short_code()
        assert len(code) == 6
        
        code_long = LinkService.generate_short_code(10)
        assert len(code_long) == 10
    
    def test_generate_short_code_uniqueness(self):
        """Тест уникальности генерируемых кодов"""
        codes = set()
        for _ in range(100):
            code = LinkService.generate_short_code()
            codes.add(code)
        
        assert len(codes) == 100
    
    def test_generate_short_code_characters(self):
        """Тест, что код содержит только допустимые символы"""
        import string
        allowed = set(string.ascii_letters + string.digits)
        
        for _ in range(100):
            code = LinkService.generate_short_code()
            assert all(c in allowed for c in code)
    
    @pytest.mark.asyncio
    async def test_is_code_available(self, db_session):
        """Тест проверки доступности кода"""
        link = Link(
            short_code="taken",
            original_url="https://example.com"
        )
        db_session.add(link)
        await db_session.commit()
        
        available = await LinkService.is_code_available("taken", db_session)
        assert available is False
        
        available = await LinkService.is_code_available("free", db_session)
        assert available is True
    
    @pytest.mark.asyncio
    async def test_create_link_success(self, db_session, sample_link_data):
        """Тест успешного создания ссылки"""
        link = await LinkService.create_link(
            LinkCreate(**sample_link_data),
            db_session,
            user=None
        )
        
        assert link is not None
        assert link.short_code is not None
        assert len(link.short_code) == 6
        assert link.original_url == sample_link_data["original_url"]
        assert link.clicks == 0
        assert link.user_id is None
    
    @pytest.mark.asyncio
    async def test_create_link_with_custom_alias(self, db_session, sample_custom_link_data):
        """Тест создания ссылки с кастомным алиасом"""
        link = await LinkService.create_link(
            LinkCreate(**sample_custom_link_data),
            db_session,
            user=None
        )
        
        assert link is not None
        assert link.short_code == "mycustomlink"
        assert link.custom_alias == "mycustomlink"
        assert link.expires_at is not None
    
    @pytest.mark.asyncio
    async def test_create_link_duplicate_custom_alias(self, db_session, sample_custom_link_data):
        """Тест создания ссылки с уже существующим алиасом"""
        await LinkService.create_link(
            LinkCreate(**sample_custom_link_data),
            db_session,
            user=None
        )
        
        with pytest.raises(ValueError, match="already in use"):
            await LinkService.create_link(
                LinkCreate(**sample_custom_link_data),
                db_session,
                user=None
            )
    
    @pytest.mark.asyncio
    async def test_get_link_by_code(self, db_session, sample_link_data):
        """Тест получения ссылки по коду"""
        created = await LinkService.create_link(
            LinkCreate(**sample_link_data),
            db_session,
            user=None
        )
        
        link = await LinkService.get_link_by_code(created.short_code, db_session)
        
        assert link is not None
        assert link.id == created.id
        assert link.original_url == sample_link_data["original_url"]
    
    @pytest.mark.asyncio
    async def test_get_link_by_code_not_found(self, db_session):
        """Тест получения несуществующей ссылки"""
        link = await LinkService.get_link_by_code("nonexistent", db_session)
        assert link is None
    
    @pytest.mark.asyncio
    async def test_get_link_by_code_with_clicks_increment(self, db_session, sample_link_data):
        """Тест получения ссылки с увеличением счетчика кликов"""
        created = await LinkService.create_link(
            LinkCreate(**sample_link_data),
            db_session,
            user=None
        )
        
        assert created.clicks == 0
        
        link = await LinkService.get_link_by_code(
            created.short_code, 
            db_session, 
            increment_clicks=True
        )
        
        assert link is not None
        assert link.clicks == 1
        assert link.last_accessed is not None
    
    @pytest.mark.asyncio
    async def test_update_link(self, db_session, sample_link_data):
        """Тест обновления ссылки"""
        user = User(
            username="owner",
            email="owner@test.com",
            hashed_password="hash"
        )
        db_session.add(user)
        await db_session.commit()
        
        created = await LinkService.create_link(
            LinkCreate(**sample_link_data),
            db_session,
            user=user
        )
        
        new_url = "https://example.com/new/url"
        updated = await LinkService.update_link(
            created.short_code,
            LinkUpdate(original_url=new_url),
            db_session,
            user
        )
        
        assert updated is not None
        assert updated.original_url == new_url
    
    @pytest.mark.asyncio
    async def test_update_link_not_owner(self, db_session, sample_link_data):
        """Тест обновления ссылки не владельцем"""
        owner = User(
            username="owner",
            email="owner@test.com",
            hashed_password="hash"
        )
        db_session.add(owner)
        
        other = User(
            username="other",
            email="other@test.com",
            hashed_password="hash"
        )
        db_session.add(other)
        await db_session.commit()
        
        created = await LinkService.create_link(
            LinkCreate(**sample_link_data),
            db_session,
            user=owner
        )
        
        new_url = "https://example.com/new/url"
        updated = await LinkService.update_link(
            created.short_code,
            LinkUpdate(original_url=new_url),
            db_session,
            other
        )
        
        assert updated is None
    
    @pytest.mark.asyncio
    async def test_delete_link(self, db_session, sample_link_data):
        """Тест удаления ссылки"""
        user = User(
            username="owner",
            email="owner@test.com",
            hashed_password="hash"
        )
        db_session.add(user)
        await db_session.commit()
        
        created = await LinkService.create_link(
            LinkCreate(**sample_link_data),
            db_session,
            user=user
        )
        
        deleted = await LinkService.delete_link(
            created.short_code,
            db_session,
            user
        )
        
        assert deleted is True
        
        link = await LinkService.get_link_by_code(created.short_code, db_session)
        assert link is None
    
    @pytest.mark.asyncio
    async def test_get_link_stats(self, db_session, sample_link_data):
        """Тест получения статистики ссылки"""
        created = await LinkService.create_link(
            LinkCreate(**sample_link_data),
            db_session,
            user=None
        )
        
        stats = await LinkService.get_link_stats(created.short_code, db_session)
        
        assert stats is not None
        assert stats.id == created.id
        assert stats.clicks == 0
    
    @pytest.mark.asyncio
    async def test_search_by_original_url(self, db_session):
        """Тест поиска по оригинальному URL"""
        await LinkService.create_link(
            LinkCreate(original_url="https://example.com/first"),
            db_session,
            user=None
        )
        await LinkService.create_link(
            LinkCreate(original_url="https://example.com/second"),
            db_session,
            user=None
        )
        await LinkService.create_link(
            LinkCreate(original_url="https://other.com/third"),
            db_session,
            user=None
        )
        
        results = await LinkService.search_by_original_url(
            "https://example.com",
            db_session
        )
        
        assert len(results) == 2
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_links(self, db_session):
        """Тест очистки истекших ссылок"""
        expired_link = Link(
            short_code="expired",
            original_url="https://example.com",
            expires_at=datetime.utcnow() - timedelta(days=1),
            is_active=True
        )
        db_session.add(expired_link)
        
        active_link = Link(
            short_code="active",
            original_url="https://example.com",
            expires_at=datetime.utcnow() + timedelta(days=1),
            is_active=True
        )
        db_session.add(active_link)
        
        await db_session.commit()
        
        await LinkService.cleanup_expired_links(db_session)
        
        expired = await LinkService.get_link_by_code("expired", db_session)
        active = await LinkService.get_link_by_code("active", db_session)
        
        assert expired is None
        assert active is not None