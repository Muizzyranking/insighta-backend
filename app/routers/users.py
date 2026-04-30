from fastapi import APIRouter

from app.dependencies import CurrentUser
from app.schemas.users import UserOut

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me")
async def get_me(current_user: CurrentUser) -> UserOut:
    return UserOut.from_orm(current_user)
