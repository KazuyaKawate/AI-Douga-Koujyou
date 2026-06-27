"""sync_executor — Orchestrator for Google Sheets Connector (v5.2 Phase 2).

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
"""
from __future__ import annotations
import time
from datetime import datetime, timezone

from src.workspace.sync_validator import load_settings, get_enabled_targets
from src.workspace.sheets_sync import read_local_data, get_mapping
from src.workspace.google_auth import get_auth_config, get_credential_status
from src.workspace.sheet_reader import read_sheet, get_reader_status
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
        "phase":            "Phase 2 (connector foundation)",
    }


def _block_reason(auth_mode: str, dry_run: bool, manual_execute: bool) -> str:
    reasons = []
    if auth_mode == "disabled":
        reasons.append("auth_mode=disabled")
    if dry_run:
        reasons.append("dry_run=True")
    if not manual_execute:
        reasons.append("manual_execute=False")
    return " / ".join(reasons) if reasons else "実行可能"
