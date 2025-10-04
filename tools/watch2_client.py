#!/usr/bin/env python3
"""Shared Watch2 API client utilities for tooling scripts."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

DEFAULT_BACKEND_URL = os.getenv("WATCH2_BACKEND_URL", "http://localhost:8000").rstrip("/")
DEFAULT_FRONTEND_URL = os.getenv("WATCH2_FRONTEND_URL", "http://localhost:3000").rstrip("/")
DEFAULT_EMAIL = os.getenv("WATCH2_ADMIN_EMAIL", "admin@example.com")
DEFAULT_PASSWORD = os.getenv("WATCH2_ADMIN_PASSWORD", "AdminPassword123!")
DEFAULT_TIMEOUT = float(os.getenv("WATCH2_HTTP_TIMEOUT", "15"))


class Watch2ClientError(RuntimeError):
    """Raised when the Watch2 client encounters an unrecoverable error."""


@dataclass(slots=True)
class Watch2Client:
    backend_url: str = DEFAULT_BACKEND_URL
    frontend_url: str = DEFAULT_FRONTEND_URL
    email: str = DEFAULT_EMAIL
    password: str = DEFAULT_PASSWORD
    timeout: float = DEFAULT_TIMEOUT

    _token: Optional[str] = None
    _session: requests.Session | None = None

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def auth_headers(self) -> Dict[str, str]:
        if not self._token:
            raise Watch2ClientError("Client not authenticated; call login() first")
        return {"Authorization": f"Bearer {self._token}"}

    def login(self) -> Dict[str, Any]:
        """Authenticate with the Watch2 backend and cache the access token."""
        payload = {"email": self.email, "password": self.password}
        response = self.session.post(
            f"{self.backend_url}/auth/login",
            json=payload,
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise Watch2ClientError(
                f"Login failed ({response.status_code}): {response.text.strip()}"
            )

        data = response.json()
        token = data.get("accessToken")
        if not token:
            raise Watch2ClientError("Authentication succeeded but accessToken missing")

        self._token = token
        return data

    def ensure_login(self) -> Dict[str, Any]:
        if self._token:
            return {"accessToken": self._token}
        return self.login()

    def get(self, path: str, *, auth: bool = False, **kwargs: Any) -> requests.Response:
        url = self._join(path)
        headers = kwargs.pop("headers", {})
        if auth:
            headers = {**headers, **self.auth_headers()}
        return self.session.get(url, headers=headers, timeout=self.timeout, **kwargs)

    def post(self, path: str, *, auth: bool = False, **kwargs: Any) -> requests.Response:
        url = self._join(path)
        headers = kwargs.pop("headers", {})
        if auth:
            headers = {**headers, **self.auth_headers()}
        return self.session.post(url, headers=headers, timeout=self.timeout, **kwargs)

    def status(self) -> Dict[str, Any]:
        response = self.get("/status")
        response.raise_for_status()
        return response.json()

    def system_version(self) -> Dict[str, Any]:
        response = self.get("/system/version")
        response.raise_for_status()
        return response.json()

    def scans_summary(self) -> Dict[str, Any]:
        response = self.get("/scans/summary", auth=True)
        response.raise_for_status()
        return response.json()

    def start_scan(self, *, directories: Optional[list[str]] = None) -> Dict[str, Any]:
        payload = {"directories": directories} if directories else {}
        response = self.post("/scans/start", json=payload, auth=True)
        response.raise_for_status()
        return response.json()

    def wait_for_frontend(self, timeout: float | None = None) -> bool:
        """Poll the frontend until it returns HTTP 200 or timeout is reached."""
        timeout = timeout or self.timeout
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                response = self.session.get(self.frontend_url, timeout=5)
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                time.sleep(0.5)
                continue
        return False

    def _join(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.backend_url}{path}"


def create_client(**overrides: Any) -> Watch2Client:
    """Factory helper that respects environment defaults and caller overrides."""
    return Watch2Client(**overrides)
