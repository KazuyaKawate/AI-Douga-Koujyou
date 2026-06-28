"""sheet_writer — Google Sheets write abstraction for Creator Factory OS (v5.2 Phase 4-3).

QUAD-LOCK WRITE GUARD (all four must be true to write):
  1. auth_mode != 'disabled'
  2. dry_run == False
  3. manual_execute == True
  4. allow_write == True   ← Phase 4-3: always False by default; Phase 4-4+ may enable writes

DEPENDENCY GUARDS (checked after quad-lock):
  5. gspread installed
  6. google-auth installed
  7. credential file exists

Default behavior is always preview-only. Never crashes UI. Never writes by accident.
Actual writes remain Phase 4-4+ (Phase 4-3 = live read-only connection verified).
"""
from __future__ import annotations

from src.workspace.google_auth import get_auth_config, get_credential_status, get_dependency_status, build_client


def _can_write(
    auth_mode: str,
    dry_run: bool,
    manual_execute: bool,
    allow_write: bool = False,
) -> tuple[bool, str]:
    """Quad-lock write guard. All four conditions must be met to allow writes."""
    if auth_mode == "disabled":
        return False, "auth_mode が 'disabled' のため書き込み不可"
    if dry_run:
        return False, "dry_run=True のため書き込み不可（プレビューのみ）"
    if not manual_execute:
        return False, "manual_execute=False のため書き込み不可（手動承認が必要）"
    if not allow_write:
        return False, "allow_write=False のため書き込み不可（Phase 4-3: 読み取り専用）"
    return True, "書き込み条件を満たしています"


def write_rows(
    sheet_name: str,
    rows: list[dict],
    *,
    dry_run: bool = True,
    manual_execute: bool = False,
    allow_write: bool = False,
    settings: dict | None = None,
) -> dict:
    """Write rows to a Google Sheet.

    Default: preview-only (dry_run=True, manual_execute=False, allow_write=False).
    Phase 4-3: allow_write always defaults False — read-only phase.
    Phase 4-4+: allow_write=True enables actual writes when all other guards pass.
    """
    auth_cfg = get_auth_config(settings)
    auth_mode = auth_cfg["auth_mode"]
    can_write, reason = _can_write(auth_mode, dry_run, manual_execute, allow_write)

    base = {
        "executed":       False,
        "dry_run":        dry_run,
        "manual_execute": manual_execute,
        "auth_mode":      auth_mode,
        "sheet_name":     sheet_name,
        "rows_preview":   len(rows),
        "rows_written":   0,
        "reason":         reason,
        "preview":        [_row_preview(r) for r in rows[:5]],
    }

    if not can_write:
        return base

    # Dependency guard — must be checked before credential and API access
    deps = get_dependency_status()
    if not deps["all_ready"]:
        missing = ", ".join(deps["missing"])
        base["reason"] = f"依存パッケージが不足しています: {missing} → {deps['install_hint']}"
        return base

    cred = get_credential_status(settings)
    if not cred["ready"]:
        base["reason"] = f"認証エラー: {cred['label']}"
        return base

    # Resolve settings for spreadsheet_id lookup
    _write_settings = settings
    if _write_settings is None:
        from src.workspace.sync_validator import load_merged_settings as _lms_w
        _write_settings = _lms_w()

    # Actual gspread append (Phase 4-4+)
    try:
        client_result = build_client(_write_settings)
        if client_result["status"] != "connected":
            base["reason"] = f"接続エラー: {client_result['status']}"
            return base
        spreadsheet_id = (
            _write_settings.get("google_sheets", {}).get("spreadsheet_id", "").strip()
            or _write_settings.get("spreadsheet_id", "").strip()
        )
        if not spreadsheet_id:
            base["reason"] = "spreadsheet_id が未設定です。config/workspace_local.json を確認してください。"
            return base
        client       = client_result["client"]
        spreadsheet  = client.open_by_key(spreadsheet_id)
        worksheet_obj = spreadsheet.worksheet(sheet_name)
        for row in rows:
            values = list(row.values())
            worksheet_obj.append_row(values, value_input_option="USER_ENTERED")
        base["executed"]     = True
        base["rows_written"] = len(rows)
        base["reason"]       = f"{len(rows)}行を追記しました（シート: {sheet_name}）"
    except Exception as exc:
        base["reason"] = f"書き込みエラー: {type(exc).__name__}: {exc}"
    return base


def _row_preview(row: dict) -> dict:
    """表示用にrow値を短縮する。"""
    return {k: str(v)[:50] for k, v in list(row.items())[:8]}


def _col_letter(n: int) -> str:
    """列番号（1始まり）をアルファベット表記に変換する（例: 1→A, 27→AA）。"""
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


def write_sheet_upsert(
    sheet_name: str,
    flat_rows: list[dict],
    key_field: str,
    columns: list[tuple[str, str]],
    *,
    dry_run: bool = True,
    manual_execute: bool = False,
    allow_write: bool = False,
    settings: dict | None = None,
) -> dict:
    """Phase 4-5: ヘッダー対応アップサート書き込み。

    処理順:
      1. ヘッダー行（row 1）を確認・なければ初期化
      2. 既存データをkey_fieldでインデックス化
      3. ローカル各行: キー一致 → update / 未一致 → append_row
      4. 行削除は行わない（安全設計）

    引数:
      sheet_name  — 書き込み先ワークシート名
      flat_rows   — extract_flat_row済みのフラット行リスト
      key_field   — ユニークキーのフィールド名
      columns     — [(local_field, header_name), ...] のリスト
      dry_run     — True=プレビューのみ（デフォルト）
      manual_execute — True=手動承認済み
      allow_write    — True=実際に書き込む（UI経由でのみ渡す）
      settings    — マージ済み設定dict（Noneの場合は自動ロード）

    戻り値:
      {ok, executed, dry_run, sheet_name, appended, updated, skipped, total_in, error, reason, duration_ms}
    """
    import time
    t0 = time.time()

    auth_cfg  = get_auth_config(settings)
    auth_mode = auth_cfg["auth_mode"]
    can_write, reason = _can_write(auth_mode, dry_run, manual_execute, allow_write)

    fields  = [f for f, _ in columns]
    headers = [h for _, h in columns]

    # key_field の列インデックス（0始まり）
    try:
        key_col_idx = fields.index(key_field)
    except ValueError:
        key_col_idx = 0

    base = {
        "ok":          False,
        "executed":    False,
        "dry_run":     dry_run,
        "sheet_name":  sheet_name,
        "appended":    0,
        "updated":     0,
        "skipped":     0,
        "total_in":    len(flat_rows),
        "error":       None,
        "reason":      reason,
        "duration_ms": 0,
    }

    if not flat_rows:
        base["ok"]     = True
        base["reason"] = "同期対象行がありません"
        base["duration_ms"] = int((time.time() - t0) * 1000)
        return base

    if not can_write:
        # dry-run / ガードブロックは ok=True（エラーではない）
        base["ok"] = True
        base["duration_ms"] = int((time.time() - t0) * 1000)
        return base

    # 依存パッケージ確認
    deps = get_dependency_status()
    if not deps["all_ready"]:
        missing = ", ".join(deps["missing"])
        base["error"] = f"依存パッケージ不足: {missing}"
        base["duration_ms"] = int((time.time() - t0) * 1000)
        return base

    cred = get_credential_status(settings)
    if not cred["ready"]:
        base["error"] = f"認証エラー: {cred['label']}"
        base["duration_ms"] = int((time.time() - t0) * 1000)
        return base

    _settings = settings
    if _settings is None:
        from src.workspace.sync_validator import load_merged_settings as _lms
        _settings = _lms()

    try:
        client_result = build_client(_settings)
        if client_result["status"] != "connected":
            base["error"] = f"接続エラー: {client_result['status']}"
            base["duration_ms"] = int((time.time() - t0) * 1000)
            return base

        spreadsheet_id = (
            _settings.get("google_sheets", {}).get("spreadsheet_id", "").strip()
            or _settings.get("spreadsheet_id", "").strip()
        )
        if not spreadsheet_id:
            base["error"] = "spreadsheet_id 未設定。config/workspace_local.json を確認してください。"
            base["duration_ms"] = int((time.time() - t0) * 1000)
            return base

        client      = client_result["client"]
        spreadsheet = client.open_by_key(spreadsheet_id)
        ws          = spreadsheet.worksheet(sheet_name)

        # 既存データをすべて取得
        all_values = ws.get_all_values()

        # ヘッダー行（row 1）が空なら初期化
        if not all_values or not any(c.strip() for c in all_values[0]):
            ws.append_row(headers, value_input_option="USER_ENTERED")
            all_values = [headers]

        # データ行をkey_fieldでインデックス化（行番号は1始まり、ヘッダー=1）
        existing_keys: dict[str, int] = {}
        for row_idx, row_vals in enumerate(all_values[1:], start=2):
            if len(row_vals) > key_col_idx:
                existing_keys[str(row_vals[key_col_idx]).strip()] = row_idx

        appended = 0
        updated  = 0
        skipped  = 0

        for flat_row in flat_rows:
            values  = [str(flat_row.get(f, "")) for f in fields]
            row_key = str(flat_row.get(key_field, "")).strip()

            if not row_key:
                skipped += 1
                continue

            if row_key in existing_keys:
                # 既存行を上書き更新（ヘッダー行は絶対に触らない）
                row_num        = existing_keys[row_key]
                end_col        = _col_letter(len(fields))
                range_notation = f"A{row_num}:{end_col}{row_num}"
                ws.update(range_notation, [values], value_input_option="USER_ENTERED")
                updated += 1
            else:
                # 新規行を末尾に追加
                ws.append_row(values, value_input_option="USER_ENTERED")
                existing_keys[row_key] = len(all_values) + appended + 1
                appended += 1

        base["ok"]       = True
        base["executed"] = True
        base["appended"] = appended
        base["updated"]  = updated
        base["skipped"]  = skipped
        base["reason"]   = f"追加:{appended}行 / 更新:{updated}行 / スキップ:{skipped}行"

    except Exception as exc:
        base["error"] = f"書き込みエラー: {type(exc).__name__}: {exc}"

    base["duration_ms"] = int((time.time() - t0) * 1000)
    return base


def get_writer_status(settings: dict | None = None) -> dict:
    """書き込み設定ステータスを返す。副作用なし。"""
    auth_cfg = get_auth_config(settings)
    return {
        "auth_mode":     auth_cfg["auth_mode"],
        "write_enabled": auth_cfg["auth_mode"] != "disabled",
        "allow_write":   False,
        "phase":         "Phase 4-5 (本番シート upsert 同期; allow_write=False in committed code)",
        "note":          "allow_write=True は UI ボタン経由でのみ渡す。コミット済みコードには含まれない。",
    }
