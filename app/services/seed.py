from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def seed_test_users(db: AsyncSession):
    """Creates persistent test users — only runs outside production."""
    test_users = [
        {
            "github_id": "test-analyst-001",
            "username": "test_analyst",
            "email": "analyst@test.com",
            "role": "analyst",
        },
        {
            "github_id": "test-admin-001",
            "username": "test_admin",
            "email": "admin@test.com",
            "role": "admin",
        },
    ]
    for u in test_users:
        result = await db.execute(select(User).where(User.github_id == u["github_id"]))
        if not result.scalar_one_or_none():
            db.add(User(**u, is_active=True))
    await db.commit()
