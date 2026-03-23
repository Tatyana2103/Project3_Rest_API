# tests/conftest.py
"""
Фикстуры для тестирования API сервиса сокращения ссылок
"""

import pytest
import pytest_asyncio
from typing import AsyncGenerator, Optional
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock
from datetime import datetime
import uuid
import json
import fnmatch

from app.main import app
from app.core.database import get_db
from app.core.redis_client import get_redis


# ==================== MOCK ДЛЯ БАЗЫ ДАННЫХ ====================

class MockAsyncSession:
    """Mock для асинхронной сессии SQLAlchemy"""
    
    def __init__(self):
        self.added = []
        self.deleted = []
        self.committed = False
        self.rolled_back = False
        self.flushed = False
        self.closed = False
        self._data_store = {
            "users": {},
            "links": {}
        }
    
    @property
    def data_store(self):
        return self._data_store
    
    async def commit(self):
        """Mock для commit"""
        try:
            for obj in self.added:
                # Генерируем ID если нет
                if hasattr(obj, 'id') and (obj.id is None or obj.id == ""):
                    obj.id = str(uuid.uuid4())
                
                # Устанавливаем created_at
                if hasattr(obj, 'created_at') and obj.created_at is None:
                    obj.created_at = datetime.utcnow()
                
                # Сохраняем в хранилище
                if hasattr(obj, '__tablename__'):
                    table_name = obj.__tablename__
                    if table_name not in self._data_store:
                        self._data_store[table_name] = {}
                    if hasattr(obj, 'id') and obj.id:
                        self._data_store[table_name][obj.id] = obj
            
            self.committed = True
            self.added.clear()
        except Exception as e:
            print(f"Error in commit mock: {e}")
            raise
    
    async def rollback(self):
        """Mock для rollback"""
        self.rolled_back = True
        self.added.clear()
        self.deleted.clear()
    
    async def flush(self):
        """Mock для flush"""
        self.flushed = True
    
    async def refresh(self, obj, attribute_names=None):
        """Mock для refresh - обновляет объект из хранилища"""
        try:
            if hasattr(obj, '__tablename__') and hasattr(obj, 'id') and obj.id:
                table_name = obj.__tablename__
                if table_name in self._data_store and obj.id in self._data_store[table_name]:
                    stored_obj = self._data_store[table_name][obj.id]
                    if hasattr(stored_obj, '__dict__'):
                        for key, value in stored_obj.__dict__.items():
                            if not key.startswith('_'):
                                setattr(obj, key, value)
        except Exception as e:
            print(f"Error in refresh mock: {e}")
    
    async def execute(self, query, params=None):
        """Mock для выполнения запросов"""
        try:
            from sqlalchemy import select
            from app.models import User, Link
            
            query_str = str(query).lower()
            results = []
            
            # Определяем таблицу и фильтруем
            if "users" in query_str:
                table_data = self._data_store.get("users", {})
                results = list(table_data.values())
                
                # Фильтрация по username для поиска пользователя
                if "username" in query_str and "where" in query_str:
                    # Простой поиск по username
                    filtered = []
                    for user in results:
                        if hasattr(user, 'username'):
                            # Проверяем, есть ли username в строке запроса
                            if user.username in query_str:
                                filtered.append(user)
                    if filtered:
                        results = filtered
                        
            elif "links" in query_str:
                table_data = self._data_store.get("links", {})
                results = list(table_data.values())
                
                # Фильтрация по short_code
                if "short_code" in query_str and "where" in query_str:
                    filtered = []
                    for link in results:
                        if hasattr(link, 'short_code'):
                            if link.short_code in query_str:
                                filtered.append(link)
                    if filtered:
                        results = filtered
                
                # Фильтрация по user_id
                if "user_id" in query_str and "where" in query_str:
                    filtered = []
                    for link in results:
                        if hasattr(link, 'user_id') and link.user_id:
                            if link.user_id in query_str:
                                filtered.append(link)
                    if filtered:
                        results = filtered
            
            class MockResult:
                def __init__(self, data):
                    self._data = data
                
                def scalar_one_or_none(self):
                    return self._data[0] if self._data else None
                
                def scalars(self):
                    return self
                
                def all(self):
                    return self._data
                
                def first(self):
                    return self._data[0] if self._data else None
                
                def __iter__(self):
                    return iter(self._data)
            
            return MockResult(results)
            
        except Exception as e:
            print(f"Error in execute mock: {e}")
            class EmptyResult:
                def scalar_one_or_none(self): return None
                def scalars(self): return self
                def all(self): return []
                def first(self): return None
                def __iter__(self): return iter([])
            return EmptyResult()
    
    def add(self, obj):
        """Mock для add"""
        try:
            self.added.append(obj)
        except Exception as e:
            print(f"Error in add mock: {e}")
    
    def delete(self, obj):
        """Mock для delete"""
        try:
            self.deleted.append(obj)
            if hasattr(obj, '__tablename__') and hasattr(obj, 'id') and obj.id:
                table_name = obj.__tablename__
                if table_name in self._data_store and obj.id in self._data_store[table_name]:
                    del self._data_store[table_name][obj.id]
        except Exception as e:
            print(f"Error in delete mock: {e}")
    
    async def close(self):
        """Mock для close"""
        self.closed = True
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    def clear(self):
        """Очистка всех данных"""
        self.added.clear()
        self.deleted.clear()
        self._data_store = {
            "users": {},
            "links": {}
        }
        self.committed = False
        self.rolled_back = False
        self.flushed = False


# ==================== MOCK ДЛЯ REDIS ====================

class MockRedisClient:
    """Mock для Redis клиента"""
    
    def __init__(self):
        self._data = {}
        self.client = MagicMock()
    
    async def init(self):
        pass
    
    async def close(self):
        self._data.clear()
    
    async def get(self, key: str):
        value = self._data.get(key)
        if value and isinstance(value, str):
            try:
                return json.loads(value)
            except:
                return value
        return value
    
    async def set(self, key: str, value, ttl: int = None):
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        self._data[key] = value
    
    async def delete(self, key: str):
        self._data.pop(key, None)
    
    async def delete_pattern(self, pattern: str):
        keys_to_delete = [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]
        for key in keys_to_delete:
            self._data.pop(key, None)
    
    async def exists(self, key: str) -> bool:
        return key in self._data


# ==================== ФИКСТУРЫ ====================

@pytest_asyncio.fixture
async def mock_db_session():
    """Mock для сессии базы данных"""
    session = MockAsyncSession()
    session.clear()
    return session


@pytest_asyncio.fixture
async def test_redis():
    """Фикстура Redis для тестов"""
    mock_redis = MockRedisClient()
    await mock_redis.init()
    return mock_redis


@pytest_asyncio.fixture
async def client(mock_db_session, test_redis):
    """
    Фикстура HTTP клиента для тестирования API
    """
    
    # Переопределение зависимостей
    async def override_get_db():
        yield mock_db_session
    
    async def override_get_redis():
        yield test_redis
    
    # Сохраняем оригинальные зависимости
    original_get_db = app.dependency_overrides.get(get_db)
    original_get_redis = app.dependency_overrides.get(get_redis)
    
    # Устанавливаем моки
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    
    # Создаем клиент с ASGITransport
    transport = ASGITransport(app=app)
    
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=False,
        timeout=30.0
    ) as client:
        yield client
    
    # Восстанавливаем оригинальные зависимости
    if original_get_db:
        app.dependency_overrides[get_db] = original_get_db
    else:
        app.dependency_overrides.pop(get_db, None)
    
    if original_get_redis:
        app.dependency_overrides[get_redis] = original_get_redis
    else:
        app.dependency_overrides.pop(get_redis, None)


# ==================== ФИКСТУРЫ ДЛЯ ТЕСТОВЫХ ДАННЫХ ====================

@pytest.fixture
def sample_user_data():
    """Пример данных для регистрации пользователя"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!"
    }


@pytest.fixture
def sample_user_data_2():
    """Второй пример данных пользователя"""
    return {
        "username": "testuser2",
        "email": "test2@example.com",
        "password": "TestPassword456!"
    }


@pytest.fixture
def sample_invalid_user_data():
    """Пример невалидных данных пользователя"""
    return {
        "username": "testuser",
        "email": "invalid-email",
        "password": "pass"
    }


@pytest.fixture
def sample_link_data():
    """Пример данных для создания ссылки"""
    return {
        "original_url": "https://example.com/very/long/url/that/needs/shortening"
    }


@pytest.fixture
def sample_link_data_2():
    """Второй пример данных для создания ссылки"""
    return {
        "original_url": "https://example.com/another/very/long/url"
    }


@pytest.fixture
def sample_custom_link_data():
    """Пример данных для создания кастомной ссылки"""
    from datetime import datetime, timedelta
    
    future_date = datetime.utcnow() + timedelta(days=30)
    return {
        "original_url": "https://example.com/custom/url",
        "custom_alias": "mycustomlink",
        "expires_at": future_date.isoformat()
    }


@pytest.fixture
def sample_invalid_link_data():
    """Пример невалидных данных ссылки"""
    return {
        "original_url": "not-a-valid-url"
    }


# ==================== ФИКСТУРЫ ДЛЯ АВТОРИЗОВАННЫХ ЗАПРОСОВ ====================

@pytest_asyncio.fixture
async def auth_token(client, sample_user_data):
    """Фикстура токена авторизации"""
    # Регистрация
    reg_response = await client.post("/auth/register", json=sample_user_data)
    if reg_response.status_code != 200:
        return None
    
    # Получение токена
    response = await client.post("/auth/token", json={
        "username": sample_user_data["username"],
        "password": sample_user_data["password"]
    })
    
    if response.status_code == 200:
        return response.json()["access_token"]
    return None


@pytest_asyncio.fixture
async def authenticated_client(client, auth_token):
    """Фикстура авторизованного клиента"""
    if not auth_token:
        yield client
        return
    
    # Создаем клиент с заголовком авторизации
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        follow_redirects=False,
        timeout=30.0,
        headers={"Authorization": f"Bearer {auth_token}"}
    ) as auth_client:
        yield auth_client


@pytest_asyncio.fixture
async def registered_user(client, sample_user_data):
    """Фикстура зарегистрированного пользователя"""
    response = await client.post("/auth/register", json=sample_user_data)
    if response.status_code == 200:
        return response.json()
    return None


@pytest_asyncio.fixture
async def test_link(authenticated_client, sample_link_data):
    """Фикстура созданной ссылки"""
    if not authenticated_client:
        return None
    response = await authenticated_client.post("/links/shorten", json=sample_link_data)
    if response.status_code == 200:
        return response.json()
    return None


# ==================== АВТОМАТИЧЕСКАЯ ОЧИСТКА ====================

@pytest.fixture(autouse=True)
async def auto_cleanup(mock_db_session):
    """
    Автоматическая очистка базы данных после каждого теста
    """
    yield
    mock_db_session.clear()


# ==================== НАСТРОЙКА ASYNCIO ====================

@pytest.fixture
def anyio_backend():
    """Настройка asyncio бэкенда для pytest-asyncio"""
    return "asyncio"
