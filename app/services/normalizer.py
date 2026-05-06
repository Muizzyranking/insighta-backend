import json
from typing import Any

# All filter keys that query_profiles() accepts.
# Any key not present in the input will be set to None in the canonical form.
_FILTER_KEYS = (
    "age_group",
    "country_id",
    "gender",
    "limit",
    "max_age",
    "min_age",
    "min_country_probability",
    "min_gender_probability",
    "order",
    "page",
    "sort_by",
)

_STRING_KEYS = {"age_group", "country_id", "gender", "order", "sort_by"}


def normalize_filters(
    gender: str | None = None,
    country_id: str | None = None,
    age_group: str | None = None,
    min_age: int | None = None,
    max_age: int | None = None,
    min_gender_probability: float | None = None,
    min_country_probability: float | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    page: int = 1,
    limit: int = 10,
) -> dict[str, Any]:
    raw = {
        "age_group": age_group,
        "country_id": country_id,
        "gender": gender,
        "limit": limit,
        "max_age": max_age,
        "min_age": min_age,
        "min_country_probability": min_country_probability,
        "min_gender_probability": min_gender_probability,
        "order": order,
        "page": page,
        "sort_by": sort_by,
    }

    canonical: dict[str, Any] = {}
    for key in sorted(_FILTER_KEYS):
        value = raw.get(key)
        if key in _STRING_KEYS and isinstance(value, str):
            value = value.lower()
        canonical[key] = value

    return canonical


def normalize_from_parsed(
    parsed: dict[str, Any],
    page: int = 1,
    limit: int = 10,
) -> dict[str, Any]:
    return normalize_filters(
        gender=parsed.get("gender"),
        country_id=parsed.get("country_id"),
        age_group=parsed.get("age_group"),
        min_age=parsed.get("min_age"),
        max_age=parsed.get("max_age"),
        min_gender_probability=parsed.get("min_gender_probability"),
        min_country_probability=parsed.get("min_country_probability"),
        sort_by=parsed.get("sort_by", "created_at"),
        order=parsed.get("order", "desc"),
        page=page,
        limit=limit,
    )


def make_cache_key(canonical: dict[str, Any]) -> str:
    return json.dumps(canonical, sort_keys=True)
