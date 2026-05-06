from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User


async def upsert_user(github_user: dict, db: AsyncSession) -> User:
    github_id = str(github_user["id"])
    now = datetime.now(timezone.utc)

    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()
    username = github_user.get("login", "")
    is_admin = (
        settings.admin_username and username.lower() == settings.admin_username.lower()
    )

    if user:
        user.username = github_user.get("login", user.username)
        user.email = github_user.get("email") or user.email
        user.avatar_url = github_user.get("avatar_url") or user.avatar_url
        user.last_login_at = now
        if is_admin and user.role != "admin":
            user.role = "admin"
    else:
        user = User(
            github_id=github_id,
            username=github_user.get("login", ""),
            email=github_user.get("email"),
            avatar_url=github_user.get("avatar_url"),
            last_login_at=now,
            role="admin" if is_admin else "analyst",
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)
    return user
