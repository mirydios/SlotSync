from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    timezone: Optional[str] = "America/Sao_Paulo"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    timezone: Optional[str] = None


class UserOut(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    username: Optional[str]
    bio: Optional[str] = None
    timezone: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
