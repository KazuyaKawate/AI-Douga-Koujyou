"""SALES-3 offer conversion local-review projections.

Pure in-memory projections inside the existing Sales Engine.  No persistence,
send, contract, payment, registration, production, or external I/O path exists.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from .acquisition import build_revenue_mapping


class OfferStatus(str, Enum):
    INQUIRY = "INQUIRY"
    ESTIMATE_CREATED = "ESTIMATE_CREATED"
    APPROVAL_WAITING = "APPROVAL_WAITING"
    APPROVED = "APPROVED"
    ORDERED = "ORDERED"
    CLOSED = "CLOSED"


OFFER_STATES = tuple(item.value for item in OfferStatus)
RESPONSIVE_MIN_WIDTH = 360

SAFETY: dict[str, bool] = {
    "local_first": True,
    "dry_run": True,
    "proposal_only": True,
    "projection_only": True,
    "template_only": True,
    "review_required": True,
    "execute_allowed": False,
    "quick_actions_enabled": False,
    "save_allowed": False,
    "google_write_allowed": False,
    "workspace_write_allowed": False,
    "mail_send_allowed": False,
    "estimate_send_allowed": False,
    "contract_allowed": False,
    "payment_allowed": False,
    "knowledge_registration_allowed": False,
    "learning_registration_allowed": False,
    "production_allowed": False,
    "external_request_sent": False,
}


def _records(values: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if values is None:
        return []
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError("offers must be a sequence of mappings")
    rows: list[dict[str, Any]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise ValueError("each offer must be a mapping")
        row = dict(value)
        status = str(row.get("status", "INQUIRY")).strip().upper()
        if status not in OFFER_STATES:
            raise ValueError(f"invalid SALES-3 offer status: {status}")
        row["status"] = status
        amount = row.get("estimate_amount")
        if amount is not None and (
            isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0
        ):
            raise ValueError("estimate_amount must be a non-negative number")
        delivery_days = row.get("delivery_days")
        if delivery_days is not None and (
            isinstance(delivery_days, bool)
            or not isinstance(delivery_days, (int, float))
            or delivery_days < 0
        ):
            raise ValueError("delivery_days must be a non-negative number")
        rows.append(row)
    return rows


def _percentage(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator * 100, 1) if denominator else None


def _average(values: Sequence[float | int]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def _elapsed_days(start: Any, end: Any) -> float | None:
    try:
        started = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        ended = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
        elapsed = (ended - started).total_seconds() / 86400
    except (TypeError, ValueError):
        return None
    return round(elapsed, 1) if elapsed >= 0 else None


def offer_workspace_template() -> dict[str, Any]:
    return {
        "case_summary": "",
        "customer_problem": "",
        "proposed_service": "",
        "price_candidates": [],
        "delivery_candidates": [],
        "expected_outcome": "",
        "real_customer_data_present": False,
        **SAFETY,
    }


def build_estimate_proposal() -> dict[str, Any]:
    return {
        "estimate_content": "",
        "scope_of_work": [],
        "delivery_date": "",
        "price": {"amount": None, "currency": "JPY", "tax_status": "human_review_required"},
        "exclusions": [],
        "cautions": [
            "Human review is required before any customer use.",
            "This proposal is not a contract, invoice, or binding quotation.",
        ],
        "status": "review_required",
        "generated_from": "template",
        "persisted": False,
        **SAFETY,
    }


def build_conversion_dashboard(
    offers: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = _records(offers)
    estimated_states = {"ESTIMATE_CREATED", "APPROVAL_WAITING", "APPROVED", "ORDERED"}
    inquiries = len(rows)
    estimates = [row for row in rows if row["status"] in estimated_states]
    approval_waiting = sum(row["status"] == "APPROVAL_WAITING" for row in rows)
    orders = sum(row["status"] == "ORDERED" for row in rows)
    amounts = [float(row["estimate_amount"]) for row in estimates if row.get("estimate_amount") is not None]
    delivery_days = [
        float(row["delivery_days"])
        for row in estimates
        if row.get("delivery_days") is not None
    ]
    lead_times = [
        elapsed
        for row in estimates
        for elapsed in [_elapsed_days(row.get("inquiry_at"), row.get("estimate_created_at"))]
        if elapsed is not None
    ]
    return {
        "metrics": {
            "inquiry_count": inquiries,
            "estimate_created_count": len(estimates),
            "approval_waiting_count": approval_waiting,
            "order_rate_pct": _percentage(orders, len(estimates)),
            "average_estimate_amount": _average(amounts),
            "average_lead_time_days": _average(lead_times),
        },
        "formulas": {
            "order_rate_pct": "orders / estimate_created_count",
            "average_estimate_amount": "sum(proposal estimate amounts) / priced estimates",
            "average_lead_time_days": "sum(estimate_created_at - inquiry_at) / dated estimates",
        },
        "projection_details": {
            "average_delivery_days": _average(delivery_days),
            "average_delivery_days_formula": "sum(proposal delivery days) / offers with delivery candidate",
        },
        "records": deepcopy(rows),
        "actual_data_present": bool(rows),
        **SAFETY,
    }


def build_executive_business_health(
    dashboard: Mapping[str, Any],
) -> dict[str, Any]:
    metrics = dict(dashboard.get("metrics", {}))
    inquiries = int(metrics.get("inquiry_count", 0))
    estimates = int(metrics.get("estimate_created_count", 0))
    average_amount = metrics.get("average_estimate_amount")
    details = dict(dashboard.get("projection_details", {}))
    return {
        "estimate_rate_pct": _percentage(estimates, inquiries),
        "estimate_rate_formula": "estimate_created_count / inquiry_count",
        "order_rate_pct": metrics.get("order_rate_pct"),
        "average_project_unit_price": average_amount,
        "average_delivery_days": details.get("average_delivery_days"),
        "case_value": round(float(average_amount) * estimates, 1) if average_amount is not None else None,
        "case_value_formula": "average_project_unit_price * estimate_created_count",
        **SAFETY,
    }


def build_commander_proposals() -> list[dict[str, Any]]:
    items = (
        ("note-fit", "この案件はnote制作向き", "Offer Workspace"),
        ("upsell", "追加提案候補をレビュー", "Sales Engine"),
        ("price-adjustment", "価格調整候補をレビュー", "Revenue Engine"),
        ("faq", "FAQ追加候補をレビュー", "Marketing Dashboard"),
    )
    return [
        {
            "proposal_id": f"sales3-{proposal_id}",
            "title": title,
            "target": target,
            "status": "review_required",
            **SAFETY,
        }
        for proposal_id, title, target in items
    ]


def customer_workspace_template() -> dict[str, Any]:
    return {
        "estimate_history": [],
        "proposal_history": [],
        "contact_history": [],
        "real_customer_data_present": False,
        **SAFETY,
    }


def build_revenue_proposal_payload(
    revenue_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    mapping = build_revenue_mapping(revenue_records)
    return {
        "payload_type": "revenue_verified_actual_proposal",
        "status": "review_required",
        "verified_actuals": deepcopy(mapping["verified_actuals"]),
        "verified_actual_count": mapping["verified_actual_count"],
        "excluded_count": mapping["excluded_count"],
        "estimated_display_allowed": False,
        "persisted": False,
        **SAFETY,
    }


def build_local_review(
    *,
    offers: Iterable[Mapping[str, Any]] | None = None,
    revenue_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = _records(offers)
    dashboard = build_conversion_dashboard(rows)
    return {
        "phase": "SALES-3",
        "status": "review_required",
        "mode": "local_review",
        "development_policy_alignment": {
            "first_revenue_priority": True,
            "inquiry_to_estimate_approval_scope": True,
            "existing_engines_only": True,
            "new_engine_added": False,
        },
        "offer_workspace": offer_workspace_template(),
        "estimate_generator": build_estimate_proposal(),
        "conversion_dashboard": dashboard,
        "executive_dashboard": {
            "business_health": build_executive_business_health(dashboard),
            **SAFETY,
        },
        "commander": {"proposals": build_commander_proposals(), **SAFETY},
        "customer_workspace": customer_workspace_template(),
        "revenue_engine": build_revenue_proposal_payload(revenue_records),
        "marketing_dashboard": {"faq_candidate_route": "commander.proposals", **SAFETY},
        "knowledge_platform": {"mode": "registration_blocked", **SAFETY},
        "existing_surface_mapping": {
            "Sales Engine": "offer_workspace+estimate_generator+conversion_dashboard",
            "Executive Dashboard": "executive_dashboard.business_health",
            "Customer Workspace": "customer_workspace",
            "Revenue Engine": "revenue_engine",
            "Commander": "commander.proposals",
            "Marketing Dashboard": "marketing_dashboard.faq_candidate_route",
        },
        "ui": {
            "design_system": "AIOS Design System v1.0",
            "responsive_min_width_px": RESPONSIVE_MIN_WIDTH,
            "desktop_supported": True,
            "quick_actions_enabled": False,
        },
        **SAFETY,
    }


__all__ = [
    "OFFER_STATES", "RESPONSIVE_MIN_WIDTH", "SAFETY", "OfferStatus",
    "build_commander_proposals", "build_conversion_dashboard",
    "build_estimate_proposal", "build_executive_business_health",
    "build_local_review", "build_revenue_proposal_payload",
    "customer_workspace_template", "offer_workspace_template",
]
