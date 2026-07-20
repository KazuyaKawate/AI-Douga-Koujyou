"""SALES-3 first outreach preparation, local presentation only."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

PHASE = "SALES-3 FIRST OUTREACH PREPARATION"
OWNER_FIELDS = ("service_price", "tax_category", "payment_terms", "contracting_entity", "inquiry_contact")
OUTREACH_STATUSES = ("CANDIDATE", "SELECTED", "COPY_REVIEWED", "READY_FOR_OWNER_REVIEW")

SAFETY = {
    "local_first": True,
    "dry_run": True,
    "presentation_only": True,
    "review_required": True,
    "execute_allowed": False,
    "production_actions_enabled": False,
    "external_request_sent": False,
    "automatic_send_allowed": False,
    "persistence_allowed": False,
}


def owner_decision_panel(decisions: Mapping[str, Any] | None = None) -> dict[str, Any]:
    values = dict(decisions or {})
    items = {field: values.get(field) for field in OWNER_FIELDS}
    undecided = [field for field, value in items.items() if value is None or str(value).strip() == ""]
    return {"items": items, "undecided": undecided, "complete": not undecided, **SAFETY}


def first_outreach_planner(candidates: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for source in candidates or ():
        row = dict(source)
        status = str(row.get("status", "CANDIDATE")).upper()
        if status not in OUTREACH_STATUSES:
            raise ValueError(f"invalid outreach status: {status}")
        priority = row.get("priority")
        if isinstance(priority, bool) or not isinstance(priority, int) or priority < 1:
            raise ValueError("priority must be a positive integer")
        row["status"] = status
        row["actual"] = False
        rows.append(row)
    rows.sort(key=lambda item: item["priority"])
    selected = [row for row in rows if row["status"] in OUTREACH_STATUSES[1:]]
    return {"candidates": deepcopy(rows), "selected_count": len(selected), **SAFETY}


def outreach_evidence(evidence: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for source in evidence or ():
        row = dict(source)
        if row.get("reply_status") not in (None, "NOT_SENT"):
            raise ValueError("reply_status must be NOT_SENT in DryRun preparation")
        row["reply_status"] = "NOT_SENT"
        row["send_date"] = row.get("send_date") or None
        row["evidence_id"] = row.get("evidence_id") or None
        row["actual"] = False
        rows.append(row)
    return {"planned_evidence": rows, "actual_evidence_count": 0, **SAFETY}


def readiness_check(owner: Mapping[str, Any], planner: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    missing = list(owner["undecided"])
    if planner["selected_count"] != 1:
        missing.append("first_outreach_target_exactly_one")
    reviewed = any(row.get("copy_reviewed") is True for row in evidence["planned_evidence"])
    if not reviewed:
        missing.append("outreach_copy_review")
    return {
        "sales_start_allowed": not missing,
        "readiness_status": "READY_FOR_OWNER_REVIEW" if not missing else "NOT_READY",
        "undecided_items": missing,
        "owner_review_required": True,
        **SAFETY,
    }


def build_first_outreach_preparation(*, decisions=None, candidates=None, evidence=None) -> dict[str, Any]:
    owner = owner_decision_panel(decisions)
    planner = first_outreach_planner(candidates)
    planned_evidence = outreach_evidence(evidence)
    return {
        "phase": PHASE,
        "owner_decision_panel": owner,
        "first_outreach_planner": planner,
        "outreach_evidence": planned_evidence,
        "readiness_check": readiness_check(owner, planner, planned_evidence),
        **SAFETY,
    }

