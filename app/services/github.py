import httpx

from app.config import settings
from app.exceptions import APIException


async def exchange_code_for_user(code: str, code_verifier: str | None) -> dict:
    """Exchange OAuth code for GitHub access token, then fetch user info."""
    async with httpx.AsyncClient() as client:
        payload: dict = {
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret,
            "code": code,
            "redirect_uri": settings.github_redirect_uri,
        }
        if code_verifier:
            payload["code_verifier"] = code_verifier

        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            json=payload,
            headers={"Accept": "application/json"},
        )

        token_data = token_resp.json()
        github_access_token = token_data.get("access_token")

        if not github_access_token:
            raise APIException("Failed to obtain GitHub access token", 502)

        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {github_access_token}",
                "Accept": "application/json",
            },
        )

        if user_resp.status_code != 200:
            raise APIException("Failed to fetch GitHub user info", 502)

        return user_resp.json()
