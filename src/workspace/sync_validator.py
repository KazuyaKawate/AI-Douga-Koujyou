"""sync_validator — Validate workspace settings and sync readiness (v5.2).

Read-only. Never makes API calls.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SETTINGS_PATH       = ROOT / "config" / "workspace_settings.json"
LOCAL_SETTINGS_PATH = ROOT / "config" / "workspace_local.json"


def load_settings() -> dict:
    """Load committed workspace_settings.json. auth_mode always 'disabled' in repo."""
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def load_local_settings() -> dict:
    """Load local-only workspace_local.json override. Returns {} if missing (normal).

    This file is git-ignored and never committed. It may contain:
      auth_mode, service_account_file, spreadsheet_id, worksheet_name, range
    """
    if LOCAL_SETTINGS_PATH.exists():
        try:
            return json.loads(LOCAL_SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def load_merged_settings() -> dict:
    """Committed settings + local overrides. Local wins. Never crashes.

    Local workspace_local.json keys override committed workspace_settings.json:
      auth_mode            → connector.auth_mode
      service_account_file → connector.service_account_file
      spreadsheet_id       → google_sheets.spreadsheet_id
      worksheet_name       → google_sheets.worksheet_name
      range                → google_sheets.range
    """
    base  = load_settings()
    local = load_local_settings()
    if not local:
        return base

    merged = copy.deepcopy(base)
    if "auth_mode" in local:
        merged.setdefault("connector", {})["auth_mode"] = local["auth_mode"]
    if "service_account_file" in local:
        merged.setdefault("connector", {})["service_account_file"] = local["service_account_file"]
    if "spreadsheet_id" in local:
        merged.setdefault("google_sheets", {})["spreadsheet_id"] = local["spreadsheet_id"]
    if "worksheet_name" in local:
        merged.setdefault("google_sheets", {})["worksheet_name"] = local["worksheet_name"]
    if "range" in local:
        merged.setdefault("google_sheets", {})["range"] = local["range"]
    return merged


def get_local_config_status() -> dict:
    """Report local workspace_local.json existence and key fields. Never crashes.

    Returns:
      exists              — bool
      path                — str (relative)
      auth_mode           — str (from local, or "")
      service_account_file — str
      spreadsheet_id      — str
      worksheet_name      — str
      has_spreadsheet_id  — bool
      has_service_account_file — bool
      is_active           — True when auth_mode != disabled/""
    """
    local  = load_local_settings()
    exists = LOCAL_SETTINGS_PATH.exists()
    am     = local.get("auth_mode", "")
    sa     = local.get("service_account_file", "")
    sid    = local.get("spreadsheet_id", "").strip()
    ws     = local.get("worksheet_name", "").strip()
    return {
        "exists":                   exists,
        "path":                     "config/workspace_local.json",
        "auth_mode":                am,
        "service_account_file":     sa,
        "spreadsheet_id":           sid,
        "worksheet_name":           ws,
        "has_spreadsheet_id":       bool(sid),
        "has_service_account_file": bool(sa),
        "is_active":                am not in ("", "disabled"),
    }


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


def check_no_credentials_committed() -> tuple[bool, list[str]]:  # noqa: D401
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


# ── Phase 3: Safety & gspread Readiness ───────────────────────────────────────

_GITIGNORE_REQUIRED_PATTERNS = (
    "credentials/",
    ".gitkeep",
    "service_account",
    "token.json",
)


def check_gitignore_protections() -> tuple[bool, list[str]]:
    """Verify that .gitignore contains credential protection patterns.

    Returns (ok, warnings).
    """
    gitignore_path = ROOT / ".gitignore"
    warnings: list[str] = []

    if not gitignore_path.exists():
        warnings.append(
            ".gitignore が見つかりません。"
            "認証ファイルが誤ってコミットされる可能性があります。"
        )
        return False, warnings

    content = gitignore_path.read_text(encoding="utf-8", errors="replace")
    missing = [p for p in _GITIGNORE_REQUIRED_PATTERNS if p not in content]
    if missing:
        warnings.append(
            f".gitignore に次のパターンが見つかりません: {', '.join(missing)}  "
            "docs/google_sheets_setup.md を参照して .gitignore を更新してください。"
        )

    return len(warnings) == 0, warnings


def check_credentials_gitkeep() -> tuple[bool, list[str]]:
    """Verify credentials/.gitkeep exists and no real credential JSON files are there.

    Returns (ok, warnings).
    """
    warnings: list[str] = []
    creds_dir = ROOT / "credentials"

    if not creds_dir.exists():
        warnings.append(
            "credentials/ フォルダが存在しません。"
            "mkdir credentials && touch credentials/.gitkeep で作成してください。"
        )
        return False, warnings

    if not (creds_dir / ".gitkeep").exists():
        warnings.append(
            "credentials/.gitkeep が見つかりません。"
            "touch credentials/.gitkeep で作成してください。"
        )

    for json_file in creds_dir.glob("*.json"):
        warnings.append(
            f"認証JSONファイルが credentials/ に検出されました: {json_file.name}  "
            "リポジトリにコミットしないでください。"
        )

    return len(warnings) == 0, warnings


def check_phase3_dependencies() -> dict:
    """Check gspread and google-auth installation. Never raises, no circular import."""
    import importlib.metadata as _meta

    def _check(pkg: str) -> tuple[bool, str]:
        try:
            return True, _meta.version(pkg)
        except Exception:
            return False, ""

    gspread_ok, gspread_ver = _check("gspread")
    gauth_ok, gauth_ver = _check("google-auth")
    missing = [p for p, ok in [("gspread", gspread_ok), ("google-auth", gauth_ok)] if not ok]

    return {
        "gspread_installed":     gspread_ok,
        "gspread_version":       gspread_ver,
        "google_auth_installed": gauth_ok,
        "google_auth_version":   gauth_ver,
        "all_ready":             gspread_ok and gauth_ok,
        "missing":               missing,
        "install_hint":          "pip install gspread google-auth" if missing else "",
    }


def get_phase3_readiness(settings: dict | None = None) -> dict:
    """Composite Phase 3 safety and gspread readiness check. Read-only, never raises.

    Returns a dict:
      ready              — True when all safety blockers are clear
      checks             — list of {label, ok, detail, optional} per check
      blockers           — list of blocking issue strings
      deps_ready         — gspread + google-auth both installed
      spreadsheet_id_set — spreadsheet_id is non-empty in settings
    """
    if settings is None:
        settings = load_settings()

    checks: list[dict] = []
    blockers: list[str] = []

    # 1. .gitignore protections
    gi_ok, gi_warns = check_gitignore_protections()
    checks.append({
        "label":    ".gitignore 認証保護",
        "ok":       gi_ok,
        "detail":   "✅ 保護パターン確認済み" if gi_ok else " / ".join(gi_warns),
        "optional": False,
    })
    if not gi_ok:
        blockers.extend(gi_warns)

    # 2. credentials/.gitkeep
    gk_ok, gk_warns = check_credentials_gitkeep()
    checks.append({
        "label":    "credentials/.gitkeep",
        "ok":       gk_ok,
        "detail":   "✅ 存在確認済み" if gk_ok else " / ".join(gk_warns),
        "optional": False,
    })
    if not gk_ok:
        blockers.extend(gk_warns)

    # 3. No credential JSON files committed
    nc_ok, nc_warns = check_no_credentials_committed()
    checks.append({
        "label":    "認証ファイル未コミット",
        "ok":       nc_ok,
        "detail":   "✅ 認証ファイルなし（安全）" if nc_ok else " / ".join(nc_warns),
        "optional": False,
    })
    if not nc_ok:
        blockers.extend(nc_warns)

    # 4. auth_mode remains disabled
    auth_mode = settings.get("connector", {}).get("auth_mode", "disabled")
    auth_safe = auth_mode == "disabled"
    checks.append({
        "label":    "auth_mode=disabled",
        "ok":       auth_safe,
        "detail":   "✅ disabled（デフォルト安全）" if auth_safe else f"⚠️ auth_mode={auth_mode}",
        "optional": False,
    })

    # 5. gspread / google-auth (optional — needed for Phase 4+)
    deps = check_phase3_dependencies()
    deps_ok = deps["all_ready"]
    if deps_ok:
        dep_detail = (
            f"✅ gspread {deps['gspread_version']} "
            f"/ google-auth {deps['google_auth_version']}"
        )
    else:
        missing_str = ", ".join(deps["missing"])
        dep_detail = (
            f"📦 未インストール: {missing_str} — "
            f"{deps['install_hint']} （Phase 4+ で必要）"
        )
    checks.append({
        "label":    "gspread / google-auth",
        "ok":       deps_ok,
        "detail":   dep_detail,
        "optional": True,
    })

    # 6. spreadsheet_id (optional — needed for Phase 4+)
    spreadsheet_id = settings.get("spreadsheet_id", "").strip()
    sid_ok = bool(spreadsheet_id)
    checks.append({
        "label":    "spreadsheet_id",
        "ok":       sid_ok,
        "detail":   (
            f"✅ 設定済み: {spreadsheet_id[:24]}…" if sid_ok
            else "⬜ 未設定 — Google SheetsのURLからIDをコピー（Phase 4+ で必要）"
        ),
        "optional": True,
    })

    return {
        "ready":              len(blockers) == 0,
        "checks":             checks,
        "blockers":           blockers,
        "deps_ready":         deps_ok,
        "spreadsheet_id_set": sid_ok,
    }
