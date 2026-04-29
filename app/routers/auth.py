import secrets
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.config import settings
from app.core.tokens import hash_token, issue_token_pair
from app.dependencies import CurrentUser, DBSession
from app.exceptions import APIException
from app.models import RefreshToken, User
from app.schemas.auth import (
    GithubCallbackQuery,
    GitHubLoginQuery,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.users import UserOut
from app.services.github import exchange_code_for_user
from app.services.users import upsert_user

router = APIRouter(prefix="/auth", tags=["auth"])

_pkce_store: dict[str, str] = {}


@router.get("/github")
async def github_login(
    request: Request,
    query_params: Annotated[GitHubLoginQuery, Query()],
) -> RedirectResponse:

    state = query_params.state or secrets.token_urlsafe(16)

    if query_params.code_verifier:
        _pkce_store[state] = query_params.code_verifier

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "read:user user:email",
        "state": state,
    }
    if query_params.code_challenge:
        params["code_challenge"] = query_params.code_challenge
        params["code_challenge_method"] = query_params.code_challenge_method or "S256"

    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{query}")


@router.get("/github/callback")
async def github_callback(
    request: Request,
    query: Annotated[GithubCallbackQuery, Query()],
    db: DBSession,
) -> TokenResponse:
    code_verifier = _pkce_store.pop(query.state, None)
    github_user = await exchange_code_for_user(query.code, code_verifier)
    user = await upsert_user(github_user, db)
    tokens = await issue_token_pair(user, db)
    return TokenResponse(**tokens)


@router.post("/refresh")
async def refresh_tokens(
    request: Request,
    body: RefreshRequest,
    db: DBSession,
) -> TokenResponse:
    token_hash = hash_token(body.refresh_token)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()

    if not stored or stored.revoked:
        raise APIException("Invalid refresh token", 401)

    from datetime import datetime, timezone

    if stored.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise APIException("Refresh token has expired", 401)

    stored.revoked = True
    await db.commit()

    result = await db.execute(select(User).where(User.id == stored.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise APIException("User not found", 401)
    if not user.is_active:
        raise APIException("Account is disabled", 403)

    tokens = await issue_token_pair(user, db)
    return TokenResponse(**tokens)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    body: RefreshRequest,
    db: DBSession,
) -> Response:
    token_hash = hash_token(body.refresh_token)

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    stored = result.scalar_one_or_none()

    if stored and not stored.revoked:
        stored.revoked = True
        await db.commit()

    return Response(status_code=204)


@router.get("/me")
async def whoami(request: Request, current_user: CurrentUser) -> UserOut:
    return UserOut.from_orm(current_user)
