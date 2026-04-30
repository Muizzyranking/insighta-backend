from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tokens import decode_access_token
from app.database import get_db
from app.exceptions import APIException
from app.models import User

bearer = HTTPBearer(auto_error=False)

BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    request: Request,
    credentials: BearerCredentials,
    db: DBSession,
) -> User:
    token: str | None = None

    if credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise APIException("Authentication required", 401)

    payload = decode_access_token(token)
    user_id: str | None = payload.get("sub")

    if not user_id:
        raise APIException("Invalid access token", 401)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise APIException("User not found", 401)

    if not user.is_active:
        raise APIException("Account is disabled", 403)

    return user


async def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != "admin":
        raise APIException("Admin access required", 403)
    return user
