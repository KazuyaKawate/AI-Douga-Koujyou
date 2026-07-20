"""OWNER-6 human-only approval capture and read-only projections.

The capture is deliberately in-memory.  It does not update business logic,
schemas, queues, configuration, workspaces, or external systems.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any, Mapping, Sequence

from src.operations.owner5_evidence_review import empty_evidence_register
from src.operations.owner4_configuration import DECISIONS


REVIEW_LAYER = "OWNER6_REVIEW_LAYER"
REQUIRED_APPROVAL_FIELDS = (
    "proposal", "evidence_id", "evidence_source", "owner", "reviewer",
    "approval_date", "effective_date", "rollback_impact",
)

SAFETY = {
    "local_first": True,
    "dry_run": True,
    "approval_required": True,
    "review_required": True,
    "execute_allowed": False,
    "production_allowed": False,
    "workspace_write_allowed": False,
    "google_communication_allowed": False,
    "external_communication_allowed": False,
    "business_logic_write_allowed": False,
}


def empty_approval_register() -> list[dict[str, Any]]:
    """Return the canonical 20-row OWNER-6 review form."""
    rows = []
    for row in empty_evidence_register():
        rows.append({
            "decision_id": row["decision_id"],
            "title": row["title"],
            "current_status": "PROPOSED",
            "proposal": None,
            "evidence_id": None,
            "evidence_source": None,
            "owner": None,
            "reviewer": None,
            "approval_date": None,
            "effective_date": None,
            "rollback_impact": None,
            "remarks": None,
        })
    return rows


def _text(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value or "").strip()


def capture_owner_approval(
    record: Mapping[str, Any], *, input_channel: str, human_attested: bool
) -> dict[str, Any]:
    """Validate one explicit human approval and return an in-memory copy.

    No caller can omit the Review Layer channel or human attestation.  Evidence
    completion alone never invokes this function and never changes status.
    """
    if input_channel != REVIEW_LAYER:
        raise PermissionError("Owner approval input is allowed only in OWNER-6 Review Layer")
    if human_attested is not True:
        raise PermissionError("explicit human Owner attestation is required")

    captured = deepcopy(dict(record))
    expected = {decision_id: title for decision_id, _, title in DECISIONS}
    decision_id = captured.get("decision_id")
    if decision_id not in expected or captured.get("title") != expected[decision_id]:
        raise ValueError("unknown or modified OWNER-6 decision")
    missing = [field for field in REQUIRED_APPROVAL_FIELDS if not _text(captured.get(field))]
    if missing:
        raise ValueError(f"approval evidence incomplete: {', '.join(missing)}")
    approval_date = _text(captured["approval_date"])
    effective_date = _text(captured["effective_date"])
    if effective_date < approval_date:
        raise ValueError("Effective Date cannot precede Approval Date")

    for field in REQUIRED_APPROVAL_FIELDS + ("remarks",):
        captured[field] = _text(captured.get(field)) or None
    captured["current_status"] = "APPROVED"
    captured["capture_channel"] = REVIEW_LAYER
    captured["human_attested"] = True
    return captured


def project_approval_capture(register: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Validate and project the canonical approval register without writes."""
    rows = [deepcopy(dict(row)) for row in (register or empty_approval_register())]
    expected = [(decision_id, title) for decision_id, _, title in DECISIONS]
    actual = [(row.get("decision_id"), row.get("title")) for row in rows]
    if actual != expected:
        raise ValueError("OWNER-6 register must contain all 20 canonical decisions")

    for row in rows:
        if row.get("current_status") not in {"PROPOSED", "APPROVED"}:
            raise ValueError("OWNER-6 status must be PROPOSED or APPROVED")
        complete = all(_text(row.get(field)) for field in REQUIRED_APPROVAL_FIELDS)
        row["evidence_complete"] = complete
        if row["current_status"] == "APPROVED":
            if not complete or row.get("capture_channel") != REVIEW_LAYER or row.get("human_attested") is not True:
                raise ValueError(f"APPROVED decision lacks human Review Layer capture: {row['decision_id']}")

    evidence_ids = [_text(row.get("evidence_id")) for row in rows]
    populated_ids = [value for value in evidence_ids if value]
    if len(populated_ids) != len(set(populated_ids)):
        raise ValueError("OWNER-6 Evidence ID must be unique")

    approved = sum(row["current_status"] == "APPROVED" for row in rows)
    evidence_complete = sum(row["evidence_complete"] for row in rows)
    blockers = [row["decision_id"] for row in rows if row["current_status"] != "APPROVED"]
    launch_ready = approved == len(rows) and evidence_complete == len(rows)
    return {
        "phase": "OWNER-6",
        "entrypoint": "Business Home",
        "review_layer": {"input_allowed": True, "human_only": True, "persistence": "SESSION_MEMORY_ONLY"},
        "safety": dict(SAFETY),
        "review_records": rows,
        "business_home": {
            "approval_progress": f"{approved}/20", "approved": approved,
            "remaining": 20 - approved, "evidence_missing": 20 - evidence_complete,
            "launch_blockers": blockers,
        },
        "executive": {
            "approval_percent": approved * 5,
            "evidence_percent": evidence_complete * 5,
            "launch_percent": 100 if launch_ready else 0,
        },
        "commander": {
            "mode": "PROPOSAL_ONLY", "approve_allowed": False,
            "reject_allowed": False, "quick_actions_enabled": False,
        },
        "final_judgements": [
            "OWNER APPROVAL CAPTURE READY",
            "OWNER INPUT REQUIRED" if approved < 20 else "OWNER INPUT COMPLETE",
            "LAUNCH READY" if launch_ready else "LAUNCH NO-GO",
        ],
    }
