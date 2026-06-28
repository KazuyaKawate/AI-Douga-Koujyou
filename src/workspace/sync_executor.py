"""sync_executor — Google Sheets コネクター オーケストレーター (v5.2 Phase 4-5)

実行フロー:
  1. load_settings()
  2. read_local_data() — ローカルJSONファイル
  3. read_sheet()      — Google Sheet行（auth_mode='disabled'時はサンプルデータ）
  4. diff_records()    — 差分計算
  5. プレビュー生成    — 書き込みなし
  6. execute           — manual_execute=True + dry_run=False + auth_mode != 'disabled' の場合のみ

Phase 4-5 追加:
  - run_production_sync(): KPI / Revenue / Notes の3シートにupsert同期する専用関数
    dry_run=True (デフォルト) → 差分プレビューのみ
    dry_run=False + manual_execute=True + allow_write=True → 実際のupsert実行

ルール（コードで強制）:
  - 自動実行なし
  - dry_run=True がデフォルト
  - manual_execute=False がデフォルト
  - auth_mode='disabled' がデフォルト → APIコールなし
  - allow_write=False がデフォルト → UIボタン経由でのみ True を渡す
"""
from __future__ import annotations
import time
from datetime import datetime, timezone

from src.workspace.sync_validator import load_settings, load_merged_settings, load_local_settings, get_enabled_targets
from src.workspace.sheets_sync import read_local_data, get_mapping
from src.workspace.google_auth import get_auth_config, get_credential_status, build_client, get_dependency_status
from src.workspace.sheet_reader import read_sheet, read_sheet_detail, get_reader_status
from src.workspace.sheet_writer import write_rows, get_writer_status
from src.workspace.sheet_diff import diff_records, summarize_diff


def run_preview(settings: dict | None = None) -> dict:
    """Steps 1-5: load → read local → read sheet → diff → preview. No writes."""
    if settings is None:
        settings = load_settings()

    auth_cfg       = get_auth_config(settings)
    cred_status    = get_credential_status(settings)
    reader_status  = get_reader_status(settings)
    writer_status  = get_writer_status(settings)

    t0 = time.time()
    targets = get_enabled_targets(settings)
    target_previews: list[dict] = []

    for t in targets:
        target_id  = t.get("target_id", "")
        local_file = t.get("local_file", "")
        sheet_name = t.get("sheet_name", "")
        mapping    = get_mapping(target_id)
        key_field  = mapping.get("key_field", "id") if mapping else "id"

        local_rows, local_err = read_local_data(local_file)
        sheet_rows, sheet_err = read_sheet(sheet_name, settings)

        if local_err:
            target_previews.append({
                "target_id":    target_id,
                "target_name":  t.get("name", target_id),
                "sheet_name":   sheet_name,
                "error":        local_err,
                "ready":        False,
                "diff":         None,
                "diff_summary": "",
                "conflict_count": 0,
            })
            continue

        diff = diff_records(local_rows, sheet_rows, key_field=key_field)

        target_previews.append({
            "target_id":     target_id,
            "target_name":   t.get("name", target_id),
            "sheet_name":    sheet_name,
            "local_file":    local_file,
            "ready":         True,
            "error":         sheet_err,
            "diff":          diff,
            "diff_summary":  summarize_diff(diff),
            "local_rows":    len(local_rows),
            "sheet_rows":    len(sheet_rows),
            "conflict_count": diff["summary"]["conflicts"],
        })

    duration_ms     = int((time.time() - t0) * 1000)
    total_conflicts = sum(p.get("conflict_count", 0) for p in target_previews)

    return {
        "timestamp":        datetime.now(timezone.utc).isoformat(),
        "auth_mode":        auth_cfg["auth_mode"],
        "credential_ready": cred_status["ready"],
        "credential_icon":  cred_status["icon"],
        "credential_label": cred_status["label"],
        "dry_run":          True,
        "manual_execute":   False,
        "targets":          target_previews,
        "target_count":     len(target_previews),
        "total_conflicts":  total_conflicts,
        "duration_ms":      duration_ms,
        "executed":         False,
        "reader_status":    reader_status,
        "writer_status":    writer_status,
    }


def run_execute(settings: dict | None = None, *, manual_execute: bool = False) -> dict:
    """Step 6: Execute writes only when all three guards pass.

    Guards: manual_execute=True, dry_run=False in settings, auth_mode != 'disabled'.
    """
    if settings is None:
        settings = load_settings()

    auth_cfg = get_auth_config(settings)
    dry_run  = settings.get("dry_run_default", True)

    if not manual_execute or dry_run or auth_cfg["auth_mode"] == "disabled":
        preview = run_preview(settings)
        preview["executed"] = False
        preview["execution_blocked_reason"] = _block_reason(
            auth_cfg["auth_mode"], dry_run, manual_execute
        )
        return preview

    preview = run_preview(settings)
    write_results: list[dict] = []

    for tp in preview["targets"]:
        if not tp.get("ready"):
            continue
        diff       = tp.get("diff") or {}
        rows_data  = [r["local"] for r in diff.get("added", []) if r.get("local")]
        rows_data += [r["local"] for r in diff.get("updated", []) if r.get("local")]

        result = write_rows(
            tp["sheet_name"],
            rows_data,
            dry_run=False,
            manual_execute=True,
            settings=settings,
        )
        write_results.append({"target_id": tp["target_id"], "result": result})

    preview["executed"]      = any(r["result"].get("executed", False) for r in write_results)
    preview["write_results"] = write_results
    return preview


def get_connector_health(settings: dict | None = None) -> dict:
    """Return connector health summary. Read-only. Safe for dashboard / AI CEO."""
    if settings is None:
        settings = load_settings()

    auth_cfg    = get_auth_config(settings)
    cred_status = get_credential_status(settings)
    targets     = get_enabled_targets(settings)
    dry_run     = settings.get("dry_run_default", True)
    last_preview = settings.get("connector", {}).get("last_preview") or "—"

    return {
        "auth_mode":        auth_cfg["auth_mode"],
        "credential_ready": cred_status["ready"],
        "credential_icon":  cred_status["icon"],
        "credential_label": cred_status["label"],
        "dry_run":          dry_run,
        "target_count":     len(targets),
        "targets":          [t.get("target_id", "") for t in targets],
        "last_preview":     last_preview,
        "conflict_count":   0,
        "phase":            "Phase 4-5 (本番シート upsert 同期)",
        "deps_ready":       get_dependency_status()["all_ready"],
    }


def test_read_connection(settings: dict | None = None) -> dict:
    """Read-only connection test. Calls google_auth + sheet_reader. No writes, never crashes.

    Returns a safe summary dict:
      ok            — bool
      auth_mode     — str
      client_status — str (build_client status)
      deps_ready    — bool
      sheet_tested  — str (worksheet name used for test)
      row_count     — int (-1 if not read)
      source        — "live" | "sample" | "error" | "skipped"
      error         — str | None
      duration_ms   — int
    """
    import time
    t0 = time.time()

    if settings is None:
        settings = load_merged_settings()

    auth_cfg = get_auth_config(settings)
    auth_mode = auth_cfg["auth_mode"]
    deps = get_dependency_status()

    _base = {
        "ok":            False,
        "auth_mode":     auth_mode,
        "client_status": "skipped",
        "deps_ready":    deps["all_ready"],
        "sheet_tested":  "",
        "row_count":     -1,
        "source":        "skipped",
        "error":         None,
        "duration_ms":   0,
    }

    if auth_mode == "disabled":
        _base.update({
            "ok":            True,
            "client_status": "disabled",
            "source":        "sample",
            "error":         None,
        })
        _base["duration_ms"] = int((time.time() - t0) * 1000)
        return _base

    # Build client
    client_result = build_client(settings)
    _base["client_status"] = client_result["status"]

    if client_result["status"] != "connected":
        _base["error"] = client_result.get("error") or f"接続エラー: {client_result['status']}"
        _base["duration_ms"] = int((time.time() - t0) * 1000)
        return _base

    # Pick a test worksheet from settings
    gs_cfg = settings.get("google_sheets", {})
    test_sheet = gs_cfg.get("worksheet_name", "").strip()
    if not test_sheet:
        # Fall back to first enabled target's sheet_name
        targets = get_enabled_targets(settings)
        test_sheet = targets[0]["sheet_name"] if targets else "KPI"
    _base["sheet_tested"] = test_sheet

    detail = read_sheet_detail(test_sheet, settings)
    _base.update({
        "ok":        detail["ok"],
        "row_count": detail["row_count"],
        "source":    detail["source"],
        "error":     detail["error"],
    })
    _base["duration_ms"] = int((time.time() - t0) * 1000)
    return _base


_PRODUCTION_WORKSHEETS = frozenset({"KPI", "Revenue", "Notes", "SNS", "Sales"})


def run_test_write(
    settings: dict | None = None,
    *,
    dry_run: bool = True,
    manual_execute: bool = False,
) -> dict:
    """Phase 4-4: Append exactly one tagged test row to test_worksheet_name only.

    Never touches production worksheets (KPI / Revenue / Notes / SNS / Sales).
    dry_run=True  (default) — preview only, no API write.
    dry_run=False + manual_execute=True — appends one row.

    Returns:
      ok            — bool
      executed      — bool
      dry_run       — bool
      worksheet     — str
      row_data      — dict
      rows_written  — int
      error         — str | None
      duration_ms   — int
      phase         — str
    """
    import time
    from datetime import datetime, timezone

    t0 = time.time()

    if settings is None:
        settings = load_merged_settings()

    local   = load_local_settings()
    test_ws = local.get("test_worksheet_name", "").strip()

    base = {
        "ok":           False,
        "executed":     False,
        "dry_run":      dry_run,
        "worksheet":    test_ws,
        "row_data":     {},
        "rows_written": 0,
        "error":        None,
        "duration_ms":  0,
        "phase":        "Phase 4-4 (test worksheet append only)",
    }

    if not test_ws:
        base["error"] = (
            "test_worksheet_name が未設定です。"
            "config/workspace_local.json に "
            '\"test_worksheet_name\": \"Phase4-4-Test\" を追加してください。'
        )
        base["duration_ms"] = int((time.time() - t0) * 1000)
        return base

    if test_ws in _PRODUCTION_WORKSHEETS:
        base["error"] = (
            f"test_worksheet_name='{test_ws}' は本番シートです。"
            "別のシート名（例: 'Phase4-4-Test'）を指定してください。"
        )
        base["duration_ms"] = int((time.time() - t0) * 1000)
        return base

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    test_row = {
        "_phase":  "Phase 4-4 test",
        "_ts":     ts,
        "_source": "Creator Factory OS v5.2",
        "_status": "test-write",
    }
    base["row_data"] = test_row

    if dry_run:
        base["ok"] = True
        base["duration_ms"] = int((time.time() - t0) * 1000)
        return base

    if not manual_execute:
        base["error"] = "manual_execute=False のため実行できません。UI の確認ボタンを使用してください。"
        base["duration_ms"] = int((time.time() - t0) * 1000)
        return base

    result = write_rows(
        test_ws,
        [test_row],
        dry_run=False,
        manual_execute=True,
        allow_write=True,
        settings=settings,
    )

    base["ok"]           = result.get("executed", False)
    base["executed"]     = result.get("executed", False)
    base["rows_written"] = result.get("rows_written", 0)
    base["error"]        = None if result.get("executed") else result.get("reason")
    base["duration_ms"]  = int((time.time() - t0) * 1000)
    return base


_PHASE45_TARGETS = frozenset({"kpi_targets", "revenue_expense", "note_articles"})


def run_production_sync(
    settings: dict | None = None,
    *,
    dry_run: bool = True,
    manual_execute: bool = False,
    allow_write: bool = False,
) -> dict:
    """Phase 4-5: KPI / Revenue / Notes の3シートにupsert同期する。

    安全設計:
      - 対象は _PHASE45_TARGETS（kpi_targets / revenue_expense / note_articles）のみ
      - 行削除は行わない（追加・更新のみ）
      - dry_run=True（デフォルト） → プレビューのみ、書き込みなし
      - allow_write=False（デフォルト） → UIボタン経由でのみ True を渡す

    戻り値:
      ok             — bool（全ターゲットでエラーなし）
      dry_run        — bool
      executed       — bool（実際に書き込みが行われた場合 True）
      auth_mode      — str
      targets        — [{target_id, sheet_name, flat_rows, appended, updated, skipped, error, preview}]
      total_appended — int
      total_updated  — int
      total_skipped  — int
      error          — str | None
      duration_ms    — int
      phase          — str
    """
    from src.workspace.sheets_sync import read_flat_rows, get_mapping
    from src.workspace.sheet_writer import write_sheet_upsert

    import time
    t0 = time.time()

    if settings is None:
        settings = load_merged_settings()

    auth_cfg = get_auth_config(settings)

    base: dict = {
        "ok":            False,
        "dry_run":       dry_run,
        "executed":      False,
        "auth_mode":     auth_cfg["auth_mode"],
        "targets":       [],
        "total_appended": 0,
        "total_updated":  0,
        "total_skipped":  0,
        "error":         None,
        "duration_ms":   0,
        "phase":         "Phase 4-5 (本番シート upsert 同期)",
    }

    # 有効ターゲットを取得し Phase 4-5 対象のみに絞る
    all_targets = get_enabled_targets(settings)
    targets = [t for t in all_targets if t.get("target_id") in _PHASE45_TARGETS]

    target_results: list[dict] = []
    total_appended = 0
    total_updated  = 0
    total_skipped  = 0

    for t in targets:
        target_id  = t["target_id"]
        local_file = t["local_file"]
        sheet_name = t["sheet_name"]
        mapping    = get_mapping(target_id)

        tr: dict = {
            "target_id":  target_id,
            "sheet_name": sheet_name,
            "local_file": local_file,
            "flat_rows":  0,
            "appended":   0,
            "updated":    0,
            "skipped":    0,
            "executed":   False,
            "error":      None,
        }

        # フラット行読み込み（extract_flat_row済み）
        flat_rows, read_err = read_flat_rows(target_id, local_file)
        if read_err:
            tr["error"] = read_err
            target_results.append(tr)
            continue

        tr["flat_rows"] = len(flat_rows)

        if dry_run:
            # ドライランはプレビューのみ（APIコールなし）
            tr["preview"] = [_preview_row(r) for r in flat_rows[:3]]
            target_results.append(tr)
            continue

        # 実際の書き込み（allow_write=True のときのみ _can_write が通る）
        key_field = mapping["key_field"] if mapping else "id"
        columns   = mapping["columns"]   if mapping else []

        result = write_sheet_upsert(
            sheet_name,
            flat_rows,
            key_field,
            columns,
            dry_run=False,
            manual_execute=manual_execute,
            allow_write=allow_write,
            settings=settings,
        )

        tr["appended"] = result.get("appended", 0)
        tr["updated"]  = result.get("updated",  0)
        tr["skipped"]  = result.get("skipped",  0)
        tr["executed"] = result.get("executed", False)
        if result.get("error"):
            tr["error"] = result["error"]

        total_appended += tr["appended"]
        total_updated  += tr["updated"]
        total_skipped  += tr["skipped"]
        target_results.append(tr)

    base["targets"]        = target_results
    base["total_appended"] = total_appended
    base["total_updated"]  = total_updated
    base["total_skipped"]  = total_skipped
    base["executed"]       = not dry_run and any(tr.get("executed") for tr in target_results)
    base["ok"]             = all(tr.get("error") is None for tr in target_results)
    base["duration_ms"]    = int((time.time() - t0) * 1000)
    return base


def _preview_row(row: dict) -> dict:
    """プレビュー表示用にrow値を短縮する。"""
    return {k: str(v)[:50] for k, v in list(row.items())[:6]}


def _block_reason(auth_mode: str, dry_run: bool, manual_execute: bool) -> str:
    reasons = []
    if auth_mode == "disabled":
        reasons.append("auth_mode=disabled")
    if dry_run:
        reasons.append("dry_run=True")
    if not manual_execute:
        reasons.append("manual_execute=False")
    return " / ".join(reasons) if reasons else "実行可能"
