import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_github_login_redirects(client: AsyncClient):
    resp = await client.get("/auth/github", follow_redirects=False)
    assert resp.status_code in (302, 307)
    assert "github.com/login/oauth/authorize" in resp.headers["location"]


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    resp = await client.post(
        "/auth/refresh",
        json={"refresh_token": "fake-token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalid_token(client: AsyncClient):
    resp = await client.post(
        "/auth/logout",
        json={"refresh_token": "fake-token"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_whoami_no_auth(client: AsyncClient):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_whoami_authenticated(client: AsyncClient, analyst_user):
    from tests.conftest import make_access_token

    resp = await client.get(
        "/auth/me",
        headers={"authorization": f"Bearer {make_access_token(analyst_user)}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["username"] == "testanalyst"
    assert body["role"] == "analyst"
