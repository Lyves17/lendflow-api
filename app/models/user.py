import enum
from datetime import datetime, timezone
from typing import Optional
from beanie import Document
from pydantic import Field


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    AGENT = "agent"
    CLIENT = "client"


class User(Document):
    email: str
    phone: Optional[str] = None
    hashed_password: str
    full_name: str
    role: UserRole = UserRole.CLIENT
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "users"
