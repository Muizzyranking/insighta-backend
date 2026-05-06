"""
Ingestion benchmark v5 — COPY path, explicit transaction on raw_conn.
Run with: uv run python scripts/benchmark_ingest.py
"""

import asyncio
import csv
import io
import sys
import os
import time
from datetime import datetime, timezone

import uuid6

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine
from app.core.countries import COUNTRY_ID_TO_NAME

TEST_ROWS = 500_000

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

VALID_GENDERS = {"male", "female"}


def _age_group(age: int) -> str:
    if age <= 12:
        return "child"
    elif age <= 17:
        return "teenager"
    elif age <= 64:
        return "adult"
    else:
        return "senior"


def make_test_csv(n: int) -> bytes:
    print(f"Generating {n:,} row test CSV...", flush=True)
    t0 = time.perf_counter()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["name", "gender", "age", "country_id"])
    countries = list(COUNTRY_ID_TO_NAME.keys())
    for i in range(n):
        writer.writerow(
            [
                f"BenchmarkV5 Person {i}",
                "male" if i % 2 == 0 else "female",
                (i % 80) + 10,
                countries[i % len(countries)],
            ]
        )
    elapsed = time.perf_counter() - t0
    result = buf.getvalue().encode("utf-8")
    print(f"  {len(result) / 1_000_000:.1f}MB generated in {elapsed:.2f}s", flush=True)
    return result


def parse_and_validate(file_bytes: bytes) -> list[tuple]:
    print(f"\nParsing + validating {TEST_ROWS:,} rows...", flush=True)
    t0 = time.perf_counter()
    text_data = file_bytes.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text_data))
    now = datetime.now(timezone.utc)
    rows = []
    for raw in reader:
        name = str(raw.get("name", "")).strip()
        gender = str(raw.get("gender", "")).strip().lower()
        try:
            age = int(str(raw.get("age", "")).strip())
        except ValueError:
            continue
        country_id = str(raw.get("country_id", "")).strip().upper()
        if (
            not name
            or gender not in VALID_GENDERS
            or age < 0
            or country_id not in COUNTRY_ID_TO_NAME
        ):
            continue
        rows.append(
            (
                str(uuid6.uuid7()),
                name,
                gender,
                1.0,
                age,
                _age_group(age),
                country_id,
                COUNTRY_ID_TO_NAME[country_id],
                1.0,
                now,
            )
        )
    elapsed = time.perf_counter() - t0
    print(
        f"  {len(rows):,} valid rows in {elapsed:.2f}s ({len(rows) / elapsed:,.0f} rows/sec)"
    )
    return rows


async def benchmark_copy(records: list[tuple]):
    print(f"\nCOPY benchmark ({len(records):,} rows)...", flush=True)

    # Acquire a raw asyncpg connection directly from the engine pool.
    # This bypasses SQLAlchemy session transaction management entirely,
    # so we have full control over BEGIN/COMMIT and temp table lifetime.
    async with engine.connect() as sa_conn:
        raw_conn = await sa_conn.get_raw_connection()
        raw_conn = raw_conn.driver_connection

        # Clean up previous run
        await raw_conn.execute("DELETE FROM profiles WHERE name LIKE 'BenchmarkV5%'")

        t0 = time.perf_counter()

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

        t_copy = time.perf_counter()
        await raw_conn.copy_records_to_table(
            "profiles_import",
            records=records,
            columns=COPY_COLUMNS,
        )
        copy_elapsed = time.perf_counter() - t_copy
        print(
            f"  COPY into temp:   {copy_elapsed:.2f}s  ({len(records) / copy_elapsed:,.0f} rows/sec)"
        )

        t_insert = time.perf_counter()
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
        insert_elapsed = time.perf_counter() - t_insert
        inserted = int(result.split()[-1])
        print(
            f"  INSERT from temp: {insert_elapsed:.2f}s  — {inserted:,} rows inserted"
        )

        await raw_conn.execute("DROP TABLE profiles_import")
        await raw_conn.execute("COMMIT")

        total = time.perf_counter() - t0
        print(f"\n  Total DB time:    {total:.2f}s")
        print(f"  End-to-end rate:  {inserted / total:,.0f} rows/sec")

        # Cleanup
        await raw_conn.execute("DELETE FROM profiles WHERE name LIKE 'BenchmarkV5%'")
        await raw_conn.execute("COMMIT")
        print("  Cleaned up.")


async def main():
    print("=" * 60)
    print("INSIGHTA COPY BENCHMARK v5")
    print("=" * 60)
    file_bytes = make_test_csv(TEST_ROWS)
    records = parse_and_validate(file_bytes)
    await benchmark_copy(records)
    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
