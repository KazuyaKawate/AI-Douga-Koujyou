"""google_auth — Credential configuration loader for Google Sheets Connector (v5.2 Phase 2).

SECURITY RULES (enforced, not just convention):
  - Real credentials are NEVER committed to this repository.
  - service_account_file / oauth_client_file are LOCAL paths set by the user.
  - auth_mode defaults to "disabled" — all operations run in dry-run mode.
  - This module NEVER loads credential file contents; it only checks existence.
"""
from __future__ import annotations
from pathlib import Path

from src.workspace.sync_validator import load_settings

ROOT = Path(__file__).parent.parent.parent

AUTH_MODES = ("disabled", "service_account", "oauth")


def get_auth_config(settings: dict | None = None) -> dict:
    """Return auth configuration (paths and mode only). No credentials loaded."""
    if settings is None:
        settings = load_settings()

    connector = settings.get("connector", {})
    auth_mode = connector.get("auth_mode", "disabled")
    if auth_mode not in AUTH_MODES:
        auth_mode = "disabled"

    return {
        "auth_mode":           auth_mode,
        "service_account_file": connector.get("service_account_file", ""),
        "oauth_client_file":   connector.get("oauth_client_file", ""),
    }


def get_credential_status(settings: dict | None = None) -> dict:
    """Return credential status without loading actual credential content."""
    cfg = get_auth_config(settings)
    auth_mode = cfg["auth_mode"]

    if auth_mode == "disabled":
        return {
            "auth_mode":              "disabled",
            "ready":                  False,
            "status":                 "disabled",
            "icon":                   "⚫",
            "label":                  "認証無効（ドライランのみ）",
            "credential_file_exists": False,
            "credential_file_path":   "",
        }

    if auth_mode == "service_account":
        path_str = cfg["service_account_file"]
        if not path_str:
            return {
                "auth_mode":              auth_mode,
                "ready":                  False,
                "status":                 "no_file_configured",
                "icon":                   "🔴",
                "label":                  "サービスアカウントファイル未設定",
                "credential_file_exists": False,
                "credential_file_path":   "",
            }
        exists = (ROOT / path_str).exists()
        return {
            "auth_mode":              auth_mode,
            "ready":                  exists,
            "status":                 "file_found" if exists else "file_missing",
            "icon":                   "🟢" if exists else "🔴",
            "label":                  "サービスアカウント: ファイルあり" if exists else f"ファイルなし: {path_str}",
            "credential_file_exists": exists,
            "credential_file_path":   path_str,
        }

    if auth_mode == "oauth":
        path_str = cfg["oauth_client_file"]
        if not path_str:
            return {
                "auth_mode":              auth_mode,
                "ready":                  False,
                "status":                 "no_file_configured",
                "icon":                   "🔴",
                "label":                  "OAuthクライアントファイル未設定",
                "credential_file_exists": False,
                "credential_file_path":   "",
            }
        exists = (ROOT / path_str).exists()
        return {
            "auth_mode":              auth_mode,
            "ready":                  exists,
            "status":                 "file_found" if exists else "file_missing",
            "icon":                   "🟢" if exists else "🔴",
            "label":                  "OAuth: ファイルあり" if exists else f"ファイルなし: {path_str}",
            "credential_file_exists": exists,
            "credential_file_path":   path_str,
        }

    return {
        "auth_mode":              auth_mode,
        "ready":                  False,
        "status":                 "unknown",
        "icon":                   "⚫",
        "label":                  "不明な認証モード",
        "credential_file_exists": False,
        "credential_file_path":   "",
    }


def build_client(settings: dict | None = None):
    """Placeholder for future Google API client construction.

    Phase 2: always returns None (no gspread dependency).
    Phase 3+: will return a google-auth credentials object for gspread when
              auth_mode != 'disabled' and the credential file exists.
    """
    status = get_credential_status(settings)
    if not status["ready"]:
        return None
    # Phase 3+: construct actual google-auth / gspread client here.
    return None
