import csv
import io
from collections import defaultdict
from datetime import datetime, timezone

import uuid6
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.countries import COUNTRY_ID_TO_NAME
from app.database import engine
from app.services.cache import cache_invalidate

VALID_GENDERS = {"male", "female"}

COPY_COLUMNS = [
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


def _derive_age_group(age: int) -> str:
    if age <= 12:
        return "child"
    elif age <= 17:
        return "teenager"
    elif age <= 64:
        return "adult"
    else:
        return "senior"


def _validate_row(row: dict, now: datetime) -> tuple[tuple | None, str | None]:
    """
    Validate one CSV row and return a COPY-ready tuple, or a skip reason.
    """
    for field in ("name", "gender", "age", "country_id"):
        if field not in row or not str(row.get(field, "")).strip():
            return None, "missing_fields"

    name = str(row["name"]).strip()
    if not name:
        return None, "missing_fields"

    gender = str(row["gender"]).strip().lower()
    if gender not in VALID_GENDERS:
        return None, "invalid_gender"

    try:
        age = int(str(row["age"]).strip())
    except (ValueError, TypeError):
        return None, "invalid_age"

    if age < 0 or age > 150:
        return None, "invalid_age"

    country_id = str(row["country_id"]).strip().upper()
    if country_id not in COUNTRY_ID_TO_NAME:
        return None, "invalid_country"

    return (
        str(uuid6.uuid7()),  # id
        name,  # name
        gender,  # gender
        1.0,  # gender_probability
        age,  # age
        _derive_age_group(age),  # age_group
        country_id,  # country_id
        COUNTRY_ID_TO_NAME[country_id],  # country_name
        1.0,  # country_probability
        now,  # created_at
    ), None


async def ingest_csv(db: AsyncSession, file_bytes: bytes) -> dict:
    """
    Parse and bulk-load profiles from CSV bytes into Postgres via COPY.

    Returns:
    {
        "status": "success",
        "total_rows": N,
        "inserted": N,
        "skipped": N,
        "reasons": { "duplicate_name": N, "invalid_age": N, ... }
    }
    """
    total_rows = 0
    skipped = 0
    reasons: dict[str, int] = defaultdict(int)

    # ── Step 1: decode ────────────────────────────────────────────────────────
    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("utf-8", errors="replace")

    # ── Step 2: parse + validate all rows ────────────────────────────────────
    # Single shared timestamp — avoids 500k datetime.now() calls and gives
    # the entire import batch a consistent created_at.
    now = datetime.now(timezone.utc)
    reader = csv.DictReader(io.StringIO(text))
    valid_rows: list[tuple] = []

    for raw_row in reader:
        total_rows += 1
        try:
            record, reason = _validate_row(raw_row, now)
        except Exception:
            skipped += 1
            reasons["malformed_row"] += 1
            continue

        if record is None:
            skipped += 1
            reasons[reason] += 1
            continue

        valid_rows.append(record)

    if not valid_rows:
        return {
            "status": "success",
            "total_rows": total_rows,
            "inserted": 0,
            "skipped": skipped,
            "reasons": dict(reasons),
        }

    # ── Step 3: COPY via raw asyncpg connection ───────────────────────────────
    # We use engine.connect() + get_raw_connection() to bypass SQLAlchemy's
    # session transaction management. This gives us a clean asyncpg connection
    # where we control BEGIN/COMMIT, so the temp table stays alive for the
    # full duration of our operation.
    inserted = 0

    try:
        async with engine.connect() as sa_conn:
            raw_conn = (await sa_conn.get_raw_connection()).driver_connection

            await raw_conn.execute("""
                CREATE TEMP TABLE profiles_import (
                    id                  TEXT,
                    name                TEXT,
                    gender              TEXT,
                    gender_probability  DOUBLE PRECISION,
                    age                 INTEGER,
                    age_group           TEXT,
                    country_id          TEXT,
                    country_name        TEXT,
                    country_probability DOUBLE PRECISION,
                    created_at          TIMESTAMPTZ
                )
            """)

            await raw_conn.copy_records_to_table(
                "profiles_import",
                records=valid_rows,
                columns=COPY_COLUMNS,
            )

            result = await raw_conn.execute("""
                INSERT INTO profiles (
                    id, name, gender, gender_probability,
                    age, age_group, country_id, country_name,
                    country_probability, created_at
                )
                SELECT
                    id, name, gender, gender_probability,
                    age, age_group, country_id, country_name,
                    country_probability, created_at
                FROM profiles_import
                ON CONFLICT (name) DO NOTHING
            """)

            inserted = int(result.split()[-1])
            duplicate_count = len(valid_rows) - inserted

            await raw_conn.execute("DROP TABLE profiles_import")
            await raw_conn.execute("COMMIT")

    except Exception:
        skipped += len(valid_rows)
        return {
            "status": "success",
            "total_rows": total_rows,
            "inserted": 0,
            "skipped": skipped,
            "reasons": dict(reasons),
        }

    if duplicate_count > 0:
        reasons["duplicate_name"] += duplicate_count
    skipped += duplicate_count

    cache_invalidate()

    return {
        "status": "success",
        "total_rows": total_rows,
        "inserted": inserted,
        "skipped": skipped,
        "reasons": dict(reasons),
    }
