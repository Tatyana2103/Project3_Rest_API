# tests/unit/test_auth_utils.py
import pytest
from datetime import datetime, timedelta
from jose import jwt
from unittest.mock import AsyncMock, patch

from app.auth.utils import (
    verify_password,
    get_password_hash,
    create_access_token
)
from app.config import get_settings


class TestAuthUtils:
    
    def test_password_hashing(self):
        """Тест хеширования и верификации пароля"""
        password = "TestPassword123!"
        
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong", hashed) is False
    
    def test_password_hash_is_different_each_time(self):
        """Тест, что хеши пароля разные при каждом вызове"""
        password = "TestPassword123!"
        
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
    
    def test_create_access_token(self):
        """Тест создания JWT токена"""
        data = {"sub": "testuser"}
        
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        
        settings = get_settings()
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        assert decoded["sub"] == "testuser"
        assert "exp" in decoded
    
    def test_access_token_expiration(self):
        """Тест срока действия токена"""
        data = {"sub": "testuser"}
        
        token = create_access_token(data)
        
        settings = get_settings()
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        exp_time = datetime.fromtimestamp(decoded["exp"])
        expected_time = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        diff = abs((exp_time - expected_time).total_seconds())
        assert diff < 2
    
    def test_access_token_with_custom_data(self):
        """Тест создания токена с дополнительными данными"""
        data = {
            "sub": "testuser",
            "email": "test@example.com",
            "role": "user"
        }
        
        token = create_access_token(data)
        
        settings = get_settings()
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        assert decoded["sub"] == "testuser"
        assert decoded["email"] == "test@example.com"
        assert decoded["role"] == "user"
    
    def test_verify_password_with_empty_string(self):
        """Тест верификации пустого пароля"""
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True
        assert verify_password("something", hashed) is False