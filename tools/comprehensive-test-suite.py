#!/usr/bin/env python3
"""
Watch2 Media Server - Comprehensive Test Suite
Targets the Express backend (`watch2/windsurf-project`) and Vue frontend.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests


class Watch2TestSuite:
    def __init__(
        self,
        backend_url: str = "http://localhost:8000",
        frontend_url: str = "http://localhost:3000",
        admin_email: str = "admin@example.com",
        admin_password: str = "AdminPassword123!",
    ) -> None:
        self.backend_url = backend_url.rstrip("/")
        self.frontend_url = frontend_url.rstrip("/")
        self.admin_email = admin_email
        self.admin_password = admin_password
        self.token: Optional[str] = None
        self.user_info: Optional[Dict[str, Any]] = None
        self.test_results: List[Dict[str, Any]] = []

    def log_test(
        self,
        category: str,
        test_name: str,
        status: str,
        details: str = "",
        response_time: float = 0,
    ) -> None:
        result = {
            "timestamp": datetime.now().isoformat(),
            "category": category,
            "test_name": test_name,
            "status": status,
            "details": details,
            "response_time_ms": round(response_time * 1000, 2),
        }
        self.test_results.append(result)

        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} [{category}] {test_name}: {status}")
        if details:
            print(f"   Details: {details}")
        if response_time > 0:
            print(f"   Response Time: {result['response_time_ms']}ms")

    def _require_token(self, category: str) -> bool:
        if not self.token:
            self.log_test(category, "All Tests", "SKIP", "No authentication token")
            return False
        return True

    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def test_service_availability(self) -> None:
        print("\n🔍 Testing Service Availability")
        print("-" * 50)

        try:
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/api/v1/health", timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                status_text = data.get("status", "unknown")
                self.log_test("Service", "Backend Health", "PASS", f"Status: {status_text}", response_time)
            else:
                self.log_test("Service", "Backend Health", "FAIL", f"Status Code: {response.status_code}")
        except Exception as error:  # noqa: BLE001
            self.log_test("Service", "Backend Health", "FAIL", str(error))

        try:
            start_time = time.time()
            response = requests.get(self.frontend_url, timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200:
                self.log_test("Service", "Frontend Availability", "PASS", "Frontend accessible", response_time)
            else:
                self.log_test("Service", "Frontend Availability", "FAIL", f"Status Code: {response.status_code}")
        except Exception as error:  # noqa: BLE001
            self.log_test("Service", "Frontend Availability", "FAIL", str(error))

    def test_authentication_flow(self) -> None:
        print("\n🔐 Testing Authentication Flow")
        print("-" * 50)

        try:
            print(f"DEBUG admin_password repr={self.admin_password!r}")
            start_time = time.time()
            payload = {
                "username": self.admin_email,
                "password": self.admin_password,
            }
            password_hash = hashlib.sha256(self.admin_password.encode()).hexdigest()
            response = requests.post(
                f"{self.backend_url}/api/v1/auth/login/access-token",
                data=payload,
                timeout=10,
            )
            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_info = data.get("user")
                if self.token:
                    self.log_test(
                        "Auth",
                        "Login",
                        "PASS",
                        (
                            f"Token received (length={len(self.token)}). "
                            f"token_preview={self.token[:20]}... user={self.user_info.get('email') if isinstance(self.user_info, dict) else 'unknown'}"
                        ),
                        response_time,
                    )
                else:
                    self.log_test("Auth", "Login", "FAIL", "Missing token or user payload")
                    return
            else:
                self.log_test(
                    "Auth",
                    "Login",
                    "FAIL",
                    (
                        f"Status: {response.status_code}, Response: {response.text}. "
                        f"username={payload['username']} password_hash={password_hash}"
                    ),
                )
                return
        except Exception as error:  # noqa: BLE001
            self.log_test("Auth", "Login", "FAIL", str(error))
            return

        if not self.token:
            return

        try:
            start_time = time.time()
            headers = self._auth_headers()
            response = requests.get(f"{self.backend_url}/api/v1/users/me", headers=headers, timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200:
                payload = response.json()
                self.user_info = payload
                role = "superuser" if payload.get("is_superuser") else "user"
                self.log_test(
                    "Auth",
                    "User Profile",
                    "PASS",
                    f"User: {payload.get('email')} role={role}",
                    response_time,
                )
            else:
                self.log_test("Auth", "User Profile", "FAIL", f"Status Code: {response.status_code}")
        except Exception as error:  # noqa: BLE001
            self.log_test("Auth", "User Profile", "FAIL", str(error))

    def test_media_endpoints(self) -> None:
        print("\n📺 Testing Media Endpoints")
        print("-" * 50)

        if not self._require_token("Media"):
            return

        headers = self._auth_headers()

        try:
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/api/v1/media", headers=headers, timeout=10)
            response_time = time.time() - start_time

            if response.status_code == 200:
                items = response.json().get("items", [])
                self.log_test("Media", "Media List", "PASS", f"Found {len(items)} media items", response_time)
            else:
                self.log_test("Media", "Media List", "FAIL", f"Status Code: {response.status_code}")
        except Exception as error:  # noqa: BLE001
            self.log_test("Media", "Media List", "FAIL", str(error))

        try:
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/api/v1/media/categories", headers=headers, timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200:
                categories_payload = response.json().get("categories", {})
                if isinstance(categories_payload, dict):
                    category_count = len(categories_payload)
                elif isinstance(categories_payload, list):
                    category_count = len(categories_payload)
                else:
                    category_count = 0
                self.log_test("Media", "Categories", "PASS", f"Categories returned: {category_count}", response_time)
            else:
                self.log_test("Media", "Categories", "FAIL", f"Status Code: {response.status_code}")
        except Exception as error:  # noqa: BLE001
            self.log_test("Media", "Categories", "FAIL", str(error))

    def test_playlist_endpoints(self) -> None:
        print("\n📋 Testing Playlist Endpoints")
        print("-" * 50)

        if not self._require_token("Playlist"):
            return

        headers = self._auth_headers()

        try:
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/api/v1/playlists", headers=headers, timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200:
                playlists = response.json().get("playlists", [])
                self.log_test(
                    "Playlist",
                    "List Playlists",
                    "PASS",
                    f"Found {len(playlists)} playlists",
                    response_time,
                )
            else:
                self.log_test("Playlist", "List Playlists", "FAIL", f"Status Code: {response.status_code}")
        except Exception as error:  # noqa: BLE001
            self.log_test("Playlist", "List Playlists", "FAIL", str(error))

    def test_scans_endpoints(self) -> None:
        print("\n🔍 Testing Scan Endpoints")
        print("-" * 50)

        if not self._require_token("Scan"):
            return

        headers = self._auth_headers()

        # Scan info summary (always available)
        try:
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/api/v1/media/scan-info", headers=headers, timeout=10)
            response_time = time.time() - start_time

            if response.status_code == 200:
                info = response.json()
                self.log_test(
                    "Scan",
                    "Scan Info",
                    "PASS",
                    f"Total files: {info.get('library_stats', {}).get('total_media_files', 0)}",
                    response_time,
                )
            else:
                self.log_test("Scan", "Scan Info", "FAIL", f"Status Code: {response.status_code}")
        except Exception as error:  # noqa: BLE001
            self.log_test("Scan", "Scan Info", "FAIL", str(error))

        # Trigger ad-hoc scan (best-effort: treat missing directory as warning)
        try:
            start_time = time.time()
            scan_response = requests.post(
                f"{self.backend_url}/api/v1/media/scan",
                headers=headers,
                json={"directory": "/app/media"},
                timeout=30,
            )
            response_time = time.time() - start_time

            if scan_response.status_code == 200:
                data = scan_response.json()
                self.log_test(
                    "Scan",
                    "Trigger Scan",
                    "PASS",
                    f"Found {data.get('total_found', 0)} items",
                    response_time,
                )
            elif scan_response.status_code == 400:
                detail = scan_response.json().get("detail", "Invalid directory")
                self.log_test(
                    "Scan",
                    "Trigger Scan",
                    "SKIP",
                    f"Scan skipped: {detail}",
                    response_time,
                )
            else:
                self.log_test(
                    "Scan",
                    "Trigger Scan",
                    "FAIL",
                    f"Status Code: {scan_response.status_code}",
                )
        except Exception as error:  # noqa: BLE001
            self.log_test("Scan", "Trigger Scan", "FAIL", str(error))

    def test_settings_endpoints(self) -> None:
        print("\n⚙️ Testing Settings Endpoints")
        print("-" * 50)

        if not self._require_token("Settings"):
            return

        headers = self._auth_headers()

        settings_url = f"{self.backend_url}/api/v1/settings/"

        # Fetch current settings
        try:
            start_time = time.time()
            response = requests.get(settings_url, headers=headers, timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200:
                settings_payload = response.json()
                database_settings = settings_payload.get("database", {})
                self.log_test(
                    "Settings",
                    "Get Settings",
                    "PASS",
                    f"Backup dir: {database_settings.get('backup_directory', '') or '<empty>'}",
                    response_time,
                )
            else:
                self.log_test("Settings", "Get Settings", "FAIL", f"Status Code: {response.status_code}")
                return
        except Exception as error:  # noqa: BLE001
            self.log_test("Settings", "Get Settings", "FAIL", str(error))
            return

        # Update backup directory and verify persistence
        test_directory = "/tmp/watch2-backups"
        try:
            start_time = time.time()
            put_response = requests.put(
                settings_url,
                headers=headers,
                json={"database": {"backup_directory": test_directory}},
                timeout=5,
            )
            response_time = time.time() - start_time

            if put_response.status_code == 200:
                self.log_test(
                    "Settings",
                    "Update Settings",
                    "PASS",
                    f"Set backup directory to {test_directory}",
                    response_time,
                )
            else:
                self.log_test(
                    "Settings",
                    "Update Settings",
                    "FAIL",
                    f"Status Code: {put_response.status_code}"
                )
                return
        except Exception as error:  # noqa: BLE001
            self.log_test("Settings", "Update Settings", "FAIL", str(error))
            return

        try:
            response = requests.get(settings_url, headers=headers, timeout=5)
            if response.status_code == 200:
                updated_settings = response.json().get("database", {})
                if updated_settings.get("backup_directory") == test_directory:
                    self.log_test("Settings", "Verify Persistence", "PASS", "backup_directory persisted")
                else:
                    self.log_test(
                        "Settings",
                        "Verify Persistence",
                        "FAIL",
                        f"Unexpected backup_directory: {updated_settings.get('backup_directory')}"
                    )
            else:
                self.log_test("Settings", "Verify Persistence", "FAIL", f"Status Code: {response.status_code}")
        except Exception as error:  # noqa: BLE001
            self.log_test("Settings", "Verify Persistence", "FAIL", str(error))

    def test_backup_endpoints(self) -> None:
        print("\n💾 Testing Backup Endpoints")
        print("-" * 50)

        if not self._require_token("Backups"):
            return

        headers = self._auth_headers()

        try:
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/api/v1/admin/database/backups", headers=headers, timeout=10)
            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                directory = data.get("directory", "")
                item_count = len(data.get("items", []))
                self.log_test(
                    "Backups",
                    "List Backups",
                    "PASS",
                    f"Directory: {directory or '<unset>'}, items: {item_count}",
                    response_time,
                )
            else:
                self.log_test("Backups", "List Backups", "FAIL", f"Status Code: {response.status_code}")
        except Exception as error:  # noqa: BLE001
            self.log_test("Backups", "List Backups", "FAIL", str(error))

    def test_analytics_endpoints(self) -> None:
        print("\n📊 Testing Analytics Endpoints")
        print("-" * 50)

        if not self._require_token("Analytics"):
            return

        headers = self._auth_headers()

        try:
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/api/v1/analytics/dashboard", headers=headers, timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                total_media = data.get("total_media_files", 0)
                total_playlists = data.get("total_playlists", 0)
                self.log_test(
                    "Analytics",
                    "Dashboard",
                    "PASS",
                    f"Media: {total_media}, Playlists: {total_playlists}",
                    response_time,
                )
            else:
                self.log_test("Analytics", "Dashboard", "FAIL", f"Status Code: {response.status_code}")
        except Exception as error:  # noqa: BLE001
            self.log_test("Analytics", "Dashboard", "FAIL", str(error))

    def test_system_endpoints(self) -> None:
        print("\n��️ Testing System Endpoints")
        print("-" * 50)

        try:
            start_time = time.time()
            response = requests.get(f"{self.backend_url}/api/v1/system/version", timeout=5)
            response_time = time.time() - start_time

            if response.status_code == 200:
                response_data = response.json()
                version = response_data.get("api_version") or response_data.get("version") or "unknown"
                self.log_test(
                    "System",
                    "Version Info",
                    "PASS",
                    f"API Version: {version}",
                    response_time,
                )
            else:
                self.log_test("System", "Version Info", "FAIL", f"Status Code: {response.status_code}")
        except Exception as error:  # noqa: BLE001
            self.log_test("System", "Version Info", "FAIL", str(error))

    def generate_report(self) -> bool:
        print("\n" + "=" * 60)
        print("📋 COMPREHENSIVE TEST REPORT")
        print("=" * 60)

        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        skipped_tests = len([r for r in self.test_results if r["status"] == "SKIP"])
        success_rate = (passed_tests / total_tests * 100) if total_tests else 0

        print(f"🎯 Success Rate: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️ Skipped: {skipped_tests}")

        categories: Dict[str, Dict[str, int]] = {}
        for result in self.test_results:
            category = result["category"]
            categories.setdefault(category, {"pass": 0, "fail": 0, "skip": 0})
            categories[category][result["status"].lower()] += 1

        print("\n📊 Results by Category:")
        for category, stats in categories.items():
            total_cat = sum(stats.values())
            pass_rate = (stats["pass"] / total_cat * 100) if total_cat else 0
            print(f"   {category}: {stats['pass']}/{total_cat} ({pass_rate:.1f}%) ✅{stats['pass']} ❌{stats['fail']} ⚠️{stats['skip']}")

        response_times = [r["response_time_ms"] for r in self.test_results if r["response_time_ms"] > 0]
        avg_response = sum(response_times) / len(response_times) if response_times else 0
        max_response = max(response_times) if response_times else 0
        if response_times:
            print("\n⚡ Performance:")
            print(f"   Average Response Time: {avg_response:.1f}ms")
            print(f"   Slowest Response: {max_response:.1f}ms")

        failed_results = [r for r in self.test_results if r["status"] == "FAIL"]
        if failed_results:
            print("\n❌ Failed Tests Details:")
            for result in failed_results:
                print(f"   [{result['category']}] {result['test_name']}: {result['details']}")

        print(f"\n🕒 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "skipped": skipped_tests,
                "success_rate": success_rate,
            },
            "categories": categories,
            "performance": {
                "avg_response_ms": avg_response,
                "max_response_ms": max_response,
            },
            "detailed_results": self.test_results,
        }

        with open("test-report.json", "w", encoding="utf-8") as handle:
            json.dump(report_data, handle, indent=2)

        print("\n💾 Detailed report saved to: test-report.json")
        return success_rate >= 90

    def run_all_tests(self) -> bool:
        print("🧪 Watch2 Media Server - Comprehensive Test Suite")
        print("=" * 60)
        print(f"Backend URL: {self.backend_url}")
        print(f"Frontend URL: {self.frontend_url}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        self.test_service_availability()
        self.test_authentication_flow()
        self.test_media_endpoints()
        self.test_playlist_endpoints()
        self.test_scans_endpoints()
        self.test_settings_endpoints()
        self.test_analytics_endpoints()
        self.test_system_endpoints()

        return self.generate_report()


def main() -> None:
    if len(sys.argv) > 1:
        backend_url = sys.argv[1]
        frontend_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:3000"
    else:
        backend_url = "http://localhost:8000"
        frontend_url = "http://localhost:3000"

    admin_email = os.environ.get("WATCH2_ADMIN_EMAIL", "admin@example.com")
    admin_password = os.environ.get("WATCH2_ADMIN_PASSWORD", "AdminPassword123!")

    suite = Watch2TestSuite(backend_url, frontend_url, admin_email, admin_password)
    suite.run_all_tests()
    sys.exit(0)


if __name__ == "__main__":
    main()
