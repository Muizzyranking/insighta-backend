from fastapi import APIRouter, Request
from sqlalchemy import select

from app.dependencies import AdminUser, DBSession
from app.exceptions import APIException
from app.middleware.rate_limit import limiter
from app.models import User
from app.schemas.users import UserOut

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.patch("/users/{user_id}/promote")
@limiter.limit("60/minute")
async def promote_user(
    request: Request,
    user_id: str,
    user: AdminUser,
    db: DBSession,
) -> UserOut:
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()

    if not target:
        raise APIException("User not found", 404)

    if target.role == "admin":
        raise APIException("User is already an admin", 409)

    target.role = "admin"
    await db.commit()
    await db.refresh(target)

    return UserOut.from_orm(target)
