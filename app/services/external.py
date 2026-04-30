import httpx

from app.exceptions import APIException

GENDERIZE_URL = "https://api.genderize.io"
AGIFY_URL = "https://api.agify.io"
NATIONALIZE_URL = "https://api.nationalize.io"


class ExternalAPIError(APIException):
    def __init__(self, api_name: str) -> None:
        super().__init__(f"{api_name} returned an invalid response", 502)


def classify_age_group(age: int) -> str:
    if age <= 12:
        return "child"
    if age <= 19:
        return "teenager"
    if age <= 59:
        return "adult"
    return "senior"


async def build_profile_data(name: str) -> dict:
    async with httpx.AsyncClient() as client:
        gender_resp, age_resp, nation_resp = await _fetch_all(client, name)

    gender = gender_resp.get("gender")
    gender_probability = gender_resp.get("probability")
    if not gender or not gender_probability:
        raise ExternalAPIError("Genderize")

    age = age_resp.get("age")
    if age is None:
        raise ExternalAPIError("Agify")

    countries = nation_resp.get("country", [])
    if not countries:
        raise ExternalAPIError("Nationalize")

    top_country = max(countries, key=lambda c: c["probability"])

    return {
        "gender": gender,
        "gender_probability": gender_probability,
        "age": age,
        "age_group": classify_age_group(age),
        "country_id": top_country["country_id"],
        "country_name": _resolve_country_name(top_country["country_id"]),
        "country_probability": top_country["probability"],
    }


async def _fetch_all(client: httpx.AsyncClient, name: str) -> tuple[dict, dict, dict]:
    try:
        gender_resp = await client.get(GENDERIZE_URL, params={"name": name})
        nation_resp = await client.get(NATIONALIZE_URL, params={"name": name})
        age_resp = await client.get(AGIFY_URL, params={"name": name})
        return gender_resp.json(), age_resp.json(), nation_resp.json()
    except httpx.RequestError as e:
        raise APIException("Failed to reach external APIs", 502) from e


def _resolve_country_name(country_id: str) -> str:
    from app.core.countries import COUNTRY_ID_TO_NAME

    return COUNTRY_ID_TO_NAME.get(country_id.upper(), country_id)
