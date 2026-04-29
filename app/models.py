import secrets
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import BaseModel


def new_token() -> str:
    return secrets.token_urlsafe(48)


class Profile(BaseModel):
    __tablename__ = "profiles"

    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    gender: Mapped[str] = mapped_column(String, nullable=False)
    gender_probability: Mapped[float] = mapped_column(Float, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    age_group: Mapped[str] = mapped_column(String, nullable=False)
    country_id: Mapped[str] = mapped_column(String, nullable=False)
    country_name: Mapped[str] = mapped_column(String, nullable=False)
    country_probability: Mapped[float] = mapped_column(Float, nullable=False)


class User(BaseModel):
    __tablename__ = "users"

    github_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default="analyst")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(BaseModel):
    __tablename__ = "refresh_tokens"

    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
