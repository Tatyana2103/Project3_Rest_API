# tests/functional/test_auth.py
import pytest


class TestAuthAPI:
    
    @pytest.mark.asyncio
    async def test_register_success(self, client, sample_user_data):
        """Тест успешной регистрации"""
        response = await client.post("/auth/register", json=sample_user_data)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == sample_user_data["username"]
        assert data["email"] == sample_user_data["email"]
        assert "id" in data
        assert "created_at" in data
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client, sample_user_data):
        """Тест регистрации с существующим username"""
        # Первая регистрация
        await client.post("/auth/register", json=sample_user_data)
        
        # Вторая с тем же username
        response = await client.post("/auth/register", json=sample_user_data)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client, sample_user_data):
        """Тест регистрации с существующим email"""
        # Первая регистрация
        await client.post("/auth/register", json=sample_user_data)
        
        # Вторая с тем же email
        duplicate_data = sample_user_data.copy()
        duplicate_data["username"] = "different_user"
        response = await client.post("/auth/register", json=duplicate_data)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_register_missing_fields(self, client):
        """Тест регистрации с отсутствующими полями"""
        # Отсутствует email
        response = await client.post("/auth/register", json={
            "username": "test",
            "password": "pass"
        })
        assert response.status_code == 422
        
        # Отсутствует username
        response = await client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "pass"
        })
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client):
        """Тест регистрации с невалидным email"""
        response = await client.post("/auth/register", json={
            "username": "testuser",
            "email": "invalid-email",
            "password": "password123"
        })
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_invalid_username(self, client):
        """Тест регистрации с невалидным username (спецсимволы)"""
        response = await client.post("/auth/register", json={
            "username": "test@user!",
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_short_password(self, client):
        """Тест регистрации с коротким паролем"""
        response = await client.post("/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "123"
        })
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_login_success(self, client, sample_user_data):
        """Тест успешного входа"""
        # Регистрация
        await client.post("/auth/register", json=sample_user_data)
        
        # Вход
        response = await client.post("/auth/token", json={
            "username": sample_user_data["username"],
            "password": sample_user_data["password"]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0
    
    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, sample_user_data):
        """Тест входа с неверным паролем"""
        # Регистрация
        await client.post("/auth/register", json=sample_user_data)
        
        # Вход с неверным паролем
        response = await client.post("/auth/token", json={
            "username": sample_user_data["username"],
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "Incorrect" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        """Тест входа несуществующего пользователя"""
        response = await client.post("/auth/token", json={
            "username": "nonexistent",
            "password": "password"
        })
        
        assert response.status_code == 401