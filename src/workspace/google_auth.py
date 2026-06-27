"""google_auth — Credential configuration loader for Google Sheets Connector (v5.2 Phase 4-2).

SECURITY RULES (enforced, not just convention):
  - Real credentials are NEVER committed to this repository.
  - service_account_file / oauth_client_file are LOCAL paths set by the user.
  - auth_mode defaults to "disabled" in committed config — safe by default.
  - Local runtime override: config/workspace_local.json (git-ignored).
  - This module NEVER loads credential file contents; it only checks existence.
  - credentials/ is excluded by .gitignore; only .gitkeep is tracked.
"""
from __future__ import annotations
from pathlib import Path

from src.workspace.sync_validator import load_settings, load_merged_settings

ROOT = Path(__file__).parent.parent.parent

AUTH_MODES = ("disabled", "service_account", "oauth")


def get_auth_config(settings: dict | None = None) -> dict:
    """Return auth configuration (paths and mode only). No credentials loaded.

    When settings=None, loads committed config merged with local workspace_local.json.
    Committed auth_mode is always 'disabled'; local override can activate service_account.
    """
    if settings is None:
        settings = load_merged_settings()

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


def get_dependency_status() -> dict:
    """Check whether optional gspread and google-auth packages are installed.

    Uses importlib.metadata — no import side effects, safe to call at any time.
    Never raises; always returns a dict.
    """
    import importlib.metadata as _meta

    def _check(pkg: str) -> tuple[bool, str]:
        try:
            return True, _meta.version(pkg)
        except Exception:
            return False, ""

    gspread_ok,      gspread_ver  = _check("gspread")
    google_auth_ok,  gauth_ver    = _check("google-auth")

    missing = [p for p, ok in [("gspread", gspread_ok), ("google-auth", google_auth_ok)] if not ok]

    return {
        "gspread_installed":      gspread_ok,
        "gspread_version":        gspread_ver,
        "google_auth_installed":  google_auth_ok,
        "google_auth_version":    gauth_ver,
        "all_ready":              gspread_ok and google_auth_ok,
        "missing":                missing,
        "install_hint":           "pip install gspread google-auth" if missing else "",
    }


def build_client(settings: dict | None = None) -> dict:
    """Build a gspread client for the configured auth mode. Never crashes.

    Returns a dict:
      status   — "disabled" | "connected" | "deps_missing" | "no_file_configured"
                 | "file_missing" | "error" | "oauth_pending"
      client   — gspread.Client or None
      auth_mode — str
      error    — str or None
      icon     — str emoji
      label    — str (human-readable)
    """
    if settings is None:
        settings = load_merged_settings()

    cfg = get_auth_config(settings)
    auth_mode = cfg["auth_mode"]

    _base: dict = {
        "auth_mode": auth_mode,
        "client":    None,
        "status":    "disabled",
        "error":     None,
        "icon":      "⚫",
        "label":     "認証無効（ドライランのみ）",
    }

    if auth_mode == "disabled":
        return _base

    # ── Dependency check ──────────────────────────────────────────────────────
    deps = get_dependency_status()
    if not deps["all_ready"]:
        missing = ", ".join(deps["missing"])
        return {
            **_base,
            "status": "deps_missing",
            "error":  f"依存パッケージが不足しています: {missing} → {deps['install_hint']}",
            "icon":   "🔴",
            "label":  f"パッケージ未インストール: {missing}",
        }

    # ── Service Account ───────────────────────────────────────────────────────
    if auth_mode == "service_account":
        path_str = cfg["service_account_file"]
        if not path_str:
            return {
                **_base,
                "status": "no_file_configured",
                "error":  "connector.service_account_file が設定されていません。",
                "icon":   "🔴",
                "label":  "サービスアカウントファイル未設定",
            }

        cred_path = ROOT / path_str
        if not cred_path.exists():
            return {
                **_base,
                "status": "file_missing",
                "error":  f"認証ファイルが見つかりません: {path_str}",
                "icon":   "🔴",
                "label":  f"ファイルなし: {path_str}",
            }

        try:
            import gspread  # type: ignore[import-untyped]
            from google.oauth2.service_account import Credentials  # type: ignore[import-untyped]

            _SCOPES = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_file(str(cred_path), scopes=_SCOPES)
            client = gspread.authorize(creds)
            return {
                **_base,
                "status": "connected",
                "client": client,
                "error":  None,
                "icon":   "🟢",
                "label":  "サービスアカウント接続済み",
            }
        except Exception as exc:
            return {
                **_base,
                "status": "error",
                "error":  f"gspread接続エラー: {type(exc).__name__}: {exc}",
                "icon":   "🔴",
                "label":  f"接続エラー: {type(exc).__name__}",
            }

    # ── OAuth (Phase 4-2+) ────────────────────────────────────────────────────
    if auth_mode == "oauth":
        return {
            **_base,
            "status": "oauth_pending",
            "error":  "OAuthモードはPhase 4-2以降で実装予定です。",
            "icon":   "🟡",
            "label":  "OAuth: Phase 4-2以降",
        }

    return {
        **_base,
        "status": "unknown_mode",
        "error":  f"不明な auth_mode: {auth_mode}",
        "icon":   "🔴",
        "label":  f"不明な認証モード: {auth_mode}",
    }
