"""OWNER-4 read-only Decision Register projection.

This adapter accepts an explicit, reviewed register snapshot and returns an
in-memory projection.  It never persists, approves, or executes a decision.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence


ALLOWED_STATES = frozenset({"PROPOSED", "APPROVED", "REJECTED"})
DECISIONS: tuple[tuple[str, str, str], ...] = (
    ("OWNER3-OD-01", "brand", "正式ブランド"),
    ("OWNER3-OD-02", "sales_entity", "販売主体"),
    ("OWNER3-OD-03", "service_id", "Service ID"),
    ("OWNER3-OD-04", "price", "価格"),
    ("OWNER3-OD-05", "tax_classification", "税区分"),
    ("OWNER3-OD-06", "business_hours", "営業時間"),
    ("OWNER3-OD-07", "sla", "SLA"),
    ("OWNER3-OD-08", "inquiry_contact", "問い合わせ先"),
    ("OWNER3-OD-09", "delivery_term", "納期"),
    ("OWNER3-OD-10", "revision_limit", "修正回数"),
    ("OWNER3-OD-11", "payment_method", "支払方法"),
    ("OWNER3-OD-12", "refund_policy", "返金条件"),
    ("OWNER3-OD-13", "terms", "利用規約"),
    ("OWNER3-OD-14", "privacy", "Privacy"),
    ("OWNER3-OD-15", "public_url", "公開URL"),
    ("OWNER3-OD-16", "beta_start_date", "β開始日"),
    ("OWNER3-OD-17", "intake_limit", "受付上限"),
    ("OWNER3-OD-18", "operations_owner", "運営責任者"),
    ("OWNER3-OD-19", "stop_owner", "停止責任者"),
    ("OWNER3-OD-20", "launch_approval", "Launch承認"),
)

SAFETY = {
    "local_first": True, "dry_run": True, "approval_required": True,
    "review_required": True, "projection_only": True,
    "workspace_write_allowed": False, "google_communication_allowed": False,
    "external_communication_allowed": False, "production_allowed": False,
}

_APPROVAL_FIELDS = ("approved_by", "approved_at", "effective_at", "evidence_ref")


def proposed_register() -> list[dict[str, Any]]:
    """Return the OWNER-3 baseline without inventing approval evidence."""
    return [
        {"decision_id": decision_id, "key": key, "label": label, "status": "PROPOSED", "value": None}
        for decision_id, key, label in DECISIONS
    ]


def project_owner_configuration(register: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    """Validate all 20 states and project only evidence-complete APPROVED rows."""
    rows = list(register) if register is not None else proposed_register()
    expected_ids = [item[0] for item in DECISIONS]
    if len(rows) != len(DECISIONS) or [row.get("decision_id") for row in rows] != expected_ids:
        raise ValueError("OWNER-4 register must contain all 20 decisions in canonical order")

    approved: dict[str, Any] = {}
    normalized: list[dict[str, Any]] = []
    counts = {state: 0 for state in sorted(ALLOWED_STATES)}
    for (_, canonical_key, canonical_label), source in zip(DECISIONS, rows):
        row = deepcopy(dict(source))
        status = row.get("status")
        if status not in ALLOWED_STATES:
            raise ValueError(f"invalid decision state: {status!r}")
        if row.get("key", canonical_key) != canonical_key:
            raise ValueError(f"decision key mismatch: {row.get('decision_id')}")
        if status == "APPROVED":
            if row.get("value") in (None, "") or any(not str(row.get(field, "")).strip() for field in _APPROVAL_FIELDS):
                raise ValueError(f"APPROVED decision lacks evidence: {row.get('decision_id')}")
            approved[canonical_key] = row["value"]
        counts[status] += 1
        normalized.append({**row, "key": canonical_key, "label": canonical_label, "projected": status == "APPROVED"})

    blockers = [row["label"] for row in normalized if row["status"] != "APPROVED"]
    legal_keys = {"tax_classification", "refund_policy", "terms", "privacy"}
    legal_ready = all(row["status"] == "APPROVED" for row in normalized if row["key"] in legal_keys)
    launch_ready = not blockers and approved.get("launch_approval") == "GO"
    return {
        "phase": "OWNER-4", "entrypoint": "Business Home", "safety": dict(SAFETY),
        "decision_status": normalized, "owner_configuration": approved,
        "customer_workspace": [{"decision_id": row["decision_id"], "label": row["label"], "status": row["status"]} for row in normalized],
        "commander": {"mode": "PROPOSAL_ONLY", "approve_allowed": False, "quick_actions_enabled": False},
        "revenue": {"basis": "VERIFIED_ACTUAL_ONLY", "changed": False},
        "executive": {
            "owner_completion_percent": counts["APPROVED"] * 100 // len(DECISIONS),
            "approved": counts["APPROVED"], "remaining": len(DECISIONS) - counts["APPROVED"],
            "launch_blockers": blockers, "legal_status": "READY" if legal_ready else "BLOCKED",
            "business_status": "READY" if launch_ready else "BLOCKED",
        },
        "final_judgement": "OWNER CONFIGURATION READY" if launch_ready else "OWNER APPROVAL REQUIRED",
        "launch_judgement": "GO" if launch_ready else "LAUNCH NO-GO",
    }
