#!/usr/bin/env python3
"""Watch2 system status summary."""

from __future__ import annotations

import sys
from datetime import datetime
from typing import Any

import requests

from watch2_client import Watch2Client, Watch2ClientError, create_client


def get_system_status(client: Watch2Client) -> bool:
    print("WATCH2 SYSTEM STATUS SUMMARY")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        client.ensure_login()
        print(f"✅ Authentication: WORKING (user={client.email})")
    except Watch2ClientError as error:
        print(f"❌ Authentication: FAILED ({error})")
        return False

    health_ok = check_backend_health(client)
    media_ok = summarize_media(client)
    analytics_ok = summarize_analytics(client)
    playlists_ok = summarize_playlists(client)
    frontend_ok = client.wait_for_frontend(timeout=5)

    print(f"✅ Frontend: {'ACCESSIBLE' if frontend_ok else 'NOT ACCESSIBLE'}")

    working = sum(
        1 for value in [health_ok, media_ok, analytics_ok, playlists_ok, frontend_ok] if value
    )
    total = 5
    print(f"✅ API Endpoints: {working}/{total} key checks passing")

    print("\n" + "=" * 50)
    print("QUICK ACCESS:")
    print(f"Frontend: {client.frontend_url}")
    print(f"Backend API: {client.backend_url}")
    print(f"Login: {client.email} / ****")

    return working == total


def check_backend_health(client: Watch2Client) -> bool:
    try:
        status = client.status()
        api_version = status.get("version") or status.get("apiVersion")
        print(f"✅ Backend status: OK (version {api_version})")
        return True
    except requests.RequestException as error:
        print(f"❌ Backend status: {error}")
        return False


def summarize_media(client: Watch2Client) -> bool:
    try:
        response = client.get("/media", auth=True)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items", [])
        print(f"✅ Media: {len(items)} items in library")

        categories_resp = client.get("/media/categories", auth=True)
        categories_resp.raise_for_status()
        categories = categories_resp.json().get("categories", [])
        if categories:
            print("   Categories:")
            for category in categories[:5]:
                name = category.get("name", "unknown")
                count = category.get("count", 0)
                print(f"    - {name}: {count}")
        return True
    except requests.RequestException as error:
        print(f"❌ Media: {error}")
        return False


def summarize_analytics(client: Watch2Client) -> bool:
    try:
        response = client.get("/analytics/dashboard", auth=True)
        response.raise_for_status()
        payload = response.json()
        totals: dict[str, Any] = payload.get("totals", {})
        print("✅ Analytics: Dashboard reachable")
        print(f"   Media items: {totals.get('mediaItems', 0)}")
        print(f"   Scan jobs: {totals.get('totalScanJobs', 0)}")
        return True
    except requests.RequestException as error:
        print(f"❌ Analytics: {error}")
        return False


def summarize_playlists(client: Watch2Client) -> bool:
    try:
        response = client.get("/playlists", auth=True)
        response.raise_for_status()
        payload = response.json()
        playlists = payload.get("playlists", [])
        print(f"✅ Playlists: {len(playlists)} available")
        return True
    except requests.RequestException as error:
        print(f"❌ Playlists: {error}")
        return False


def main() -> int:
    client = create_client()
    success = get_system_status(client)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
