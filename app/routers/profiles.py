import csv
import io
from datetime import datetime, timezone
from typing import Annotated

import uuid6
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.dependencies import AdminUser, CurrentUser, DBSession
from app.dependencies.versioning import require_api_version
from app.exceptions import APIException
from app.middleware.rate_limit import limiter
from app.models import Profile
from app.schemas.nl import NaturalLanguageQuery
from app.schemas.profiles import (
    ExportProfileQuery,
    LisProfilesFilterQuery,
    ProfileCreateRequest,
    ProfileCreateResponse,
    ProfileFullView,
    ProfileListResponse,
    ProfileSingleResponse,
)
from app.services.cache import cache_invalidate
from app.services.nl_parser import parse_natural_language
from app.services.profiles import build_links, query_profiles_cached

router = APIRouter(
    prefix="/api/profiles",
    tags=["profiles"],
    dependencies=[Depends(require_api_version)],
)


@router.post("", status_code=201)
@limiter.limit("60/minute")
async def create_profile(
    request: Request,
    body: ProfileCreateRequest,
    user: AdminUser,
    db: DBSession,
) -> ProfileCreateResponse:
    result = await db.execute(
        select(Profile).where(func.lower(Profile.name) == body.name.lower())
    )
    existing = result.scalar_one_or_none()

    if existing:
        return ProfileCreateResponse(
            data=ProfileFullView.from_orm(existing),
            message="Profile already exists",
        )

    from app.services.external import build_profile_data

    external_data = await build_profile_data(body.name)

    profile = Profile(
        id=str(uuid6.uuid7()),
        name=body.name,
        created_at=datetime.now(timezone.utc),
        **external_data,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    cache_invalidate()

    return ProfileCreateResponse(data=ProfileFullView.from_orm(profile))


@router.get("/search")
@limiter.limit("60/minute")
async def search_profiles(
    request: Request,
    user: CurrentUser,
    db: DBSession,
    query: Annotated[NaturalLanguageQuery, Query()],
) -> ProfileListResponse:
    filters = parse_natural_language(query.q)
    page = query.page
    limit = min(query.limit, 50)

    profiles, total = await query_profiles_cached(
        db,
        gender=filters.get("gender"),
        country_id=filters.get("country_id"),
        age_group=filters.get("age_group"),
        min_age=filters.get("min_age"),
        max_age=filters.get("max_age"),
        page=page,
        limit=limit,
    )

    return ProfileListResponse(
        page=page,
        limit=limit,
        total=total,
        total_pages=max(1, (total + limit - 1) // limit),
        links=build_links("/api/profiles/search", page, limit, total),
        data=profiles,
    )


@router.get("/export")
@limiter.limit("60/minute")
async def export_profiles(
    request: Request,
    user: CurrentUser,
    db: DBSession,
    query: Annotated[ExportProfileQuery, Query()],
) -> StreamingResponse:
    if query.format != "csv":
        raise APIException("Only csv format is supported", 400)

    profiles, _ = await query_profiles_cached(
        db,
        gender=query.gender,
        country_id=query.country_id,
        age_group=query.age_group,
        min_age=query.min_age,
        max_age=query.max_age,
        sort_by=query.sort_by,
        order=query.order,
        page=1,
        limit=10_000,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "name",
            "gender",
            "gender_probability",
            "age",
            "age_group",
            "country_id",
            "country_name",
            "country_probability",
            "created_at",
        ]
    )
    for p in profiles:
        writer.writerow(
            [
                p.id,
                p.name,
                p.gender,
                p.gender_probability,
                p.age,
                p.age_group,
                p.country_id,
                p.country_name,
                p.country_probability,
                p.created_at,
            ]
        )

    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=profiles_{timestamp}.csv"
        },
    )


@router.get("")
@limiter.limit("60/minute")
async def list_profiles(
    request: Request,
    user: CurrentUser,
    db: DBSession,
    query: Annotated[LisProfilesFilterQuery, Query()],
) -> ProfileListResponse:
    gender = query.gender
    limit = min(query.limit, 50)
    page = query.page

    profiles, total = await query_profiles_cached(
        db,
        gender=gender,
        country_id=query.country_id,
        age_group=query.age_group,
        min_age=query.min_age,
        max_age=query.max_age,
        min_gender_probability=query.min_gender_probability,
        min_country_probability=query.min_country_probability,
        sort_by=query.sort_by,
        order=query.order,
        page=page,
        limit=limit,
    )

    return ProfileListResponse(
        page=page,
        limit=limit,
        total=total,
        total_pages=max(1, (total + limit - 1) // limit),
        links=build_links("/api/profiles", page, limit, total),
        data=profiles,
    )


@router.get("/{profile_id}")
@limiter.limit("60/minute")
async def get_profile(
    request: Request,
    profile_id: str,
    user: CurrentUser,
    db: DBSession,
) -> ProfileSingleResponse:
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise APIException("Profile not found", 404)

    return ProfileSingleResponse(data=ProfileFullView.from_orm(profile))


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    request: Request,
    profile_id: str,
    user: AdminUser,
    db: DBSession,
):
    result = await db.execute(select(Profile).where(Profile.id == profile_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise APIException("Profile not found", 404)

    await db.delete(profile)
    await db.commit()
    cache_invalidate()
