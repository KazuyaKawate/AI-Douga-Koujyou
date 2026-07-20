"""OWNER-5 evidence review projection; no persistence or approval actions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from src.operations.owner4_configuration import DECISIONS


SAFETY = {
    "local_first": True,
    "dry_run": True,
    "approval_required": True,
    "review_required": True,
    "projection_only": True,
    "execute_allowed": False,
    "workspace_write_allowed": False,
    "production_allowed": False,
    "google_communication_allowed": False,
    "external_communication_allowed": False,
}

EVIDENCE_FIELDS = (
    "evidence_id", "evidence_source", "approved_by", "reviewed_by",
    "approval_date", "effective_date", "rollback_impact",
)


def empty_evidence_register() -> list[dict[str, Any]]:
    """Return the 20-row review form without inventing owner evidence."""
    return [
        {
            "decision_id": decision_id,
            "title": title,
            "current_status": "PROPOSED",
            "proposal": None,
            "evidence_id": None,
            "evidence_source": None,
            "approved_by": None,
            "reviewed_by": None,
            "approval_date": None,
            "effective_date": None,
            "rollback_impact": None,
            "notes": None,
        }
        for decision_id, _, title in DECISIONS
    ]


def project_evidence_review(register: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Validate explicit review records and return read-only surface projections.

    Evidence completion never changes a status. APPROVED must be supplied by a
    human-reviewed input and is rejected unless its evidence is complete.
    """
    rows = list(register) if register is not None else empty_evidence_register()
    expected_ids = [row[0] for row in DECISIONS]
    if len(rows) != 20 or [row.get("decision_id") for row in rows] != expected_ids:
        raise ValueError("OWNER-5 register must contain all 20 decisions in canonical order")

    normalized: list[dict[str, Any]] = []
    for (decision_id, _, title), source in zip(DECISIONS, rows):
        row = deepcopy(dict(source))
        if row.get("title") != title:
            raise ValueError(f"decision title mismatch: {decision_id}")
        status = row.get("current_status")
        if status not in {"PROPOSED", "APPROVED", "REJECTED"}:
            raise ValueError(f"invalid decision state: {status!r}")
        complete = bool(row.get("proposal")) and all(bool(str(row.get(field) or "").strip()) for field in EVIDENCE_FIELDS)
        if status == "APPROVED" and not complete:
            raise ValueError(f"APPROVED decision lacks OWNER-5 evidence: {decision_id}")
        row["evidence_complete"] = complete
        normalized.append(row)

    evidence_ids = [str(row.get("evidence_id") or "").strip() for row in normalized]
    populated_ids = [value for value in evidence_ids if value]
    if len(populated_ids) != len(set(populated_ids)):
        raise ValueError("OWNER-5 Evidence ID must be unique")

    approved = sum(row["current_status"] == "APPROVED" for row in normalized)
    evidence_complete = sum(row["evidence_complete"] for row in normalized)
    remaining = 20 - approved
    blockers = [row["decision_id"] for row in normalized if row["current_status"] != "APPROVED"]
    launch_ready = approved == 20 and evidence_complete == 20
    return {
        "phase": "OWNER-5",
        "entrypoint": "Business Home",
        "safety": dict(SAFETY),
        "review_records": normalized,
        "business_home": {
            "approval_progress": f"{approved}/20",
            "evidence_missing": 20 - evidence_complete,
            "approved_count": approved,
            "remaining_count": remaining,
            "launch_blockers": blockers,
        },
        "commander": {
            "mode": "PROPOSAL_ONLY", "proposals": [row["proposal"] for row in normalized],
            "approve_allowed": False, "reject_allowed": False, "quick_actions_enabled": False,
        },
        "executive": {
            "approval_percent": approved * 100 // 20,
            "evidence_completion_percent": evidence_complete * 100 // 20,
            "launch_ready_percent": 100 if launch_ready else 0,
        },
        "customer_workspace": [
            {"decision_id": row["decision_id"], "title": row["title"], "status": row["current_status"]}
            for row in normalized
        ],
        "final_judgements": [
            "OWNER APPROVAL WORKFLOW READY", "OWNER EVIDENCE REQUIRED",
            "LAUNCH READY" if launch_ready else "LAUNCH NO-GO",
        ],
    }
