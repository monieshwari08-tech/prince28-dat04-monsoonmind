"""Smoke-test the deployed MonsoonMind API."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def get_json(url: str) -> dict:
    try:
        with urlopen(url, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError(f"{url} returned HTTP {response.status}")
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Request failed for {url}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test MonsoonMind.")
    parser.add_argument("base_url", help="Base URL of the deployed API")
    parser.add_argument("--expect-version", help="Expected Git commit SHA")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    try:
        health = get_json(f"{base_url}/health")
        print("Health:", health)

        if health.get("status") != "ok":
            raise RuntimeError("Health check failed")

        if args.expect_version:
            actual = health.get("version")
            if actual != args.expect_version:
                raise RuntimeError(
                    f"Version mismatch: expected {args.expect_version}, got {actual}"
                )

        ready = get_json(f"{base_url}/ready")
        print("Readiness:", ready)

        if ready.get("status") != "ready":
            raise RuntimeError("Readiness check failed")

        if ready.get("checks", {}).get("database") is not True:
            raise RuntimeError("Database check failed")

        get_json(f"{base_url}/v1/documents?limit=1")
        print("Documents endpoint: OK")
        print("Smoke test passed!")
        return 0

    except (RuntimeError, ValueError) as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
