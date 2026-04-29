from typing import Annotated

from fastapi import Header

from app.exceptions import APIException


async def require_api_version(
    x_api_version: Annotated[str | None, Header()] = None,
) -> None:
    if x_api_version != "1":
        raise APIException("API version header required", 400)
