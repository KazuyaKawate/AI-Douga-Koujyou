"""OA-DECISION FREEZE read-only Owner review projection.

Decision records are validated and projected in memory.  This module never
persists a decision or performs an external action.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


PHASE = "OA-DECISION FREEZE"
STATUSES = ("PROPOSAL", "APPROVED", "REJECTED")
RESPONSIVE_MIN_WIDTH = 360

SAFETY: dict[str, bool] = {
    "local_first": True,
    "dry_run": True,
    "projection_only": True,
    "read_only": True,
    "review_required": True,
    "execute_allowed": False,
    "quick_actions_enabled": False,
    "external_communication_allowed": False,
    "production_allowed": False,
    "workspace_write_allowed": False,
    "google_write_allowed": False,
    "sns_send_allowed": False,
    "mail_send_allowed": False,
    "contract_allowed": False,
    "payment_allowed": False,
    "knowledge_registration_allowed": False,
    "learning_registration_allowed": False,
    "git_push_executed": False,
    "release_executed": False,
}

DECISION_SPECS: tuple[dict[str, Any], ...] = (
    {"decision_id": "OA-DF-01", "key": "brand_name", "label": "ブランド名", "proposal_value": "AIOS"},
    {"decision_id": "OA-DF-02", "key": "sales_service", "label": "販売サービス", "proposal_value": "REV-S01 note記事制作スターター"},
    {"decision_id": "OA-DF-03", "key": "price", "label": "価格", "proposal_value": 16_500},
    {"decision_id": "OA-DF-04", "key": "tax_treatment", "label": "税込/税別", "proposal_value": None},
    {"decision_id": "OA-DF-05", "key": "delivery", "label": "納期", "proposal_value": "3–5営業日"},
    {"decision_id": "OA-DF-06", "key": "intake_limit", "label": "受付上限", "proposal_value": 1},
    {"decision_id": "OA-DF-07", "key": "inquiry_channel", "label": "問い合わせ窓口", "proposal_value": None},
    {"decision_id": "OA-DF-08", "key": "business_hours", "label": "営業時間", "proposal_value": None},
    {"decision_id": "OA-DF-09", "key": "sla", "label": "SLA", "proposal_value": None},
    {"decision_id": "OA-DF-10", "key": "operations_owner", "label": "運営責任者", "proposal_value": None},
    {"decision_id": "OA-DF-11", "key": "beta_start_condition", "label": "Beta開始条件", "proposal_value": "Owner/Legal/Revenue/Launch Ready 100%"},
)

EVIDENCE_FIELDS = ("decision_date", "approved_by", "reason", "previous_value")
READINESS_KEYS = {
    "business_ready_pct": {"brand_name", "sales_service", "price", "tax_treatment", "delivery", "intake_limit"},
    "legal_ready_pct": {"tax_treatment", "inquiry_channel", "sla", "operations_owner"},
    "revenue_ready_pct": {"sales_service", "price", "tax_treatment", "intake_limit"},
    "launch_ready_pct": {spec["key"] for spec in DECISION_SPECS},
}


def _validate_records(records: Mapping[str, Mapping[str, Any]] | None) -> dict[str, dict[str, Any]]:
    if records is None:
        return {}
    if not isinstance(records, Mapping):
        raise ValueError("decision records must be a mapping")
    allowed = {spec["key"] for spec in DECISION_SPECS}
    unknown = set(records) - allowed
    if unknown:
        raise ValueError(f"unknown Owner decision: {sorted(unknown)[0]}")
    validated: dict[str, dict[str, Any]] = {}
    for key, raw in records.items():
        if not isinstance(raw, Mapping):
            raise ValueError(f"decision {key} must be a mapping")
        status = str(raw.get("status", "")).upper()
        if status not in STATUSES:
            raise ValueError(f"decision {key} has invalid status")
        record = dict(raw)
        if status in {"APPROVED", "REJECTED"}:
            missing = [field for field in EVIDENCE_FIELDS if field not in record]
            if missing:
                raise ValueError(f"decision {key} missing evidence: {missing[0]}")
            if record.get("value") is None and status == "APPROVED":
                raise ValueError(f"decision {key} approved value is required")
            for field in ("decision_date", "approved_by", "reason"):
                if not str(record[field]).strip():
                    raise ValueError(f"decision {key} has empty evidence: {field}")
        validated[key] = record
    return validated


def build_decision_dashboard(
    records: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the 11-item decision dashboard without persistence."""
    validated = _validate_records(records)
    decisions: list[dict[str, Any]] = []
    for spec in DECISION_SPECS:
        record = validated.get(spec["key"], {})
        status = str(record.get("status", "PROPOSAL")).upper()
        decisions.append({
            **deepcopy(spec),
            "status": status,
            "display_value": record.get("value", spec["proposal_value"]),
            "decision_date": record.get("decision_date"),
            "approved_by": record.get("approved_by"),
            "reason": record.get("reason"),
            "previous_value": record.get("previous_value"),
            "persisted": False,
            **SAFETY,
        })
    counts = {status: sum(item["status"] == status for item in decisions) for status in STATUSES}
    return {
        "decisions": decisions,
        "counts": counts,
        "total_count": len(decisions),
        "persisted": False,
        **SAFETY,
    }


def build_executive_dashboard(
    records: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    dashboard = build_decision_dashboard(records)
    approved = {item["key"] for item in dashboard["decisions"] if item["status"] == "APPROVED"}
    decided = {item["key"] for item in dashboard["decisions"] if item["status"] != "PROPOSAL"}

    def percentage(keys: set[str], passed: set[str]) -> float:
        return round(len(keys & passed) / len(keys) * 100, 1)

    metrics = {
        "owner_completion_pct": percentage({spec["key"] for spec in DECISION_SPECS}, decided),
        **{name: percentage(keys, approved) for name, keys in READINESS_KEYS.items()},
    }
    return {
        **metrics,
        "basis": {
            "owner_completion_pct": "APPROVED + REJECTED / 11",
            **{name: f"APPROVED required decisions / {len(keys)}" for name, keys in READINESS_KEYS.items()},
        },
        "launch_status": "REVIEW_REQUIRED" if metrics["launch_ready_pct"] == 100.0 else "NO_GO",
        **SAFETY,
    }


def build_commander_projection(
    records: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    proposals = [
        deepcopy(item)
        for item in build_decision_dashboard(records)["decisions"]
        if item["status"] == "PROPOSAL"
    ]
    return {
        "items": proposals,
        "proposal_count": len(proposals),
        "approve_operation_allowed": False,
        **SAFETY,
    }


def build_knowledge_candidates(
    records: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    candidates = [
        {
            "candidate_id": f'OA-KC-{index:02d}',
            "decision_id": item["decision_id"],
            "title": f'{item["label"]} Decision候補',
            "status": "DECISION_CANDIDATE",
            **SAFETY,
        }
        for index, item in enumerate(build_decision_dashboard(records)["decisions"], start=1)
        if item["status"] == "PROPOSAL"
    ]
    return {"candidates": candidates, "registered_count": 0, "auto_registration_allowed": False, **SAFETY}


def build_owner_decision_freeze(
    records: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": "REVIEW_REQUIRED",
        "owner_decision_dashboard": build_decision_dashboard(records),
        "executive_dashboard": build_executive_dashboard(records),
        "commander": build_commander_projection(records),
        "knowledge": build_knowledge_candidates(records),
        "ui": {
            "responsive_min_width_px": RESPONSIVE_MIN_WIDTH,
            "quick_actions_enabled": False,
            "review_session_only": True,
        },
        **SAFETY,
    }


__all__ = [
    "DECISION_SPECS", "EVIDENCE_FIELDS", "PHASE", "READINESS_KEYS", "RESPONSIVE_MIN_WIDTH",
    "SAFETY", "STATUSES", "build_commander_projection", "build_decision_dashboard",
    "build_executive_dashboard", "build_knowledge_candidates", "build_owner_decision_freeze",
]
