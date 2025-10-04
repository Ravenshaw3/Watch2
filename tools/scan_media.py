#!/usr/bin/env python3
"""Trigger a Watch2 media scan and optional category summary."""

from __future__ import annotations

import argparse
import sys
from typing import List

from watch2_client import Watch2Client, create_client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Trigger a Watch2 media scan")
    parser.add_argument(
        "--directories",
        nargs="*",
        help="Optional list of directories to include in the scan",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show the updated scan summary after the run",
    )
    return parser.parse_args()


def print_scan_result(result: dict) -> None:
    job = result.get("job", {})
    print("✅ Scan job created")
    print(f"   ID: {job.get('id')}")
    print(f"   Status: {job.get('status')}")
    print(f"   Started: {job.get('startedAt')}")
    print(f"   Finished: {job.get('finishedAt')}")

    payload = result.get("result") or {}
    if payload:
        print("📊 Result payload:")
        for key, value in payload.items():
            print(f"   {key}: {value}")


def print_summary(summary: dict) -> None:
    print("\n📈 Current scan summary:")
    print(f"   Total jobs: {summary.get('totalJobs', 0)}")
    for status, count in summary.get("byStatus", {}).items():
        print(f"   {status}: {count}")
    latest = summary.get("latestJob")
    if latest:
        print("   Latest job:")
        print(f"     ID: {latest.get('id')}")
        print(f"     Type: {latest.get('jobType')}")
        print(f"     Status: {latest.get('status')}")
        print(f"     Started: {latest.get('startedAt')}")
        print(f"     Finished: {latest.get('finishedAt')}")


def main() -> int:
    args = parse_args()
    client = create_client()

    directories: List[str] | None = args.directories if args.directories else None

    print(f"🔐 Authenticating as {client.email}...")
    client.ensure_login()
    print("✅ Login successful")

    print("🔄 Triggering media scan...")
    result = client.start_scan(directories=directories)
    print_scan_result(result)

    if args.summary:
        summary = client.scans_summary()
        print_summary(summary)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"❌ {exc}", file=sys.stderr)
        raise SystemExit(1)
