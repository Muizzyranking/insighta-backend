import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import uuid6
from sqlalchemy import func, select

from app.core.countries import get_country_name
from app.database import Base, SessionLocal, engine
from app.models import Profile
from app.services.external import classify_age_group

DATA_PATH = Path(__file__).parents[1] / "data" / "profiles.json"


def load_profiles() -> list[dict]:
    if not DATA_PATH.exists():
        print(f"Error: {DATA_PATH} not found.")
        sys.exit(1)
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("profiles", [])


def validate_and_fix(raw: dict) -> dict | None:
    required = [
        "name",
        "gender",
        "gender_probability",
        "age",
        "country_id",
        "country_probability",
    ]
    for field in required:
        if field not in raw:
            print(f"Skipping profile missing '{field}': {raw.get('name', '?')}")
            return None

    age = int(raw["age"])
    country_id = raw["country_id"].upper()

    return {
        "id": str(uuid6.uuid7()),
        "name": str(raw["name"]).strip(),
        "gender": str(raw["gender"]).lower(),
        "gender_probability": float(raw["gender_probability"]),
        "age": age,
        "age_group": classify_age_group(age),
        "country_id": country_id,
        "country_name": raw.get("country_name") or get_country_name(country_id),
        "country_probability": float(raw["country_probability"]),
        "created_at": datetime.now(timezone.utc),
    }


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    raw_profiles = load_profiles()
    if not raw_profiles:
        print("No profiles found in seed file.")
        return

    inserted = 0
    skipped = 0

    async with SessionLocal() as db:
        for raw in raw_profiles:
            fixed = validate_and_fix(raw)
            if fixed is None:
                skipped += 1
                continue

            result = await db.execute(
                select(Profile).where(func.lower(Profile.name) == fixed["name"].lower())
            )
            if result.scalar_one_or_none():
                skipped += 1
                continue

            db.add(Profile(**fixed))
            inserted += 1

        await db.commit()

    print(f"Done: {inserted} inserted, {skipped} skipped.")


if __name__ == "__main__":
    asyncio.run(seed())
