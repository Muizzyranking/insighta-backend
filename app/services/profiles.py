from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Profile
from app.schemas.profiles import PaginationLinks, ProfileFullView

ALLOWED_SORT = {"age", "created_at", "gender_probability"}
VALID_GENDERS = {"male", "female"}
VALID_AGE_GROUPS = {"child", "teenager", "adult", "senior"}


async def query_profiles(
    db: AsyncSession,
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
) -> tuple[list[ProfileFullView], int]:
    stmt = select(Profile)
    count_stmt = select(func.count()).select_from(Profile)

    filters = []

    if gender and gender.lower() in VALID_GENDERS:
        filters.append(func.lower(Profile.gender) == gender.lower())

    if country_id:
        filters.append(func.lower(Profile.country_id) == country_id.lower())

    if age_group and age_group.lower() in VALID_AGE_GROUPS:
        filters.append(func.lower(Profile.age_group) == age_group.lower())

    if min_age is not None and min_age >= 0:
        filters.append(Profile.age >= min_age)

    if max_age is not None and max_age >= 0:
        filters.append(Profile.age <= max_age)

    if min_gender_probability is not None:
        filters.append(Profile.gender_probability >= min_gender_probability)

    if min_country_probability is not None:
        filters.append(Profile.country_probability >= min_country_probability)

    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    sort_col = sort_by if sort_by in ALLOWED_SORT else "created_at"
    col = getattr(Profile, sort_col)
    stmt = stmt.order_by(col.asc() if order.lower() == "asc" else col.desc())
    stmt = stmt.offset((page - 1) * limit).limit(limit)

    result = await db.execute(stmt)
    profiles = list(result.scalars().all())

    return [ProfileFullView.from_orm(p) for p in profiles], total


def build_links(path: str, page: int, limit: int, total: int) -> PaginationLinks:
    total_pages = max(1, (total + limit - 1) // limit)
    return PaginationLinks(
        self=f"{path}?page={page}&limit={limit}",
        next=f"{path}?page={page + 1}&limit={limit}" if page < total_pages else None,
        prev=f"{path}?page={page - 1}&limit={limit}" if page > 1 else None,
    )
