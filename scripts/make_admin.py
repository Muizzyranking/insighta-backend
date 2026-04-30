import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import User


async def promote(username: str) -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            print(f"No user found with GitHub username: {username}")
            sys.exit(1)

        if user.role == "admin":
            print(f"@{username} is already an admin.")
            return

        user.role = "admin"
        await db.commit()
        print(f"✓ @{username} has been promoted to admin.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/make_admin.py <github_username>")
        sys.exit(1)

    asyncio.run(promote(sys.argv[1]))
