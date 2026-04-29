from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ProfileCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Name cannot be empty")
        return stripped


class ProfileListQuery(BaseModel):
    gender: str | None = None
    country_id: str | None = None
    age_group: str | None = None
    min_age: int | None = Field(None, ge=0)
    max_age: int | None = Field(None, ge=0)
    min_gender_probability: float | None = Field(None, ge=0.0, le=1.0)
    min_country_probability: float | None = Field(None, ge=0.0, le=1.0)
    sort_by: str = "created_at"
    order: str = "desc"
    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=50)

    @field_validator("gender", "country_id", "age_group")
    @classmethod
    def lowercase_strings(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class ProfileFullView(BaseModel):
    id: str
    name: str
    gender: str
    gender_probability: float
    age: int
    age_group: str
    country_id: str
    country_name: str
    country_probability: float
    created_at: str

    @field_validator("gender_probability", "country_probability")
    @classmethod
    def round_probabilities(cls, v: float) -> float:
        return round(v, 2)

    @field_validator("created_at", mode="before")
    @classmethod
    def format_datetime(cls, v: Any) -> str:
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%dT%H:%M:%SZ")
        return v

    @classmethod
    def from_orm(cls, obj: Any) -> "ProfileFullView":
        return cls(
            id=obj.id,
            name=obj.name,
            gender=obj.gender,
            gender_probability=obj.gender_probability,
            age=obj.age,
            age_group=obj.age_group,
            country_id=obj.country_id,
            country_name=obj.country_name,
            country_probability=obj.country_probability,
            created_at=obj.created_at,
        )


class PaginationLinks(BaseModel):
    self: str
    next: str | None
    prev: str | None


class ProfileListResponse(BaseModel):
    status: str = "success"
    page: int
    limit: int
    total: int
    total_pages: int
    links: PaginationLinks
    data: list[ProfileFullView]


class ProfileCreateResponse(BaseModel):
    status: str = "success"
    message: str | None = None
    data: ProfileFullView


class ProfileSingleResponse(BaseModel):
    status: str = "success"
    data: ProfileFullView
