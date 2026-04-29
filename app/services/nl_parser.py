import re
from typing import Any

from app.core.countries import COUNTRY_NAME_TO_ID
from app.exceptions import APIException

GENDER_KEYWORDS: dict[str, str] = {
    "male": "male",
    "males": "male",
    "man": "male",
    "men": "male",
    "boy": "male",
    "boys": "male",
    "female": "female",
    "females": "female",
    "woman": "female",
    "women": "female",
    "girl": "female",
    "girls": "female",
}

AGE_GROUP_KEYWORDS: dict[str, str] = {
    "child": "child",
    "children": "child",
    "kid": "child",
    "kids": "child",
    "teenager": "teenager",
    "teenagers": "teenager",
    "teen": "teenager",
    "teens": "teenager",
    "adult": "adult",
    "adults": "adult",
    "senior": "senior",
    "seniors": "senior",
    "elderly": "senior",
    "old": "senior",
}

AGE_ABOVE_RE = re.compile(r"(?:above|over|older\s+than)\s+(\d+)", re.IGNORECASE)
AGE_BELOW_RE = re.compile(r"(?:below|under|younger\s+than)\s+(\d+)", re.IGNORECASE)
AGE_BETWEEN_RE = re.compile(r"between\s+(\d+)\s+and\s+(\d+)", re.IGNORECASE)


class UnableToInterpretQuery(APIException):
    def __init__(self) -> None:
        super().__init__("Unable to interpret query", status_code=400)


def parse_natural_language(query: str) -> dict[str, Any]:
    normalized = query.lower().strip()
    if not normalized:
        raise UnableToInterpretQuery()

    filters: dict[str, Any] = {}
    tokens = re.findall(r"[a-zA-Z]+|\d+", normalized)
    token_set = set(tokens)

    # Gender
    for token, gender in GENDER_KEYWORDS.items():
        if token in token_set:
            filters["gender"] = gender
            break

    # Age group
    for token, age_group in AGE_GROUP_KEYWORDS.items():
        if token in token_set:
            filters["age_group"] = age_group
            break

    # "young" / "youth" → age range 16–24
    if "young" in token_set or "youth" in token_set:
        filters["min_age"] = 16
        filters["max_age"] = 24

    between_match = AGE_BETWEEN_RE.search(normalized)
    if between_match:
        filters["min_age"] = int(between_match.group(1))
        filters["max_age"] = int(between_match.group(2))
    else:
        above_match = AGE_ABOVE_RE.search(normalized)
        if above_match:
            filters["min_age"] = int(above_match.group(1))

        below_match = AGE_BELOW_RE.search(normalized)
        if below_match:
            filters["max_age"] = int(below_match.group(1))

    for name, cid in sorted(COUNTRY_NAME_TO_ID.items(), key=lambda x: -len(x[0])):
        if name in normalized:
            filters["country_id"] = cid
            break

    if not filters:
        raise UnableToInterpretQuery()

    return filters
