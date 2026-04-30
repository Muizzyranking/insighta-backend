from fastapi import APIRouter
from sqlalchemy import select

from app.config import settings
from app.core.tokens import issue_token_pair
from app.dependencies import DBSession
from app.exceptions import APIException
from app.models import User
from app.schemas.users import UserOut

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/test-users")
async def test_users(db: DBSession) -> dict:
    if settings.app_env == "production":
        raise APIException("Not available in production", 403)

    results = {}
    for github_id, label in [
        ("test-analyst-001", "analyst"),
        ("test-admin-001", "admin"),
    ]:
        result = await db.execute(select(User).where(User.github_id == github_id))
        user = result.scalar_one_or_none()
        if not user:
            raise APIException(
                f"Test user '{label}' not seeded — restart the server", 500
            )
        tokens = await issue_token_pair(user, db)
        results[label] = {"user": UserOut.from_orm(user), **tokens}

    return results
