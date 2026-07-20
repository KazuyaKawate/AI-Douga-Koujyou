"""Phase 8 Google Workspace connection diagnostics.

This module is deliberately read-only.  It can authenticate and make minimal
metadata requests, but it never creates, updates, sends, uploads, or deletes
anything.  Missing credentials stop the check with ``認証情報が必要です``.
"""
from __future__ import annotations

import importlib.metadata
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any, Callable

from src.utils.config import PROJECT_ROOT


CONFIG_NAME = "google_workspace.json"
AUTH_MODES = {"disabled", "service_account", "oauth"}
SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
)
WORKSPACE_SCOPES = SCOPES + (
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
)
PHASE102_SCOPES = (
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
)
AUTH_REQUIRED = "認証情報が必要です"


class GoogleWorkspaceManager:
    """Load unified settings and run explicitly requested read-only checks."""

    def __init__(
        self,
        *,
        root: str | Path = PROJECT_ROOT,
        config_path: str | Path | None = None,
        credentials_factory: Callable[[dict[str, Any]], Any] | None = None,
        service_builder: Callable[..., Any] | None = None,
        timeout_seconds: float = 10.0,
        retry_attempts: int = 3,
        retry_backoff_seconds: float = 0.25,
    ) -> None:
        self.root = Path(root)
        self.config_path = Path(config_path) if config_path else self.root / "config" / CONFIG_NAME
        self._credentials_factory = credentials_factory
        self._service_builder = service_builder
        self.timeout_seconds = max(0.1, float(timeout_seconds))
        self.retry_attempts = max(1, int(retry_attempts))
        self.retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))

    def load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {}
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            config = dict(data) if isinstance(data, dict) else {}
            return self._apply_environment(config)
        except (OSError, ValueError, TypeError):
            return {}

    @staticmethod
    def _apply_environment(config: dict[str, Any]) -> dict[str, Any]:
        """Overlay secrets and account identifiers from the process environment only."""
        auth = config.setdefault("auth", {})
        services = config.setdefault("services", {})
        env_map = {
            "AIOS_GOOGLE_AUTH_MODE": (auth, "mode"),
            "AIOS_GOOGLE_SERVICE_ACCOUNT_FILE": (auth, "service_account_file"),
            "AIOS_GOOGLE_OAUTH_CLIENT_FILE": (auth, "oauth_client_file"),
            "AIOS_GOOGLE_OAUTH_TOKEN_FILE": (auth, "oauth_token_file"),
            "AIOS_GOOGLE_DELEGATED_USER": (auth, "delegated_user"),
        }
        for env_name, (target, key) in env_map.items():
            if os.environ.get(env_name):
                target[key] = os.environ[env_name]
        if os.environ.get("AIOS_GOOGLE_SPREADSHEET_ID"):
            services.setdefault("sheets", {})["spreadsheet_id"] = os.environ["AIOS_GOOGLE_SPREADSHEET_ID"]
        if os.environ.get("AIOS_GOOGLE_ENABLED"):
            config["enabled"] = os.environ["AIOS_GOOGLE_ENABLED"].strip().lower() == "true"
        return config

    @staticmethod
    def dependency_status() -> dict[str, Any]:
        packages = ("google-auth", "google-auth-oauthlib", "google-api-python-client")
        versions: dict[str, str] = {}
        missing: list[str] = []
        for package in packages:
            try:
                versions[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                missing.append(package)
        return {
            "ready": not missing,
            "missing": missing,
            "versions": versions,
            "install_hint": "pip install google-auth google-auth-oauthlib google-api-python-client" if missing else "",
        }

    def configuration_status(self) -> dict[str, Any]:
        config = self.load_config()
        errors = self._validate(config)
        auth = config.get("auth", {}) if isinstance(config.get("auth"), dict) else {}
        mode = str(auth.get("mode", "disabled"))
        credential_path = self._credential_path(config)
        has_credentials = bool(credential_path and credential_path.exists())
        oauth_client_path = self._auth_path(config, "oauth_client_file")
        enabled = config.get("enabled") is True

        if not config:
            status, label = "config_missing", f"設定ファイルが必要です: config/{CONFIG_NAME}"
        elif errors:
            status, label = "invalid_config", errors[0]
        elif not enabled or mode == "disabled":
            status, label = "auth_required", AUTH_REQUIRED
        elif not has_credentials:
            status, label = "auth_required", AUTH_REQUIRED
        else:
            status, label = "configured", "接続確認可能"
        services = config.get("services", {}) if isinstance(config.get("services"), dict) else {}
        return {
            "status": status,
            "label": label,
            "enabled": enabled,
            "auth_mode": mode,
            "has_credentials": has_credentials,
            "has_oauth_client": bool(oauth_client_path and oauth_client_path.exists()),
            "config_path": f"config/{CONFIG_NAME}",
            "services": {name: bool((services.get(name) or {}).get("enabled", False)) for name in ("sheets", "drive", "docs", "gmail", "calendar")},
            "local_first": config.get("local_first") is True,
            "dry_run": True,
            "review_required": True,
            "approval_required": True,
            "execute_allowed": False,
            "production_actions_enabled": False,
            "errors": errors,
            "dependencies": self.dependency_status(),
        }

    def check_connections(self, *, dry_run: bool = True) -> dict[str, Any]:
        """Run minimal read-only API requests. Non-DryRun is always rejected."""
        if dry_run is not True:
            raise ValueError("Google Workspace接続確認はDryRun必須です。")
        config = self.load_config()
        status = self.configuration_status()
        if status["status"] != "configured":
            return self._result(status, {}, ok=False)
        deps = status["dependencies"]
        if not deps["ready"]:
            blocked = {name: self._service_result("dependencies_missing", "必要ライブラリが不足しています") for name in self._enabled_services(config)}
            return self._result(status, blocked, ok=False)

        try:
            credentials = self._credentials_factory(config) if self._credentials_factory else self._build_credentials(config)
        except Exception as exc:
            blocked = {name: self._service_result("auth_error", f"認証エラー: {type(exc).__name__}") for name in self._enabled_services(config)}
            return self._result(status, blocked, ok=False)

        results: dict[str, dict[str, Any]] = {}
        for name in self._enabled_services(config):
            try:
                results[name] = self._check_service(name, config, credentials)
            except Exception as exc:
                results[name] = self._service_result("connection_error", f"接続エラー: {type(exc).__name__}: {exc}")
        return self._result(status, results, ok=bool(results) and all(row["ok"] for row in results.values()))

    def _build_credentials(self, config: dict[str, Any]) -> Any:
        auth = config["auth"]
        mode = auth["mode"]
        path = self._credential_path(config)
        if path is None or not path.exists():
            raise FileNotFoundError(AUTH_REQUIRED)
        if mode == "service_account":
            from google.oauth2.service_account import Credentials

            credentials = Credentials.from_service_account_file(str(path), scopes=list(WORKSPACE_SCOPES))
            delegated_user = str(auth.get("delegated_user", "")).strip()
            return credentials.with_subject(delegated_user) if delegated_user else credentials
        if mode == "oauth":
            from google.oauth2.credentials import Credentials

            credentials = Credentials.from_authorized_user_file(str(path), scopes=list(PHASE102_SCOPES))
            if credentials.expired and credentials.refresh_token:
                from google.auth.transport.requests import Request
                credentials.refresh(Request())
                save_path = self._credential_path(config)
                if save_path:
                    from src.utils.json_store import save_json_atomic
                    save_json_atomic(save_path, json.loads(credentials.to_json()))
            return credentials
        raise ValueError(AUTH_REQUIRED)

    def _check_service(self, name: str, config: dict[str, Any], credentials: Any) -> dict[str, Any]:
        build = self._service_builder
        if build is None:
            from googleapiclient.discovery import build
        if name == "sheets":
            spreadsheet_id = str(config["services"]["sheets"].get("spreadsheet_id", "")).strip()
            if not spreadsheet_id:
                drive = build("drive", "v3", credentials=credentials, cache_discovery=False)
                found = self._execute(drive.files().list(
                    q="mimeType='application/vnd.google-apps.spreadsheet' and trashed=false",
                    pageSize=1,
                    fields="files(id)",
                )).get("files", [])
                if not found:
                    return self._service_result("configuration_required", "Spreadsheet IDまたは既存Google Sheetsが必要です")
                spreadsheet_id = str(found[0]["id"])
            self._execute(build("sheets", "v4", credentials=credentials, cache_discovery=False).spreadsheets().get(
                spreadsheetId=spreadsheet_id, fields="spreadsheetId"
            ))
        elif name == "drive":
            self._execute(build("drive", "v3", credentials=credentials, cache_discovery=False).about().get(fields="user"))
        elif name == "gmail":
            user_id = str(config["services"]["gmail"].get("user_id", "me") or "me")
            self._execute(build("gmail", "v1", credentials=credentials, cache_discovery=False).users().getProfile(userId=user_id))
        elif name == "docs":
            return self._service_result("configured", "Docs読込はDocument ID指定時に確認します")
        elif name == "calendar":
            self._execute(build("calendar", "v3", credentials=credentials, cache_discovery=False).calendarList().list(maxResults=1))
        return self._service_result("connected", "接続確認済み")

    def _execute(self, request: Any) -> Any:
        """Execute a read request with bounded retries and a caller-visible timeout."""
        last_error: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(request.execute)
            try:
                return future.result(timeout=self.timeout_seconds)
            except FutureTimeoutError as exc:
                future.cancel()
                last_error = TimeoutError(f"Google API timeout after {self.timeout_seconds:g}s")
            except Exception as exc:
                last_error = exc
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
            if attempt < self.retry_attempts and self.retry_backoff_seconds:
                time.sleep(self.retry_backoff_seconds * (2 ** (attempt - 1)))
        assert last_error is not None
        raise last_error

    def _credential_path(self, config: dict[str, Any]) -> Path | None:
        auth = config.get("auth", {}) if isinstance(config.get("auth"), dict) else {}
        mode = auth.get("mode", "disabled")
        key = "service_account_file" if mode == "service_account" else "oauth_token_file" if mode == "oauth" else ""
        value = str(auth.get(key, "")).strip() if key else ""
        return self._resolve_path(value)

    def _auth_path(self, config: dict[str, Any], key: str) -> Path | None:
        auth = config.get("auth", {}) if isinstance(config.get("auth"), dict) else {}
        return self._resolve_path(str(auth.get(key, "")).strip())

    def _resolve_path(self, value: str) -> Path | None:
        if not value:
            return None
        path = Path(value)
        return path if path.is_absolute() else self.root / path

    @staticmethod
    def _enabled_services(config: dict[str, Any]) -> list[str]:
        services = config.get("services", {}) if isinstance(config.get("services"), dict) else {}
        return [name for name in ("sheets", "drive", "gmail", "docs", "calendar") if isinstance(services.get(name), dict) and services[name].get("enabled") is True]

    @staticmethod
    def _validate(config: dict[str, Any]) -> list[str]:
        if not config:
            return [f"config/{CONFIG_NAME} が必要です"]
        errors: list[str] = []
        auth = config.get("auth", {}) if isinstance(config.get("auth"), dict) else {}
        if auth.get("mode", "disabled") not in AUTH_MODES:
            errors.append("auth.mode は disabled / service_account / oauth のいずれかです")
        if config.get("local_first") is not True:
            errors.append("local_first=true が必須です")
        if config.get("dry_run_required") is not True:
            errors.append("dry_run_required=true が必須です")
        if config.get("review_required") is not True:
            errors.append("review_required=true が必須です")
        if config.get("production_actions_enabled") is not False:
            errors.append("production_actions_enabled=false が必須です")
        return errors

    @staticmethod
    def _service_result(status: str, label: str) -> dict[str, Any]:
        return {"ok": status == "connected", "status": status, "label": label, "dry_run": True, "write_performed": False, "review_required": True}

    @staticmethod
    def _result(config_status: dict[str, Any], services: dict[str, Any], *, ok: bool) -> dict[str, Any]:
        return {
            "ok": ok,
            "status": "connected" if ok else config_status.get("status", "blocked"),
            "label": "Google Workspace接続確認済み" if ok else config_status.get("label", AUTH_REQUIRED),
            "services": services,
            "dry_run": True,
            "write_performed": False,
            "production_actions_enabled": False,
            "execute_allowed": False,
            "approval_required": True,
            "review_required": True,
        }


def get_google_workspace_health(*, root: str | Path = PROJECT_ROOT) -> dict[str, Any]:
    """Configuration-only health snapshot; never contacts Google."""
    return GoogleWorkspaceManager(root=root).configuration_status()
