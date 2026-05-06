import secrets
import time
from typing import Annotated
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from app.config import settings
from app.core.tokens import hash_token, issue_token_pair
from app.dependencies import CurrentUser, DBSession
from app.exceptions import APIException
from app.middleware.rate_limit import limiter
from app.models import RefreshToken, User
from app.schemas.auth import (
    GithubCallbackQuery,
    GitHubLoginQuery,
    RefreshRequest,
)
from app.schemas.users import UserOut
from app.services.github import exchange_code_for_user
from app.services.users import upsert_user

router = APIRouter(prefix="/auth", tags=["auth"])

_pkce_store: dict[str, str] = {}
_ott_store: dict[str, dict] = {}


def _set_auth_cookies(response: Response, tokens: dict):
    is_prod = settings.app_env == "production"
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=900,
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )


@router.get("/github")
@limiter.limit("10/minute")
async def github_login(
    request: Request,
    query_params: Annotated[GitHubLoginQuery, Query()],
) -> RedirectResponse:

    state = query_params.state or secrets.token_urlsafe(16)

    if query_params.code_verifier or query_params.redirect_uri:
        _pkce_store[state] = {
            "code_verifier": query_params.code_verifier,
            "redirect_uri": query_params.redirect_uri,
        }

    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": settings.github_redirect_uri,
        "scope": "read:user user:email",
        "state": state,
    }
    if query_params.code_challenge:
        params["code_challenge"] = query_params.code_challenge
        params["code_challenge_method"] = query_params.code_challenge_method or "S256"

    return RedirectResponse(
        f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    )


@router.get("/github/callback")
@limiter.limit("10/minute")
async def github_callback(
    request: Request,
    query: Annotated[GithubCallbackQuery, Query()],
    db: DBSession,
) -> RedirectResponse:

    if not query.code:
        raise APIException("Missing code", 400)

    if not query.state:
        raise APIException("Missing state", 400)

    stored = _pkce_store.pop(query.state, {})
    code_verifier = stored.get("code_verifier")
    cli_redirect_uri = stored.get("redirect_uri")

    github_user = await exchange_code_for_user(query.code, code_verifier)
    user = await upsert_user(github_user, db)
    tokens = await issue_token_pair(user, db)

    one_time_token = secrets.token_urlsafe(32)
    _ott_store[one_time_token] = {"tokens": tokens, "expires_at": time.time() + 60}

    if cli_redirect_uri:
        parsed = urlparse(cli_redirect_uri)
        if parsed.hostname not in ("localhost", "127.0.0.1"):
            raise APIException("Invalid CLI redirect URI", 400)

        params = urlencode(
            {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
            }
        )
        return RedirectResponse(f"{cli_redirect_uri}?{params}")

    return RedirectResponse(
        url=f"{settings.frontend_url}/auth/callback?ott={one_time_token}"
    )


@router.post("/session")
@limiter.limit("10/minute")
async def exchange_ott(request: Request, ott: str):
    entry = _ott_store.pop(ott, None)
    if not entry or time.time() > entry["expires_at"]:
        raise APIException("Invalid or expired token", 400)

    response = JSONResponse(content={"status": "success"})
    _set_auth_cookies(response, entry["tokens"])
    return response


@router.post("/refresh")
@limiter.limit("11/minute")
async def refresh_tokens(
    request: Request,
    db: DBSession,
    body: RefreshRequest | None = None,
):

    refresh_token = request.cookies.get("refresh_token") or (
        body and body.refresh_token
    )
    if not refresh_token:
        raise APIException("No refresh token", 401)

    token_hash = hash_token(refresh_token)

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

    response = JSONResponse(
        content={
            "status": "success",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }
    )
    if request.cookies.get("refresh_token"):
        _set_auth_cookies(response, tokens)
    return response


@router.post("/logout")
@limiter.limit("11/minute")
async def logout(request: Request, db: DBSession, body: RefreshRequest | None = None):
    refresh_token = request.cookies.get("refresh_token") or (
        body and body.refresh_token
    )
    if refresh_token:
        token_hash = hash_token(refresh_token)
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored = result.scalar_one_or_none()
        if stored and not stored.revoked:
            stored.revoked = True
            await db.commit()

    response = JSONResponse(content={"status": "success"})
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")

    return response


@router.get("/me")
async def whoami(request: Request, current_user: CurrentUser) -> UserOut:
    return UserOut.from_orm(current_user)
