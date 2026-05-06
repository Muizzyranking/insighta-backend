import asyncio
import statistics
import time

import httpx

HEADERS = {"X-API-Version": "1"}
BASE_URL = "http://localhost:8000"

QUERIES = [
    "/api/profiles",
    "/api/profiles?gender=male",
    "/api/profiles?gender=male&country_id=NG",
    "/api/profiles?gender=female&age_group=adult",
    "/api/profiles?min_age=20&max_age=40&country_id=NG",
    "/api/profiles/search?q=young males from nigeria",
    "/api/profiles/search?q=adult females above 30",
]


async def measure(client: httpx.AsyncClient, url: str, n: int = 10) -> dict:
    times = []
    for _ in range(n):
        start = time.perf_counter()
        resp = await client.get(f"{BASE_URL}{url}", headers=HEADERS)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)
        assert resp.status_code == 200, f"Got {resp.status_code} for {url}"

    return {
        "url": url,
        "p50": round(statistics.median(times), 1),
        "p95": round(statistics.quantiles(times, n=20)[18], 1),
        "min": round(min(times), 1),
        "max": round(max(times), 1),
        "first": round(times[0], 1),  # cold
        "second": round(times[1], 1),  # warm (cache hit)
    }


async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        print(f"{'URL':<55} {'P50':>8} {'P95':>8} {'COLD':>8} {'WARM':>8}")
        print("-" * 90)

        for query in QUERIES:
            result = await measure(client, query)
            print(
                f"{result['url']:<55} "
                f"{result['p50']:>7}ms "
                f"{result['p95']:>7}ms "
                f"{result['first']:>7}ms "
                f"{result['second']:>7}ms"
            )


asyncio.run(main())
