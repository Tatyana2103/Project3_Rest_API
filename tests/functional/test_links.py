# tests/functional/test_links.py
import pytest
from datetime import datetime, timedelta


class TestLinksAPI:
    
    @pytest.mark.asyncio
    async def test_create_link_anonymous(self, client, sample_link_data):
        """Тест создания ссылки анонимным пользователем"""
        response = await client.post("/links/shorten", json=sample_link_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["original_url"] == sample_link_data["original_url"]
        assert "short_code" in data
        assert "short_url" in data
        assert data["short_url"].endswith(data["short_code"])
        assert data["clicks"] == 0
        assert data["user_id"] is None
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_create_link_authenticated(self, authenticated_client, sample_link_data):
        """Тест создания ссылки авторизованным пользователем"""
        response = await authenticated_client.post("/links/shorten", json=sample_link_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["original_url"] == sample_link_data["original_url"]
        assert data["user_id"] is not None
    
    @pytest.mark.asyncio
    async def test_create_link_with_custom_alias(self, authenticated_client, sample_custom_link_data):
        """Тест создания ссылки с кастомным алиасом"""
        response = await authenticated_client.post("/links/shorten", json=sample_custom_link_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["short_code"] == "mycustomlink"
        assert data["custom_alias"] == "mycustomlink"
        assert data["expires_at"] is not None
    
    @pytest.mark.asyncio
    async def test_create_link_duplicate_alias(self, authenticated_client, sample_custom_link_data):
        """Тест создания ссылки с уже существующим алиасом"""
        # Первая ссылка
        await authenticated_client.post("/links/shorten", json=sample_custom_link_data)
        
        # Вторая с таким же алиасом
        response = await authenticated_client.post("/links/shorten", json=sample_custom_link_data)
        
        assert response.status_code == 400
        assert "already in use" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_link_invalid_url(self, authenticated_client):
        """Тест создания ссылки с невалидным URL"""
        response = await authenticated_client.post("/links/shorten", json={
            "original_url": "not-a-valid-url"
        })
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_link_with_expiration(self, authenticated_client):
        """Тест создания ссылки с временем жизни"""
        expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
        response = await authenticated_client.post("/links/shorten", json={
            "original_url": "https://example.com/temp",
            "expires_at": expires_at
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["expires_at"] is not None
    
    @pytest.mark.asyncio
    async def test_create_link_custom_alias_too_short(self, authenticated_client):
        """Тест создания ссылки с слишком коротким алиасом"""
        response = await authenticated_client.post("/links/shorten", json={
            "original_url": "https://example.com/test",
            "custom_alias": "ab"  # меньше 3 символов
        })
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_create_link_custom_alias_invalid_chars(self, authenticated_client):
        """Тест создания ссылки с недопустимыми символами в алиасе"""
        response = await authenticated_client.post("/links/shorten", json={
            "original_url": "https://example.com/test",
            "custom_alias": "my@alias!"
        })
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_get_link_stats_anonymous(self, client, sample_link_data):
        """Тест получения статистики анонимным пользователем"""
        # Создаем ссылку
        create_response = await client.post("/links/shorten", json=sample_link_data)
        assert create_response.status_code == 200
        short_code = create_response.json()["short_code"]
        
        # Получаем статистику
        response = await client.get(f"/links/{short_code}/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["original_url"] == sample_link_data["original_url"]
        assert data["short_code"] == short_code
        assert data["clicks"] == 0
        assert "created_at" in data
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_link_stats(self, client):
        """Тест получения статистики несуществующей ссылки"""
        response = await client.get("/links/nonexistent/stats")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_link_owner(self, authenticated_client, sample_link_data):
        """Тест обновления ссылки владельцем"""
        # Создаем ссылку
        create_response = await authenticated_client.post("/links/shorten", json=sample_link_data)
        assert create_response.status_code == 200
        short_code = create_response.json()["short_code"]
        
        # Обновляем
        new_url = "https://example.com/updated/url"
        response = await authenticated_client.put(
            f"/links/{short_code}",
            json={"original_url": new_url}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["original_url"] == new_url
        assert data["short_code"] == short_code
    
    @pytest.mark.asyncio
    async def test_update_link_not_owner(self, client, authenticated_client, sample_link_data):
        """Тест обновления ссылки не владельцем"""
        # Создаем ссылку одним пользователем
        create_response = await authenticated_client.post("/links/shorten", json=sample_link_data)
        assert create_response.status_code == 200
        short_code = create_response.json()["short_code"]
        
        # Пытаемся обновить анонимным пользователем
        new_url = "https://example.com/updated/url"
        response = await client.put(
            f"/links/{short_code}",
            json={"original_url": new_url}
        )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_delete_link_owner(self, authenticated_client, sample_link_data):
        """Тест удаления ссылки владельцем"""
        # Создаем ссылку
        create_response = await authenticated_client.post("/links/shorten", json=sample_link_data)
        assert create_response.status_code == 200
        short_code = create_response.json()["short_code"]
        
        # Удаляем
        response = await authenticated_client.delete(f"/links/{short_code}")
        
        assert response.status_code == 204
        assert response.text == ""
        
        # Проверяем, что ссылка удалена
        stats_response = await authenticated_client.get(f"/links/{short_code}/stats")
        assert stats_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_link_not_owner(self, client, authenticated_client, sample_link_data):
        """Тест удаления ссылки не владельцем"""
        # Создаем ссылку авторизованным пользователем
        create_response = await authenticated_client.post("/links/shorten", json=sample_link_data)
        assert create_response.status_code == 200
        short_code = create_response.json()["short_code"]
        
        # Пытаемся удалить анонимным клиентом
        response = await client.delete(f"/links/{short_code}")
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_search_links(self, client):
        """Тест поиска ссылок по оригинальному URL"""
        # Создаем несколько ссылок
        await client.post("/links/shorten", json={"original_url": "https://example.com/first"})
        await client.post("/links/shorten", json={"original_url": "https://example.com/second"})
        await client.post("/links/shorten", json={"original_url": "https://other.com/third"})
        
        # Ищем по example.com
        response = await client.get("/links/search?original_url=https://example.com")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        for item in data:
            assert "example.com" in item["original_url"]
            assert "short_code" in item
            assert "short_url" in item
            assert "clicks" in item
    
    @pytest.mark.asyncio
    async def test_get_user_links(self, authenticated_client):
        """Тест получения всех ссылок пользователя"""
        # Создаем несколько ссылок
        await authenticated_client.post("/links/shorten", json={"original_url": "https://example.com/1"})
        await authenticated_client.post("/links/shorten", json={"original_url": "https://example.com/2"})
        
        # Получаем список
        response = await authenticated_client.get("/links/user/me")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for item in data:
            assert "user_id" in item
            assert item["user_id"] is not None
            assert "short_code" in item
            assert "original_url" in item