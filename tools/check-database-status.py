#!/usr/bin/env python3
"""Watch2 database status checker."""

from __future__ import annotations

import sys
from typing import Any, Dict

import requests

from watch2_client import Watch2Client, Watch2ClientError, create_client


def check_media(client: Watch2Client) -> bool:
    print("\nCHECKING MEDIA API ENDPOINTS")
    print("============================")

    try:
        response = client.get("/media", auth=True)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        print(f"ERROR: Media list failed: {error}")
        return False

    items = payload.get("items", [])
    print(f"SUCCESS: Media list returned {len(items)} items")

    if items:
        print("  Sample items:")
        for index, item in enumerate(items[:5], start=1):
            title = item.get("title") or item.get("name") or item.get("id")
            status = item.get("status", "unknown")
            print(f"   {index}. {title} [status={status}]")

    try:
        categories_response = client.get("/media/categories", auth=True)
        categories_response.raise_for_status()
        categories_payload = categories_response.json()
        categories = categories_payload.get("categories", [])
        print(f"SUCCESS: Categories endpoint returned {len(categories)} entries")
    except requests.RequestException as error:
        print(f"ERROR: Categories endpoint failed: {error}")
        return False

    return True


def check_playlists(client: Watch2Client) -> bool:
    try:
        response = client.get("/playlists", auth=True)
        response.raise_for_status()
        payload = response.json()
        playlists = payload.get("playlists", [])
        print(f"SUCCESS: Playlists endpoint returned {len(playlists)} playlists")

        for playlist in playlists[:3]:
            print(f"  - {playlist.get('name', 'Unnamed')} (public={playlist.get('isPublic')})")
        return True
    except requests.RequestException as error:
        print(f"ERROR: Playlists endpoint failed: {error}")
        return False


def check_settings(client: Watch2Client) -> bool:
    try:
        response = client.get("/settings", auth=True)
        response.raise_for_status()
        payload = response.json()
        settings = payload.get("settings", {})
        print(f"SUCCESS: Settings endpoint returned {len(settings)} top-level keys")
        return True
    except requests.RequestException as error:
        print(f"ERROR: Settings endpoint failed: {error}")
        return False


def check_analytics(client: Watch2Client) -> bool:
    try:
        response = client.get("/analytics/dashboard", auth=True)
        response.raise_for_status()
        payload = response.json()
        totals: Dict[str, Any] = payload.get("totals", {})
        print("SUCCESS: Analytics dashboard available")
        print(f"  Media items: {totals.get('mediaItems', 0)}")
        print(f"  Total scan jobs: {totals.get('totalScanJobs', 0)}")
        return True
    except requests.RequestException as error:
        print(f"ERROR: Analytics endpoint failed: {error}")
        return False


def check_frontend(client: Watch2Client) -> bool:
    if client.wait_for_frontend(timeout=10):
        print(f"SUCCESS: Frontend accessible at {client.frontend_url}")
        return True

    print("ERROR: Frontend not reachable within timeout")
    return False


def run_comprehensive_check(client: Watch2Client) -> bool:
    print("DATABASE STATUS CHECKER")
    print("=======================")

    try:
        client.ensure_login()
        print("Authenticated as", client.email)
    except Watch2ClientError as error:
        print(f"ERROR: Authentication failed: {error}")
        return False

    results = {
        "media_api": check_media(client),
        "playlists_api": check_playlists(client),
        "settings_api": check_settings(client),
        "analytics_api": check_analytics(client),
        "frontend": check_frontend(client),
    }

    print("\n" + "=" * 50)
    print("DATABASE STATUS SUMMARY")
    print("=" * 50)

    success_count = sum(1 for result in results.values() if result)
    for name, result in results.items():
        status = "SUCCESS" if result else "FAILED"
        indicator = "[OK]" if result else "[FAIL]"
        print(f"{name:15} | {status:7} | {indicator}")

    total = len(results)
    print(f"\nOVERALL STATUS: {success_count}/{total} checks passed")

    if success_count == total:
        print("SUCCESS: Database is populated and core endpoints are reachable")
        return True

    print("WARNING: Some database or API issues detected")
    return False


def main() -> int:
    client = create_client()
    success = run_comprehensive_check(client)

    if success:
        print("\nRESULT: Database and views are working correctly!")
        return 0

    print("\nRESULT: Some issues detected - inspect the failing endpoints above")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
