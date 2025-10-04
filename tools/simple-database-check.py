#!/usr/bin/env python3
"""Simple Watch2 database and frontend smoke check."""

from __future__ import annotations

import sys
from typing import Dict

import requests

from watch2_client import Watch2Client, Watch2ClientError, create_client


def test_database_population(client: Watch2Client) -> bool:
    print("DATABASE POPULATION CHECK")
    print("========================")

    try:
        client.ensure_login()
        print("SUCCESS: Authentication successful")
    except Watch2ClientError as error:
        print(f"ERROR: Authentication failed: {error}")
        return False

    try:
        response = client.get("/media", auth=True)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        print(f"ERROR: Media API error: {error}")
        return False

    items = payload.get("items", [])
    total_items = len(items)

    print("\nMEDIA DATABASE STATUS:")
    print(f"  - Items returned: {total_items}")

    if items:
        print("  - Sample Media Items:")
        for index, item in enumerate(items[:5], start=1):
            title = item.get("title") or item.get("name") or item.get("id")
            status = item.get("status", "unknown")
            print(f"    {index}. {title} [status={status}]")

    try:
        categories_response = client.get("/media/categories", auth=True)
        categories_response.raise_for_status()
        categories = categories_response.json().get("categories", [])
        print(f"  - Categories: {len(categories)}")
    except requests.RequestException as error:
        print(f"ERROR: Category API error: {error}")
        return False

    return total_items > 0


def test_frontend_access(client: Watch2Client) -> bool:
    print("\nFRONTEND ACCESS CHECK")
    print("====================")

    if client.wait_for_frontend(timeout=10):
        print(f"SUCCESS: Frontend accessible at {client.frontend_url}")
        return True

    print("ERROR: Frontend did not respond with HTTP 200 within timeout")
    return False


def test_api_endpoints(client: Watch2Client) -> bool:
    print("\nAPI ENDPOINTS CHECK")
    print("==================")

    try:
        client.ensure_login()
    except Watch2ClientError as error:
        print(f"ERROR: Could not authenticate for API tests: {error}")
        return False

    endpoints: Dict[str, str] = {
        "Media List": "/media",
        "Media Categories": "/media/categories",
        "Playlists": "/playlists",
        "Settings": "/settings",
        "Analytics Dashboard": "/analytics/dashboard",
        "Scans Summary": "/scans/summary",
        "System Version": "/system/version",
    }

    successes = 0

    for name, path in endpoints.items():
        try:
            response = client.get(path, auth=not path.startswith("/system"))
            response.raise_for_status()
            print(f"SUCCESS: {name} - {response.status_code} OK")
            successes += 1
        except requests.HTTPError as error:
            print(f"ERROR: {name} - {error.response.status_code} {error.response.text}")
        except requests.RequestException as error:
            print(f"ERROR: {name} - {error}")

    total = len(endpoints)
    print(f"\nAPI ENDPOINTS: {successes}/{total} working")
    return successes == total


def main() -> int:
    print("WATCH2 DATABASE AND FRONTEND CHECK")
    print("==================================")

    client = create_client()

    database_ok = test_database_population(client)
    frontend_ok = test_frontend_access(client)
    api_ok = test_api_endpoints(client)

    print("\n" + "=" * 50)
    print("OVERALL SYSTEM STATUS")
    print("=" * 50)

    tests = {
        "Database Population": database_ok,
        "Frontend Access": frontend_ok,
        "API Endpoints": api_ok,
    }

    success_count = sum(1 for result in tests.values() if result)

    for test_name, result in tests.items():
        status = "SUCCESS" if result else "FAILED"
        indicator = "[OK]" if result else "[FAIL]"
        print(f"{test_name:20} | {status:7} | {indicator}")

    print(f"\nOVERALL: {success_count}/{len(tests)} systems working")

    if success_count == len(tests):
        print("\nRESULT: Database is populated and core endpoints are reachable.")
    else:
        print("\nRESULT: Some issues detected - check individual components.")

    return 0 if success_count == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
