from fastapi import APIRouter

from app.config import settings
from app.core.tokens import issue_token_pair
from app.dependencies import DBSession
from app.exceptions import APIException
from app.models import User

router = APIRouter(prefix="/test", tags=["test"])


@router.get("/test-users")
async def test_users(db: DBSession) -> dict:
    """Dev-only endpoint for manual testing — remove before production."""
    if settings.app_env == "production":
        raise APIException("Not available in production", 403)

    analyst = User(
        id=9001,
        github_id="test-github-analyst",
        username="test_analyst",
        email="analyst@test.com",
        avatar_url="https://avatars.githubusercontent.com/u/9001",
        role="analyst",
        is_active=True,
    )

    admin = User(
        id=9002,
        github_id="test-github-admin",
        username="test_admin",
        email="admin@test.com",
        avatar_url="https://avatars.githubusercontent.com/u/9002",
        role="admin",
        is_active=True,
    )

    analyst_tokens = await issue_token_pair(analyst, db)
    admin_tokens = await issue_token_pair(admin, db)

    return {
        "analyst": {
            "user": {
                "id": analyst.id,
                "username": analyst.username,
                "email": analyst.email,
                "role": analyst.role,
            },
            **analyst_tokens,
        },
        "admin": {
            "user": {
                "id": admin.id,
                "username": admin.username,
                "email": admin.email,
                "role": admin.role,
            },
            **admin_tokens,
        },
    }
