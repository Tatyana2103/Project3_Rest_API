import pytest
from datetime import datetime, timedelta


class TestRedirectAPI:
    
    @pytest.mark.asyncio
    async def test_redirect_success(self, client, sample_link_data):
        """Тест успешного редиректа"""
        # Создаем ссылку
        create_response = await client.post("/links/shorten", json=sample_link_data)
        assert create_response.status_code == 200
        short_code = create_response.json()["short_code"]
        
        # Переходим по ссылке
        response = await client.get(f"/{short_code}", follow_redirects=False)
        
        assert response.status_code == 307
        assert "location" in response.headers
        assert response.headers["location"] == sample_link_data["original_url"]
    
    @pytest.mark.asyncio
    async def test_redirect_increments_clicks(self, client, sample_link_data):
        """Тест, что редирект увеличивает счетчик кликов"""
        # Создаем ссылку
        create_response = await client.post("/links/shorten", json=sample_link_data)
        short_code = create_response.json()["short_code"]
        
        # Проверяем начальное значение
        stats_before = await client.get(f"/links/{short_code}/stats")
        assert stats_before.json()["clicks"] == 0
        
        # Переходим по ссылке
        await client.get(f"/{short_code}", follow_redirects=False)
        
        # Проверяем, что счетчик увеличился
        stats_after = await client.get(f"/links/{short_code}/stats")
        assert stats_after.json()["clicks"] == 1
    
    @pytest.mark.asyncio
    async def test_redirect_nonexistent_link(self, client):
        """Тест редиректа на несуществующую ссылку"""
        response = await client.get("/nonexistent123", follow_redirects=False)
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_redirect_expired_link(self, client, sample_custom_link_data):
        """Тест редиректа на истекшую ссылку"""
        # Создаем ссылку с истекшим сроком
        expired_data = sample_custom_link_data.copy()
        expired_data["expires_at"] = (datetime.utcnow() - timedelta(days=1)).isoformat()
        
        create_response = await client.post("/links/shorten", json=expired_data)
        assert create_response.status_code == 200
        short_code = create_response.json()["short_code"]
        
        response = await client.get(f"/{short_code}", follow_redirects=False)
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_redirect_valid_expired_link(self, client, sample_custom_link_data):
        """Тест редиректа на ссылку, срок которой не истек"""
        # Создаем ссылку с будущим сроком
        future_data = sample_custom_link_data.copy()
        future_data["expires_at"] = (datetime.utcnow() + timedelta(days=30)).isoformat()
        
        create_response = await client.post("/links/shorten", json=future_data)
        assert create_response.status_code == 200
        short_code = create_response.json()["short_code"]
        
        # Переходим по ссылке
        response = await client.get(f"/{short_code}", follow_redirects=False)
        
        assert response.status_code == 307
        assert response.headers["location"] == future_data["original_url"]
    
    @pytest.mark.asyncio
    async def test_redirect_with_custom_alias(self, client, sample_custom_link_data):
        """Тест редиректа по кастомному алиасу"""
        # Создаем ссылку с кастомным алиасом
        create_response = await client.post("/links/shorten", json=sample_custom_link_data)
        assert create_response.status_code == 200
        short_code = create_response.json()["short_code"]
        
        # Переходим по алиасу
        response = await client.get(f"/{short_code}", follow_redirects=False)
        
        assert response.status_code == 307
        assert response.headers["location"] == sample_custom_link_data["original_url"]