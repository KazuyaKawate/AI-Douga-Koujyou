"""BETA-2 Owner decision activation preview.

This is an in-memory projection adapter inside the existing Sales Engine. It
can preview already-evidenced Owner decisions, but never persists or executes.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


PHASE = "BETA-2"
RESPONSIVE_MIN_WIDTH = 360

SAFETY: dict[str, bool] = {
    "local_first": True,
    "dry_run": True,
    "proposal_only": True,
    "projection_only": True,
    "read_only": True,
    "review_required": True,
    "execute_allowed": False,
    "quick_actions_enabled": False,
    "google_write_allowed": False,
    "workspace_write_allowed": False,
    "mail_send_allowed": False,
    "inquiry_send_allowed": False,
    "contract_allowed": False,
    "payment_allowed": False,
    "production_allowed": False,
    "knowledge_registration_allowed": False,
    "learning_registration_allowed": False,
    "external_request_sent": False,
    "git_push_executed": False,
    "release_executed": False,
}

DECISION_SPECS: tuple[dict[str, Any], ...] = (
    {"decision_id": "B2-OD-01", "key": "brand_name", "label": "ブランド名", "proposal_value": "AIOS", "source": "existing brand candidate"},
    {"decision_id": "B2-OD-02", "key": "sales_service", "label": "販売サービス", "proposal_value": "REV-S01 note記事制作スターター", "source": "existing service catalog candidate"},
    {"decision_id": "B2-OD-03", "key": "price_jpy", "label": "価格", "proposal_value": 16_500, "source": "existing catalog candidate"},
    {"decision_id": "B2-OD-04", "key": "tax_treatment", "label": "税込／税別", "proposal_value": None, "source": "owner value required"},
    {"decision_id": "B2-OD-05", "key": "delivery_days", "label": "納期", "proposal_value": "3–5営業日", "source": "existing catalog candidate"},
    {"decision_id": "B2-OD-06", "key": "intake_limit", "label": "受付上限", "proposal_value": 1, "source": "limited beta candidate"},
    {"decision_id": "B2-OD-07", "key": "business_hours", "label": "営業時間", "proposal_value": None, "source": "owner value required"},
    {"decision_id": "B2-OD-08", "key": "first_response_sla", "label": "初回返信SLA", "proposal_value": None, "source": "owner value required"},
    {"decision_id": "B2-OD-09", "key": "inquiry_channel", "label": "問い合わせチャネル", "proposal_value": None, "source": "owner value required"},
    {"decision_id": "B2-OD-10", "key": "operations_owner", "label": "運営責任者", "proposal_value": None, "source": "owner value required"},
    {"decision_id": "B2-OD-11", "key": "beta_capacity", "label": "Beta人数", "proposal_value": 1, "source": "limited beta candidate"},
)

_REQUIRED_APPROVAL_FIELDS = {"value", "evidence_id", "approved_by", "approved_at"}


def _validate_approved_decisions(
    approved_decisions: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    if approved_decisions is None:
        return {}
    if not isinstance(approved_decisions, Mapping):
        raise ValueError("approved decisions must be a mapping")
    allowed_keys = {spec["key"] for spec in DECISION_SPECS}
    unknown = set(approved_decisions) - allowed_keys
    if unknown:
        raise ValueError(f"unknown BETA-2 owner decision: {sorted(unknown)[0]}")
    validated: dict[str, dict[str, Any]] = {}
    for key, record in approved_decisions.items():
        if not isinstance(record, Mapping):
            raise ValueError(f"owner decision {key} must be a mapping")
        missing = _REQUIRED_APPROVAL_FIELDS - set(record)
        if missing:
            raise ValueError(f"owner decision {key} missing approval evidence")
        if record["value"] is None or any(not str(record[field]).strip() for field in _REQUIRED_APPROVAL_FIELDS - {"value"}):
            raise ValueError(f"owner decision {key} has empty approval evidence")
        validated[key] = dict(record)
    return validated


def build_owner_activation(
    approved_decisions: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a non-persistent activation preview from explicit evidence."""
    approved = _validate_approved_decisions(approved_decisions)
    decisions: list[dict[str, Any]] = []
    for spec in DECISION_SPECS:
        record = approved.get(spec["key"])
        decisions.append(
            {
                **deepcopy(spec),
                "display_value": record["value"] if record else spec["proposal_value"],
                "status": "APPROVED_PROJECTION" if record else "PROPOSAL",
                "evidence_id": record["evidence_id"] if record else None,
                "approved_by": record["approved_by"] if record else None,
                "approved_at": record["approved_at"] if record else None,
                "persisted": False,
                **SAFETY,
            }
        )
    approved_count = len(approved)
    return {
        "decisions": decisions,
        "approved_count": approved_count,
        "total_count": len(DECISION_SPECS),
        "completion_pct": round(approved_count / len(DECISION_SPECS) * 100, 1),
        "remaining_count": len(DECISION_SPECS) - approved_count,
        "activation_ready": approved_count == len(DECISION_SPECS),
        "persisted": False,
        **SAFETY,
    }


def _approved_keys(activation: Mapping[str, Any]) -> set[str]:
    return {
        str(item["key"])
        for item in activation["decisions"]
        if item["status"] == "APPROVED_PROJECTION"
    }


def build_launch_gates(
    approved_decisions: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    activation = build_owner_activation(approved_decisions)
    approved = _approved_keys(activation)
    business_keys = {"brand_name", "sales_service", "price_jpy", "tax_treatment"}
    operations_keys = {
        "delivery_days", "intake_limit", "business_hours", "first_response_sla",
        "inquiry_channel", "operations_owner", "beta_capacity",
    }
    gates = (
        ("Business Gate", "READY" if business_keys <= approved else "WARNING", "brand/service/price/tax Owner evidence"),
        ("Legal Gate", "BLOCKED", "contract/privacy approval is outside current decision evidence"),
        ("Technical Gate", "READY", "local projection and DryRun contract verified"),
        ("Operations Gate", "READY" if operations_keys <= approved else "WARNING", "delivery/capacity/hours/SLA/channel/owner evidence"),
        ("Revenue Gate", "READY" if {"price_jpy", "tax_treatment"} <= approved else "BLOCKED", "verified actual only; price/tax approval required"),
        ("Owner Gate", "READY" if activation["activation_ready"] else "BLOCKED", "all 11 Owner decisions require evidence"),
    )
    return [
        {"sequence": index, "gate": name, "status": status, "basis": basis, **SAFETY}
        for index, (name, status, basis) in enumerate(gates, start=1)
    ]


def build_executive_projection(
    approved_decisions: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    activation = build_owner_activation(approved_decisions)
    gates = build_launch_gates(approved_decisions)
    ready = sum(gate["status"] == "READY" for gate in gates)
    blocking = [gate["gate"] for gate in gates if gate["status"] == "BLOCKED"]
    return {
        "launch_readiness_pct": round(ready / len(gates) * 100, 1),
        "launch_readiness_basis": "READY gates / total gates",
        "owner_completion_pct": activation["completion_pct"],
        "remaining_decisions": activation["remaining_count"],
        "blocking_items": blocking,
        "blocking_item_count": len(blocking),
        "launch_status": "NO_GO" if blocking else "REVIEW_REQUIRED",
        **SAFETY,
    }


def build_commander_proposals() -> list[dict[str, Any]]:
    rows = (
        ("残作業", "Owner決定11件へ値・Evidence・承認者・承認日時を付与", "未承認値のActivation"),
        ("公開前確認", "Legal/Revenue/Owner GateのBLOCKEDを個別Review", "Gate判定の読み違い"),
        ("リスク", "税・契約・privacy・責任者の欠損を最優先で解消", "法務・請求・誤送信"),
        ("次アクション", "Ownerが候補値を承認または差戻ししEvidenceを記録", "AIによる承認代行"),
    )
    return [
        {"sequence": index, "category": category, "proposal": proposal, "risk": risk, "status": "PROPOSAL", **SAFETY}
        for index, (category, proposal, risk) in enumerate(rows, start=1)
    ]


def build_customer_workspace_template(
    activation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    owner = activation or build_owner_activation()
    return {
        "beta_status": {"status": "NOT_STARTED", "customer_count": 0, "capacity": 1},
        "owner_approval": {
            "status": "READY_FOR_SEPARATE_LAUNCH_REVIEW" if owner["activation_ready"] else "PENDING",
            "approved_count": owner["approved_count"],
            "total_count": owner["total_count"],
        },
        "real_customer_count": 0,
        "persisted": False,
        **SAFETY,
    }


def build_knowledge_candidates() -> dict[str, Any]:
    candidates = [
        {"candidate_id": "B2-KC-001", "title": "Owner Decision Evidence contract", "status": "REGISTRATION_CANDIDATE", **SAFETY},
        {"candidate_id": "B2-KC-002", "title": "Launch Gate status derivation", "status": "REGISTRATION_CANDIDATE", **SAFETY},
    ]
    return {
        "candidates": candidates,
        "candidate_count": len(candidates),
        "registered_count": 0,
        "registration_status": "NOT_REGISTERED",
        **SAFETY,
    }


def build_owner_decision_activation(
    approved_decisions: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    activation = build_owner_activation(approved_decisions)
    executive = build_executive_projection(approved_decisions)
    return {
        "phase": PHASE,
        "status": "OWNER_DECISION_REVIEW_REQUIRED",
        "owner_decision_activation": activation,
        "launch_gate": {"gates": build_launch_gates(approved_decisions), **SAFETY},
        "executive_dashboard": executive,
        "commander": {"proposals": build_commander_proposals(), **SAFETY},
        "customer_workspace": build_customer_workspace_template(activation),
        "revenue_engine": {
            "verified_actual_revenue_jpy": 0,
            "proposal_revenue_included": False,
            "recognition_basis": "VERIFIED_ACTUAL_ONLY",
            **SAFETY,
        },
        "marketing_dashboard": {"public_status": "NOT_PUBLISHED", "owner_approval_required": True, **SAFETY},
        "sales_engine": {"activation_preview_only": True, "intake_allowed": False, **SAFETY},
        "google_workspace_read_layer": {"mode": "READ_ONLY", "connected": False, "record_count": 0, "write_observed": False, **SAFETY},
        "knowledge_platform": build_knowledge_candidates(),
        "existing_surface_mapping": {
            "Executive Dashboard": "readiness/completion/remaining/blockers projection",
            "Sales Engine": "owner activation preview",
            "Revenue Engine": "verified actual only",
            "Customer Workspace": "beta status and owner approval templates",
            "Marketing Dashboard": "not-published owner approval status",
            "Commander": "four proposals",
            "Google Workspace Read Layer": "disconnected read-only projection",
            "Knowledge Platform": "explicit requirement 7; candidates only",
        },
        "development_policy_alignment": {"first_revenue_priority": True, "existing_engines_only": True, "new_engine_added": False},
        "ui": {"design_system": "AIOS Design System v1.0", "responsive_min_width_px": RESPONSIVE_MIN_WIDTH, "desktop_supported": True, "quick_actions_enabled": False},
        **SAFETY,
    }


__all__ = [
    "DECISION_SPECS", "PHASE", "RESPONSIVE_MIN_WIDTH", "SAFETY",
    "build_commander_proposals", "build_customer_workspace_template",
    "build_executive_projection", "build_knowledge_candidates", "build_launch_gates",
    "build_owner_activation", "build_owner_decision_activation",
]
