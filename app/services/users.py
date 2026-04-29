from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def upsert_user(github_user: dict, db: AsyncSession) -> User:
    github_id = str(github_user["id"])
    now = datetime.now(timezone.utc)

    result = await db.execute(select(User).where(User.github_id == github_id))
    user = result.scalar_one_or_none()

    if user:
        user.username = github_user.get("login", user.username)
        user.email = github_user.get("email") or user.email
        user.avatar_url = github_user.get("avatar_url") or user.avatar_url
        user.last_login_at = now
    else:
        user = User(
            github_id=github_id,
            username=github_user.get("login", ""),
            email=github_user.get("email"),
            avatar_url=github_user.get("avatar_url"),
            last_login_at=now,
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)
    return user
