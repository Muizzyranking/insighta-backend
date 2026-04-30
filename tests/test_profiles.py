import pytest
from httpx import AsyncClient

from tests.conftest import make_access_token

HEADERS = {"x-api-version": "1", "content-type": "application/json"}


def auth_headers(user) -> dict:
    return {**HEADERS, "authorization": f"Bearer {make_access_token(user)}"}


@pytest.mark.asyncio
async def test_create_profile_no_version_header(client: AsyncClient, admin_user):
    resp = await client.post(
        "/api/profiles",
        json={"name": "Emmanuel"},
        headers={"authorization": f"Bearer {make_access_token(admin_user)}"},
    )
    assert resp.status_code == 400
    assert resp.json()["status"] == "error"


@pytest.mark.asyncio
async def test_create_profile_analyst_forbidden(client: AsyncClient, analyst_user):
    resp = await client.post(
        "/api/profiles",
        json={"name": "Emmanuel"},
        headers=auth_headers(analyst_user),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_profile_missing_name(client: AsyncClient, admin_user):
    resp = await client.post(
        "/api/profiles",
        json={},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_profile_empty_name(client: AsyncClient, admin_user):
    resp = await client.post(
        "/api/profiles",
        json={"name": "   "},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_profile_invalid_name_type(client: AsyncClient, admin_user):
    resp = await client.post(
        "/api/profiles",
        json={"name": 123},
        headers=auth_headers(admin_user),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_profiles_no_auth(client: AsyncClient):
    resp = await client.get("/api/profiles", headers={"x-api-version": "1"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_profiles_no_version(client: AsyncClient, analyst_user):
    resp = await client.get(
        "/api/profiles",
        headers={"authorization": f"Bearer {make_access_token(analyst_user)}"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_profiles_success(client: AsyncClient, analyst_user):
    resp = await client.get(
        "/api/profiles",
        headers=auth_headers(analyst_user),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "data" in body
    assert "total" in body
    assert "total_pages" in body
    assert "links" in body
    assert "self" in body["links"]


@pytest.mark.asyncio
async def test_list_profiles_pagination_shape(client: AsyncClient, analyst_user):
    resp = await client.get(
        "/api/profiles?page=1&limit=10",
        headers=auth_headers(analyst_user),
    )
    body = resp.json()
    assert body["page"] == 1
    assert body["limit"] == 10
    assert body["links"]["prev"] is None


@pytest.mark.asyncio
async def test_search_missing_q(client: AsyncClient, analyst_user):
    resp = await client.get(
        "/api/profiles/search",
        headers=auth_headers(analyst_user),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_search_uninterpretable(client: AsyncClient, analyst_user):
    resp = await client.get(
        "/api/profiles/search?q=xyzzy+blorp",
        headers=auth_headers(analyst_user),
    )
    assert resp.status_code == 400
    assert resp.json()["message"] == "Unable to interpret query"


@pytest.mark.asyncio
async def test_search_valid_query(client: AsyncClient, analyst_user):
    resp = await client.get(
        "/api/profiles/search?q=young males from nigeria",
        headers=auth_headers(analyst_user),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "data" in body


@pytest.mark.asyncio
async def test_get_profile_not_found(client: AsyncClient, analyst_user):
    resp = await client.get(
        "/api/profiles/nonexistent-id",
        headers=auth_headers(analyst_user),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_profile_analyst_forbidden(client: AsyncClient, analyst_user):
    resp = await client.delete(
        "/api/profiles/some-id",
        headers=auth_headers(analyst_user),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_export_csv(client: AsyncClient, analyst_user):
    resp = await client.get(
        "/api/profiles/export?format=csv",
        headers=auth_headers(analyst_user),
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/csv; charset=utf-8"


@pytest.mark.asyncio
async def test_export_invalid_format(client: AsyncClient, analyst_user):
    resp = await client.get(
        "/api/profiles/export?format=xml",
        headers=auth_headers(analyst_user),
    )
    assert resp.status_code == 400
