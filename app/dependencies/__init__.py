from typing import Annotated

from fastapi import Depends

from app.dependencies.auth import DBSession, get_current_user, require_admin
from app.models import User

CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]

__all__ = [
    "CurrentUser",
    "AdminUser",
    "DBSession",
]
