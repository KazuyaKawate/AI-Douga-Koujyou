"""sync_executor — Orchestrator for Google Sheets Connector (v5.2 Phase 3).

Execution flow:
  1. load_settings()
  2. read_local_data() — local JSON files
  3. read_sheet()      — Google Sheet rows (sample data when auth_mode='disabled')
  4. diff_records()    — calculate diff
  5. generate preview  — no writes
  6. execute           — only if manual_execute=True, dry_run=False, auth_mode != 'disabled'

Rules (enforced in code):
  - No automatic execution.
  - dry_run=True by default.
  - manual_execute=False by default.
  - auth_mode='disabled' by default → no API calls.
  - Phase 3: gspread/google-auth readiness checks added; actual writes remain Phase 4+.
"""
from __future__ import annotations
import time
from datetime import datetime, timezone

from src.workspace.sync_validator import load_settings, load_merged_settings, get_enabled_targets
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
        "phase":            "Phase 4-2 (local config override, read-only)",
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


def _block_reason(auth_mode: str, dry_run: bool, manual_execute: bool) -> str:
    reasons = []
    if auth_mode == "disabled":
        reasons.append("auth_mode=disabled")
    if dry_run:
        reasons.append("dry_run=True")
    if not manual_execute:
        reasons.append("manual_execute=False")
    return " / ".join(reasons) if reasons else "実行可能"
