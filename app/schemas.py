from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    username: str
    email: str


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: str
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class LinkBase(BaseModel):
    original_url: HttpUrl


class LinkCreate(LinkBase):
    custom_alias: Optional[str] = Field(None, min_length=3, max_length=50)
    expires_at: Optional[datetime] = None


class LinkUpdate(BaseModel):
    original_url: HttpUrl


class LinkResponse(BaseModel):
    id: str
    short_code: str
    short_url: str
    original_url: str
    custom_alias: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    clicks: int
    last_accessed: Optional[datetime]
    user_id: Optional[str]
    
    class Config:
        from_attributes = True


class LinkStats(LinkResponse):
    pass  


class LinkSearch(BaseModel):
    original_url: str
    short_code: str
    short_url: str
    created_at: datetime
    clicks: int