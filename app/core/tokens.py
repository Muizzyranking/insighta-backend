import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import APIException
from app.models import RefreshToken, User


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def make_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as e:
        raise APIException("Access token has expired", 401) from e
    except jwt.InvalidTokenError as e:
        raise APIException("Invalid access token", 401) from e


async def make_refresh_token(user: User, db: AsyncSession) -> str:
    raw = secrets.token_urlsafe(48)
    db_token = RefreshToken(
        token_hash=hash_token(raw),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc)
        + timedelta(minutes=settings.refresh_token_expire_minutes),
    )
    db.add(db_token)
    await db.commit()
    return raw


async def issue_token_pair(user: User, db: AsyncSession) -> dict:
    return {
        "status": "success",
        "access_token": make_access_token(user),
        "refresh_token": await make_refresh_token(user, db),
    }
