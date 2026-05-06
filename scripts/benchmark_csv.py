import time

import httpx

BASE_URL = "http://localhost:8000"


def benchmark_import(filepath: str):
    with open(filepath, "rb") as f:
        content = f.read()

    file_size_mb = len(content) / (1024 * 1024)
    print(f"File size: {file_size_mb:.1f} MB")

    start = time.perf_counter()

    with httpx.Client(timeout=300) as client:
        resp = client.post(
            f"{BASE_URL}/api/profiles/import",
            headers={"X-API-Version": "1"},
            files={"file": ("test.csv", content, "text/csv")},
        )

    elapsed = time.perf_counter() - start

    print(f"Status: {resp.status_code}")
    print(f"Time: {elapsed:.1f}s")

    if resp.status_code == 200:
        data = resp.json()
        print(f"Total rows: {data['total_rows']}")
        print(f"Inserted:   {data['inserted']}")
        print(f"Skipped:    {data['skipped']}")
        print(f"Reasons:    {data['reasons']}")
        print(f"Rows/sec:   {data['total_rows'] / elapsed:.0f}")


if __name__ == "__main__":
    import sys

    filepath = sys.argv[1] if len(sys.argv) > 1 else "test_500k.csv"
    benchmark_import(filepath)
