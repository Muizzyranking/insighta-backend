from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class UserOut(BaseModel):
    id: str
    github_id: str
    username: str
    email: str | None
    avatar_url: str | None
    role: str
    is_active: bool
    last_login_at: str | None
    created_at: str

    @field_validator("last_login_at", "created_at", mode="before")
    @classmethod
    def format_datetime(cls, v: Any) -> str | None:
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%dT%H:%M:%SZ")
        return v

    @classmethod
    def from_orm(cls, obj: Any) -> "UserOut":
        return cls(
            id=obj.id,
            github_id=obj.github_id,
            username=obj.username,
            email=obj.email,
            avatar_url=obj.avatar_url,
            role=obj.role,
            is_active=obj.is_active,
            last_login_at=obj.last_login_at,
            created_at=obj.created_at,
        )
