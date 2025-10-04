#!/usr/bin/env python3
"""Enhanced Watch2 storage format verification suite."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from watch2_client import Watch2Client, Watch2ClientError, create_client


class EnhancedStorageTestSuite:
    """Exercise Watch2 storage-related endpoints and summarise findings."""

    def __init__(self, client: Optional[Watch2Client] = None) -> None:
        self.client = client or create_client()
        self.results: List[Dict[str, Any]] = []
        self._authenticated = False

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------
    def log_test(
        self,
        category: str,
        test_name: str,
        status: str,
        details: str = "",
        response_time: float = 0,
    ) -> None:
        icon_map = {
            "PASS": "✅",
            "FAIL": "❌",
            "WARN": "⚠️",
            "SKIP": "⚠️",
            "INFO": "ℹ️",
        }
        entry = {
            "category": category,
            "test": test_name,
            "status": status,
            "details": details,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat(),
        }
        self.results.append(entry)

        badge = icon_map.get(status.upper(), "•")
        print(f"{badge} [{category}] {test_name}: {status}")
        if details:
            print(f"   Details: {details}")
        if response_time:
            print(f"   Response Time: {response_time:.2f}ms")

    def _ensure_auth(self) -> bool:
        if self._authenticated:
            return True

        try:
            start = time.time()
            self.client.ensure_login()
            elapsed = (time.time() - start) * 1000
            self._authenticated = True
            self.log_test(
                "Auth",
                "Authenticate",
                "PASS",
                f"Logged in as {self.client.email}",
                elapsed,
            )
            return True
        except Watch2ClientError as error:
            self.log_test("Auth", "Authenticate", "FAIL", str(error))
            return False

    # ------------------------------------------------------------------
    # Core checks
    # ------------------------------------------------------------------
    def test_frontend_accessibility(self) -> bool:
        print("\n🌐 Testing Frontend Accessibility")
        print("-" * 50)

        start = time.time()
        reachable = self.client.wait_for_frontend(timeout=10)
        elapsed = (time.time() - start) * 1000

        if reachable:
            self.log_test(
                "Frontend",
                "Accessibility",
                "PASS",
                f"Frontend reachable at {self.client.frontend_url}",
                elapsed,
            )
            return True

        self.log_test(
            "Frontend",
            "Accessibility",
            "FAIL",
            f"Frontend not reachable at {self.client.frontend_url}",
            elapsed,
        )
        return False

    def test_api_matrix(self) -> bool:
        print("\n🔗 Testing API Endpoint Matrix")
        print("-" * 50)

        endpoints = [
            ("/status", "Status", False),
            ("/system/version", "System Version", False),
            ("/media", "Media", True),
            ("/media/categories", "Media Categories", True),
            ("/playlists", "Playlists", True),
            ("/settings", "Settings", True),
            ("/analytics/dashboard", "Analytics Dashboard", True),
        ]

        working = 0
        for path, name, auth in endpoints:
            try:
                start = time.time()
                response = self.client.get(path, auth=auth)
                elapsed = (time.time() - start) * 1000
                response.raise_for_status()
                working += 1
                self.log_test("API", name, "PASS", f"HTTP {response.status_code}", elapsed)
            except requests.RequestException as error:
                self.log_test("API", name, "FAIL", str(error))

        self.log_test(
            "API",
            "Summary",
            "PASS" if working == len(endpoints) else "WARN",
            f"{working}/{len(endpoints)} endpoints reachable",
        )
        return working == len(endpoints)

    def test_scan_trigger(self) -> bool:
        print("\n🌀 Testing Scan Trigger")
        print("-" * 50)

        if not self._ensure_auth():
            self.log_test("Scans", "Trigger", "SKIP", "Authentication unavailable")
            return False

        try:
            start = time.time()
            response = self.client.start_scan()
            elapsed = (time.time() - start) * 1000
            job = response.get("job", {})
            self.log_test(
                "Scans",
                "Trigger",
                "PASS",
                f"Job {job.get('id', 'unknown')} status {job.get('status', 'queued')}",
                elapsed,
            )
            return True
        except requests.RequestException as error:
            self.log_test("Scans", "Trigger", "FAIL", str(error))
            return False

    def test_storage_formats(self) -> bool:
        print("\n📊 Testing Storage Format Coverage")
        print("-" * 50)

        if not self._ensure_auth():
            self.log_test("Storage", "Categories", "SKIP", "Authentication unavailable")
            return False

        try:
            start = time.time()
            response = self.client.get("/media/categories", auth=True)
            elapsed = (time.time() - start) * 1000
            response.raise_for_status()
            categories = response.json().get("categories", [])
            if not categories:
                self.log_test("Storage", "Categories", "WARN", "No categories reported", elapsed)
                return False

            formats: Dict[str, List[Dict[str, Any]]] = {"collection": [], "series": [], "group": []}
            for category in categories:
                format_name = (category.get("storageFormat") or category.get("format") or "").lower()
                if format_name in formats:
                    formats[format_name].append(category)

            success = True
            for format_name, items in formats.items():
                if items:
                    total = sum(item.get("count", 0) for item in items)
                    details = ", ".join(f"{item.get('name', 'unknown')}({item.get('count', 0)})" for item in items)
                    self.log_test(
                        "Storage",
                        f"{format_name.title()} Format",
                        "PASS",
                        f"Categories: {details} | Total items: {total}",
                    )
                else:
                    self.log_test(
                        "Storage",
                        f"{format_name.title()} Format",
                        "WARN",
                        "No categories detected for this format",
                    )
                    success = False

            self.log_test(
                "Storage",
                "Categories",
                "PASS" if success else "WARN",
                f"Analysed {len(categories)} categories",
                elapsed,
            )
            return success
        except requests.RequestException as error:
            self.log_test("Storage", "Categories", "FAIL", str(error))
            return False

    def test_media_catalog(self) -> bool:
        print("\n🗂️ Testing Media Catalogue")
        print("-" * 50)

        if not self._ensure_auth():
            self.log_test("Media", "Catalogue", "SKIP", "Authentication unavailable")
            return False

        try:
            start = time.time()
            response = self.client.get("/media", params={"limit": 100}, auth=True)
            elapsed = (time.time() - start) * 1000
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items", [])
            total = payload.get("total", len(items))

            if items:
                self.log_test(
                    "Media",
                    "Catalogue",
                    "PASS",
                    f"Fetched {len(items)} sample items (reported total {total})",
                    elapsed,
                )
            else:
                self.log_test(
                    "Media",
                    "Catalogue",
                    "FAIL",
                    "No media items returned",
                    elapsed,
                )
                return False

            typed_counts: Dict[str, int] = {}
            for item in items:
                item_type = item.get("type", item.get("status", "unknown"))
                typed_counts[item_type] = typed_counts.get(item_type, 0) + 1

            details = ", ".join(f"{key}:{value}" for key, value in typed_counts.items())
            self.log_test("Media", "Type Breakdown", "INFO", details)

            metadata_rich = [item for item in items if item.get("releaseYear") or item.get("tags")]
            self.log_test(
                "Media",
                "Metadata",
                "PASS" if metadata_rich else "WARN",
                f"Items with enhanced metadata: {len(metadata_rich)}",
            )
            return True
        except requests.RequestException as error:
            self.log_test("Media", "Catalogue", "FAIL", str(error))
            return False

    def test_settings(self) -> bool:
        print("\n⚙️ Testing Configuration Settings")
        print("-" * 50)

        if not self._ensure_auth():
            self.log_test("Config", "Settings", "SKIP", "Authentication unavailable")
            return False

        try:
            start = time.time()
            response = self.client.get("/settings", auth=True)
            elapsed = (time.time() - start) * 1000
            response.raise_for_status()
            settings = response.json().get("settings", {})
            media_dirs = settings.get("mediaDirectories", [])

            self.log_test(
                "Config",
                "Media Directories",
                "PASS" if media_dirs else "WARN",
                f"Configured directories: {len(media_dirs)}",
                elapsed,
            )

            t_drive_dirs = [path for path in media_dirs if "T:" in path or "/app/T/" in path]
            if t_drive_dirs:
                self.log_test(
                    "Config",
                    "T-Drive Directories",
                    "PASS",
                    ", ".join(t_drive_dirs),
                )
            else:
                self.log_test(
                    "Config",
                    "T-Drive Directories",
                    "WARN",
                    "No T: drive directories configured",
                )
            return bool(media_dirs)
        except requests.RequestException as error:
            self.log_test("Config", "Media Directories", "FAIL", str(error))
            return False

    def record_follow_up(self) -> None:
        self.log_test(
            "Follow-up",
            "Deferred Enhancements",
            "INFO",
            "Restore detailed benchmark/performance assertions in a future iteration.",
        )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def generate_report(self) -> bool:
        print(f"\n{'=' * 80}")
        print("📋 ENHANCED STORAGE FORMAT TEST REPORT")
        print(f"{'=' * 80}")

        total = len(self.results)
        passed = len([r for r in self.results if r["status"] == "PASS"])
        failed = len([r for r in self.results if r["status"] == "FAIL"])
        skipped = len([r for r in self.results if r["status"] == "SKIP"])
        success_rate = (passed / total * 100) if total else 0

        print(f"🕒 Test Duration: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Success Rate: {passed}/{total} ({success_rate:.1f}%)")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️ Skipped: {skipped}")

        categories: Dict[str, Dict[str, int]] = {}
        for result in self.results:
            bucket = categories.setdefault(
                result["category"], {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0, "INFO": 0}
            )
            status = result["status"].upper()
            bucket[status] = bucket.get(status, 0) + 1

        print("\n📊 Results by Category:")
        for category, counts in categories.items():
            total_in_category = sum(counts.values())
            pass_rate = (counts["PASS"] / total_in_category * 100) if total_in_category else 0
            print(
                f"   {category}: {counts['PASS']}/{total_in_category} ({pass_rate:.1f}%) "
                f"✅{counts['PASS']} ❌{counts['FAIL']} ⚠️{counts['SKIP']} ℹ️{counts['INFO']}"
            )

        failed_results = [r for r in self.results if r["status"] == "FAIL"]
        if failed_results:
            print("\n❌ Failed Tests Details:")
            for result in failed_results:
                print(f"   [{result['category']}] {result['test']}: {result['details']}")

        response_times = [r["response_time"] for r in self.results if r["response_time"] > 0]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            print("\n⚡ Performance:")
            print(f"   Average Response Time: {avg_time:.1f}ms")
            print(f"   Slowest Response: {max_time:.1f}ms")

        report = {
            "timestamp": datetime.now().isoformat(),
            "backend_url": self.client.backend_url,
            "frontend_url": self.client.frontend_url,
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "success_rate": success_rate,
            },
            "results": self.results,
        }

        with open("enhanced-storage-test-report.json", "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2)

        print("\n💾 Detailed report saved to: enhanced-storage-test-report.json")
        print(f"🕒 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return success_rate >= 80

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------
    def run_all_tests(self) -> bool:
        print("🧪 Enhanced Watch2 Storage Format Test Suite")
        print("=" * 80)
        print(f"Backend URL: {self.client.backend_url}")
        print(f"Frontend URL: {self.client.frontend_url}")
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not self._ensure_auth():
            print("❌ Authentication failed. Cannot proceed with tests.")
            return False

        self.test_frontend_accessibility()
        self.test_api_matrix()
        self.test_scan_trigger()
        self.test_storage_formats()
        self.test_media_catalog()
        self.test_settings()
        self.record_follow_up()

        return self.generate_report()


def main() -> int:
    overrides: Dict[str, Any] = {}
    if len(sys.argv) > 1:
        overrides["backend_url"] = sys.argv[1].rstrip("/")
    if len(sys.argv) > 2:
        overrides["frontend_url"] = sys.argv[2].rstrip("/")

    suite = EnhancedStorageTestSuite(client=create_client(**overrides))
    success = suite.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
