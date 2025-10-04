#!/usr/bin/env python3
"""Basic Watch2 API tester."""

from __future__ import annotations

from typing import Callable

import requests

from watch2_client import Watch2Client, Watch2ClientError, create_client


def test_api(client: Watch2Client) -> bool:
    tests: list[tuple[str, Callable[[], requests.Response]]] = [
        ("Status", lambda: client.get("/status")),
        ("System Version", client.system_version),
        ("Auth Login", lambda: client.post("/auth/login", json={"email": client.email, "password": client.password})),
    ]

    passed = 0

    for name, request_fn in tests:
        try:
            response = request_fn()
            if isinstance(response, dict):
                print(f"✅ {name}: PASS")
                passed += 1
                continue

            response.raise_for_status()
            print(f"✅ {name}: HTTP {response.status_code}")
            passed += 1
        except Watch2ClientError as error:
            print(f"❌ {name}: {error}")
        except requests.HTTPError as error:
            print(f"❌ {name}: HTTP {error.response.status_code}")
        except requests.RequestException as error:
            print(f"❌ {name}: {error}")

    print(f"\nResults: {passed}/{len(tests)} tests passed")
    return passed == len(tests)


def main() -> int:
    client = create_client()
    client.ensure_login()

    if test_api(client):
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
