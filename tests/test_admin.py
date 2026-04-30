import pytest
from httpx import AsyncClient

from tests.conftest import make_access_token

HEADERS = {"x-api-version": "1"}


@pytest.mark.asyncio
async def test_promote_user_as_analyst(client: AsyncClient, analyst_user):
    resp = await client.patch(
        f"/api/admin/users/{analyst_user.id}/promote",
        headers={
            **HEADERS,
            "authorization": f"Bearer {make_access_token(analyst_user)}",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_promote_nonexistent_user(client: AsyncClient, admin_user):
    resp = await client.patch(
        "/api/admin/users/nonexistent-id/promote",
        headers={
            **HEADERS,
            "authorization": f"Bearer {make_access_token(admin_user)}",
        },
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_promote_already_admin(client: AsyncClient, admin_user):
    resp = await client.patch(
        f"/api/admin/users/{admin_user.id}/promote",
        headers={
            **HEADERS,
            "authorization": f"Bearer {make_access_token(admin_user)}",
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_promote_success(client: AsyncClient, admin_user, analyst_user):
    resp = await client.patch(
        f"/api/admin/users/{analyst_user.id}/promote",
        headers={
            **HEADERS,
            "authorization": f"Bearer {make_access_token(admin_user)}",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "admin"
