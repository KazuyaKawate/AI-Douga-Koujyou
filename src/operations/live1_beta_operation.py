"""LIVE-1R local beta improvement cycle (presentation and DryRun only)."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

from src.revenue_engine.revenue11_analytics import build_dashboard as build_revenue11


SAFETY = {
    "local_first": True, "dry_run": True, "presentation_only": True,
    "owner_review_required": True, "execute_allowed": False,
    "production_actions_enabled": False, "external_request_sent": False,
    "actual_mutation_allowed": False,
}
OWNER_STATES = {"UNCONFIRMED", "CONFIRMED", "REJECTED"}


def _records(package: dict[str, Any], key: str) -> list[dict[str, Any]]:
    section = package.get(key, {})
    rows = section.get("records", []) if isinstance(section, dict) else []
    return deepcopy(rows) if isinstance(rows, list) else []


def allocate_evidence_id(records: Iterable[dict[str, Any]], observed_at: str) -> str:
    """Return the first unused date-scoped ID without changing supplied records."""
    prefix = f"LIVE1R-EV-{observed_at[:10].replace('-', '')}-"
    used = {str(row.get("evidence_id", "")) for row in records}
    sequence = 1
    while f"{prefix}{sequence:03d}" in used:
        sequence += 1
    return f"{prefix}{sequence:03d}"


def prepare_evidence_record(
    records: Iterable[dict[str, Any]], *, category: str, related_crm: str | None = None,
    related_revenue: str | None = None, observed_at: str | None = None,
) -> dict[str, Any]:
    """Prepare (but never persist) one Owner-reviewable Evidence record."""
    timestamp = observed_at or datetime.now(timezone.utc).isoformat()
    return {
        "evidence_id": allocate_evidence_id(records, timestamp), "observed_at": timestamp,
        "category": category, "related_crm": related_crm, "related_revenue": related_revenue,
        "owner_confirmation": "UNCONFIRMED", "status": "DRAFT / NOT SAVED",
    }


def build_seven_day_logs(start_date: str, daily_records: Iterable[dict[str, Any]] = ()) -> list[dict[str, Any]]:
    """Build seven log slots; missing days remain explicitly unrecorded."""
    supplied = {str(row.get("date")): deepcopy(row) for row in daily_records}
    start = date.fromisoformat(start_date)
    logs = []
    for offset in range(7):
        day = (start + timedelta(days=offset)).isoformat()
        source = supplied.get(day)
        logs.append(source if source is not None else {
            "date": day, "recording_status": "NOT RECORDED", "evidence_ids": [],
            "owner_confirmation": "UNCONFIRMED", "actuals": None,
        })
    return logs


def _improvements(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    proposals = []
    for index, row in enumerate(evidence, 1):
        finding = str(row.get("finding") or "").strip()
        if not finding:
            continue
        proposals.append({
            "proposal_id": f"LIVE1R-IMP-{index:03d}", "evidence_ids": [row.get("evidence_id")],
            "proposal": str(row.get("improvement_candidate") or f"Evidenceの所見をOwnerがレビューする: {finding}"),
            "priority": str(row.get("priority") or "MEDIUM").upper(),
            "recurrence_prevention": str(row.get("recurrence_prevention") or "Owner確認後に手順へ反映する"),
            "status": "PROPOSAL ONLY / OWNER REVIEW REQUIRED",
        })
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return sorted(proposals, key=lambda row: order.get(row["priority"], 3))


def build_weekly_summary(logs: list[dict[str, Any]], package: dict[str, Any]) -> dict[str, Any]:
    recorded = [row for row in logs if row.get("recording_status") == "RECORDED"]
    totals = {key: sum(int(row.get(key, 0)) for row in recorded) for key in
              ("posts", "inquiries", "crm_records", "feedback", "verified_revenue_jpy")}
    return {
        **totals, "improvement_items": len(_improvements(_records(package, "evidence"))),
        "recorded_days": len(recorded), "unrecorded_days": 7 - len(recorded),
        "calculation_basis": "RECORDED daily logs only", "status": "OWNER REVIEW REQUIRED",
    }


def build_beta_operation(owner_acceptance: dict[str, Any] | None = None,
                         actual_package: dict[str, Any] | None = None,
                         operation_date: str | None = None) -> dict[str, Any]:
    acceptance, package = deepcopy(owner_acceptance or {}), deepcopy(actual_package or {})
    revenue11 = build_revenue11(package)
    inquiries, feedback = revenue11["actual"]["inquiry_analytics"]["records"], revenue11["actual"]["feedback"]
    crm, evidence = _records(package, "crm"), _records(package, "evidence")
    daily_records = _records(package, "daily_logs")
    pending = [row for row in inquiries if row.get("reply_status") not in {"REPLIED", "OWNER REPLIED"}]
    today = operation_date or date.today().isoformat()
    logs = build_seven_day_logs(today, daily_records)
    improvements = _improvements(evidence)
    accepted = acceptance.get("decision") == "GO" and bool(acceptance.get("owner_name")) and bool(acceptance.get("review_date"))
    health = {
        "insufficient_evidence": [r for r in evidence if not r.get("evidence_id") or not r.get("observed_at")],
        "unconfirmed_crm": [r for r in crm if r.get("owner_confirmation", "UNCONFIRMED") != "CONFIRMED"],
        "unprocessed_inquiry": pending,
        "unconfirmed_feedback": [r for r in feedback if r.get("owner_confirmation", "UNCONFIRMED") != "CONFIRMED"],
    }
    summary = build_weekly_summary(logs, package)
    result = {
        "phase": "LIVE-1R BETA IMPROVEMENT CYCLE", "classification": "PRESENTATION ONLY", "operation_date": today,
        "owner_acceptance": {"completed": accepted, "status": "ACCEPTED" if accepted else "OWNER REVIEW REQUIRED"},
        "dashboard": {
            "todays_mission": "未処理Inquiryと未確認EvidenceをOwnerがレビューする",
            "pending_inquiry": {"count": len(pending), "records": pending}, "crm": {"count": len(crm), "records": crm},
            "evidence_count": len(evidence), "revenue": deepcopy(revenue11["actual"]["business_kpi"]),
            "analytics": deepcopy(revenue11["actual"]["inquiry_analytics"]), "improvement_tasks": improvements,
        },
        "feedback": feedback, "evidence": {"count": len(evidence), "records": evidence, "save_mode": "OWNER-PROVIDED LOCAL ONLY"},
        "daily_operation_log": logs[0], "seven_day_operation_logs": logs, "weekly_summary": summary,
        "weekly_operation_report": {"period_start": logs[0]["date"], "period_end": logs[-1]["date"], "summary": summary,
                                    "evidence_ids": [r.get("evidence_id") for r in evidence if r.get("evidence_id")],
                                    "status": "DRAFT / OWNER REVIEW REQUIRED"},
        "improvement_proposals": improvements, "operation_health": health,
        "completion": {"state": "READY_FOR_OWNER_REVIEW" if summary["recorded_days"] == 7 else "BETA_LOGGING_IN_PROGRESS",
                       "first_inquiry_observed": bool(inquiries), "seven_days_completed": summary["recorded_days"] == 7},
        "separation_contract": {"actual_source": "Owner-provided local records only", "projection_source": "Evidence-derived proposals only", "cross_mutation": False},
        "safety": deepcopy(SAFETY),
    }
    validate_beta_operation(result)
    return result


def validate_beta_operation(result: dict[str, Any]) -> None:
    if result.get("safety") != SAFETY: raise ValueError("unsafe LIVE-1R state")
    if result.get("separation_contract", {}).get("cross_mutation") is not False: raise ValueError("Actual mutation prohibited")
    if result.get("classification") != "PRESENTATION ONLY": raise ValueError("Presentation Only required")
    for row in result.get("evidence", {}).get("records", []):
        state = row.get("owner_confirmation", "UNCONFIRMED")
        if state not in OWNER_STATES: raise ValueError("invalid Owner confirmation state")
    known = {row.get("evidence_id") for row in result.get("evidence", {}).get("records", [])}
    for proposal in result.get("improvement_proposals", []):
        if not set(proposal.get("evidence_ids", [])).issubset(known): raise ValueError("proposal without Evidence")
