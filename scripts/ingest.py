"""Queue and monitor MonsoonMind document ingestion."""

import argparse
import json
import os
import sys
import time

import httpx


def headers() -> dict[str, str]:
    token = os.getenv("ADMIN_TOKEN", "")
    if not token:
        raise ValueError("ADMIN_TOKEN is not set in the environment")
    return {"X-Admin-Token": token}


def show_problem(response: httpx.Response) -> int:
    try:
        detail = response.json().get("detail", response.text[:300])
    except ValueError:
        detail = response.text[:300]
    print(f"HTTP {response.status_code}: {detail}")
    return 1


def submit(client: httpx.Client, limit: int) -> int:
    response = client.post("/v1/ingest", headers=headers(), json={"limit": limit})
    if response.status_code != 202:
        return show_problem(response)

    job = response.json()
    print(json.dumps(job, indent=2))
    print(f"\nWatch with: uv run python scripts/ingest.py watch {job['job_id']}")
    return 0


def watch(client: httpx.Client, job_id: str, interval: int) -> int:
    while True:
        response = client.get(f"/v1/ingest/{job_id}")
        if response.status_code != 200:
            return show_problem(response)

        job = response.json()
        print(
            f"\rTotal: {job['total']} | Queued: {job['queued']} | "
            f"Running: {job['running']} | Done: {job['done']} | "
            f"Failed: {job['failed']}",
            end="",
            flush=True,
        )

        if job["queued"] == 0 and job["running"] == 0:
            print()
            return 1 if job["failed"] else 0

        time.sleep(interval)


def dead_letter(client: httpx.Client) -> int:
    response = client.get("/v1/ingest/dead-letter")
    if response.status_code != 200:
        return show_problem(response)
    print(json.dumps(response.json(), indent=2))
    return 0


def retry(client: httpx.Client, job_id: str) -> int:
    response = client.post(
        f"/v1/ingest/{job_id}/retry",
        headers=headers(),
    )
    if response.status_code != 202:
        return show_problem(response)
    print(json.dumps(response.json(), indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="MonsoonMind API base URL",
    )

    commands = parser.add_subparsers(dest="command", required=True)

    submit_parser = commands.add_parser("submit")
    submit_parser.add_argument("--limit", type=int, default=10)

    watch_parser = commands.add_parser("watch")
    watch_parser.add_argument("job_id")
    watch_parser.add_argument("--interval", type=int, default=3)

    retry_parser = commands.add_parser("retry")
    retry_parser.add_argument("job_id")

    commands.add_parser("dead-letter")

    args = parser.parse_args()
    sys.stdout.reconfigure(errors="replace")

    try:
        with httpx.Client(base_url=args.url.rstrip("/"), timeout=30) as client:
            if args.command == "submit":
                return submit(client, args.limit)
            if args.command == "watch":
                return watch(client, args.job_id, args.interval)
            if args.command == "retry":
                return retry(client, args.job_id)
            if args.command == "dead-letter":
                return dead_letter(client)
    except ValueError as exc:
        print(exc)
        return 1
    except httpx.TransportError as exc:
        print(f"{type(exc).__name__}: is the API running at {args.url}?")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
