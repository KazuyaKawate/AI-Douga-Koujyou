"""sync_validator — Validate workspace settings and sync readiness (v5.2).

Read-only. Never makes API calls.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SETTINGS_PATH = ROOT / "config" / "workspace_settings.json"


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def validate_settings(settings: dict | None = None) -> tuple[bool, list[str]]:
    """Return (is_valid, errors). Checks config completeness without API calls."""
    if settings is None:
        settings = load_settings()
    errors: list[str] = []

    if not settings:
        errors.append("workspace_settings.json が存在しないか空です。")
        return False, errors

    spreadsheet_id = settings.get("spreadsheet_id", "").strip()
    if not spreadsheet_id:
        errors.append("spreadsheet_id が設定されていません。Google SheetsのURLからIDをコピーしてください。")

    creds_path = settings.get("google_credentials_path", "").strip()
    if not creds_path:
        errors.append("google_credentials_path が設定されていません。")
    elif not (ROOT / creds_path).exists():
        errors.append(
            f"Google認証ファイルが見つかりません: {creds_path}  "
            f"Google Cloud ConsoleからService Account JSONをダウンロードして配置してください。"
        )

    targets = settings.get("sync_targets", [])
    if not targets:
        errors.append("sync_targets が空です。config/workspace_settings.json に同期ターゲットを追加してください。")
    else:
        for t in targets:
            if not t.get("enabled", True):
                continue
            local_file = t.get("local_file", "")
            if local_file and not (ROOT / local_file).exists():
                errors.append(f"ローカルファイルが見つかりません: {local_file} (target: {t.get('target_id', '?')})")

    if settings.get("auto_sync", False):
        errors.append("auto_sync=true は禁止です。手動同期のみ許可されています。")

    return len(errors) == 0, errors


def get_connection_status(settings: dict | None = None) -> dict:
    """Return connection status dict. Read-only, no API calls."""
    if settings is None:
        settings = load_settings()

    if not settings:
        return {"status": "unconfigured", "label": "未設定", "icon": "⚫",
                "has_credentials": False, "has_spreadsheet_id": False,
                "enabled": False, "dry_run_default": True}

    has_spreadsheet_id = bool(settings.get("spreadsheet_id", "").strip())
    creds_path = settings.get("google_credentials_path", "").strip()
    has_credentials = bool(creds_path) and (ROOT / creds_path).exists()
    enabled = settings.get("enabled", False)

    if not has_credentials:
        status, label, icon = "no_credentials", "認証ファイルなし", "🔴"
    elif not has_spreadsheet_id:
        status, label, icon = "no_spreadsheet", "スプレッドシートID未設定", "🟡"
    elif not enabled:
        status, label, icon = "disabled", "無効", "⚪"
    else:
        status, label, icon = "configured", "設定済み（未接続）", "🟡"

    return {
        "status":            status,
        "label":             label,
        "icon":              icon,
        "has_credentials":   has_credentials,
        "has_spreadsheet_id": has_spreadsheet_id,
        "enabled":           enabled,
        "dry_run_default":   settings.get("dry_run_default", True),
    }


def get_enabled_targets(settings: dict | None = None) -> list[dict]:
    if settings is None:
        settings = load_settings()
    return [t for t in settings.get("sync_targets", []) if t.get("enabled", True)]


# ── Phase 2: Connector validation ─────────────────────────────────────────────

_CREDENTIAL_PATTERNS = (
    "google_credentials.json",
    "service_account.json",
    "credentials.json",
    "client_secret.json",
    "oauth_client.json",
    "token.json",
)


def validate_connector_settings(settings: dict | None = None) -> tuple[bool, list[str]]:
    """Validate Phase 2 connector configuration. Read-only, no API calls."""
    if settings is None:
        settings = load_settings()
    errors: list[str] = []

    connector = settings.get("connector", {})
    auth_mode = connector.get("auth_mode", "disabled")
    if auth_mode not in ("disabled", "service_account", "oauth"):
        errors.append(
            f"connector.auth_mode が無効な値です: '{auth_mode}'. "
            "disabled / service_account / oauth のいずれかを指定してください。"
        )

    if auth_mode == "disabled":
        return True, []

    if auth_mode == "service_account":
        sa_file = connector.get("service_account_file", "").strip()
        if not sa_file:
            errors.append("connector.service_account_file が設定されていません。")
        elif (ROOT / sa_file).exists():
            pass
        else:
            errors.append(f"サービスアカウントファイルが見つかりません: {sa_file}")

    if auth_mode == "oauth":
        oc_file = connector.get("oauth_client_file", "").strip()
        if not oc_file:
            errors.append("connector.oauth_client_file が設定されていません。")
        elif not (ROOT / oc_file).exists():
            errors.append(f"OAuthクライアントファイルが見つかりません: {oc_file}")

    return len(errors) == 0, errors


def check_no_credentials_committed() -> tuple[bool, list[str]]:
    """Confirm that known credential file patterns are not present in the project root.

    This is a safety check — credential files must never be committed.
    Returns (safe, warnings).
    """
    warnings: list[str] = []
    for name in _CREDENTIAL_PATTERNS:
        # Check root and config/ directory
        for candidate in (ROOT / name, ROOT / "config" / name):
            if candidate.exists():
                warnings.append(
                    f"認証ファイルが検出されました: {candidate.relative_to(ROOT)}  "
                    "このファイルをリポジトリにコミットしないでください。"
                    ".gitignore に追加してください。"
                )
    return len(warnings) == 0, warnings
