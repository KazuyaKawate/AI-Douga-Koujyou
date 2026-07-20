"""SALES-1 first-customer acquisition projections.

Pure local-review functions only. This module has no persistence, network,
queue, publication, registration, contract, payment, or production path.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence


class LeadStatus(str, Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    HEARING = "HEARING"
    ESTIMATE = "ESTIMATE"
    WAITING = "WAITING"
    ORDERED = "ORDERED"
    DELIVERED = "DELIVERED"
    SUCCESS = "SUCCESS"
    CLOSED = "CLOSED"


PIPELINE_STATES = tuple(item.value for item in LeadStatus)
RESPONSIVE_MIN_WIDTH = 360

SAFETY: dict[str, bool] = {
    "local_first": True,
    "dry_run": True,
    "proposal_only": True,
    "approval_required": True,
    "review_required": True,
    "execute_allowed": False,
    "quick_actions_enabled": False,
    "google_write_allowed": False,
    "workspace_write_allowed": False,
    "mail_send_allowed": False,
    "sns_post_allowed": False,
    "inquiry_send_allowed": False,
    "contract_allowed": False,
    "payment_allowed": False,
    "knowledge_write_allowed": False,
    "learning_registration_allowed": False,
    "production_actions_enabled": False,
    "external_request_sent": False,
}

WEBSITE_FUNNEL = (
    "Home", "Service", "Beta", "Contact", "Inquiry", "Customer Workspace",
)


def _records(values: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if values is None:
        return []
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError("records must be a sequence of mappings")
    rows: list[dict[str, Any]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise ValueError("each record must be a mapping")
        row = dict(value)
        status = str(row.get("status", "NEW")).strip().upper()
        if status not in PIPELINE_STATES:
            raise ValueError(f"invalid SALES-1 pipeline status: {status}")
        row["status"] = status
        rows.append(row)
    return rows


def _percentage(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator * 100, 1) if denominator else None


def _elapsed_days(start: Any, end: Any) -> int | None:
    try:
        started = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        ended = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    days = (ended - started).total_seconds() / 86400
    return round(days) if days >= 0 else None


def build_funnel_projection(
    leads: Iterable[Mapping[str, Any]] | None = None,
    *,
    local_lp_views: int = 0,
) -> dict[str, Any]:
    """Project current pipeline states into monotonic funnel milestones."""
    if isinstance(local_lp_views, bool) or not isinstance(local_lp_views, int) or local_lp_views < 0:
        raise ValueError("local_lp_views must be a non-negative integer")
    rows = _records(leads)
    statuses = [row["status"] for row in rows]

    def count(*accepted: str) -> int:
        return sum(status in accepted for status in statuses)

    inquiry_count = len(rows)
    meeting_count = count("HEARING", "ESTIMATE", "WAITING", "ORDERED", "DELIVERED", "SUCCESS")
    estimate_count = count("ESTIMATE", "WAITING", "ORDERED", "DELIVERED", "SUCCESS")
    order_count = count("ORDERED", "DELIVERED", "SUCCESS")
    delivery_count = count("DELIVERED", "SUCCESS")
    review_count = count("SUCCESS")
    metrics = {
        "lp_views_local": local_lp_views,
        "inquiries": inquiry_count,
        "meetings": meeting_count,
        "estimates_submitted": estimate_count,
        "orders": order_count,
        "deliveries": delivery_count,
        "reviews_acquired": review_count,
    }
    return {
        "mode": "projection",
        "source": "local_only",
        "metrics": metrics,
        "actual_data_present": bool(rows or local_lp_views),
        **SAFETY,
    }


def build_pipeline_projection(leads: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    rows = _records(leads)
    counts = {state: sum(row["status"] == state for row in rows) for state in PIPELINE_STATES}
    return {
        "states": list(PIPELINE_STATES),
        "counts": counts,
        "lead_count": len(rows),
        "records": deepcopy(rows),
        "mode": "projection",
        **SAFETY,
    }


def first_customer_card_template() -> dict[str, Any]:
    return {
        "company_name": "",
        "contact_name": "",
        "project_name": "",
        "current_status": LeadStatus.NEW.value,
        "deadline": "",
        "next_action": "",
        "template_only": True,
        "real_customer_data_present": False,
        **SAFETY,
    }


def build_sales_recommendations() -> list[dict[str, Any]]:
    items = (
        ("threads-draft", "今日のThreads投稿案をレビュー", "Threads"),
        ("note-update", "note更新候補をレビュー", "note"),
        ("follow-up", "フォローアップ候補をレビュー", "Customer Workspace"),
        ("lp-improvement", "LP改善候補をレビュー", "Beta LP"),
    )
    return [
        {
            "recommendation_id": recommendation_id,
            "title": title,
            "target": target,
            "status": "review_required",
            **SAFETY,
        }
        for recommendation_id, title, target in items
    ]


def build_business_health(
    funnel: Mapping[str, Any],
    leads: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = _records(leads)
    metrics = dict(funnel.get("metrics", {}))
    inquiries = int(metrics.get("inquiries", 0))
    estimates = int(metrics.get("estimates_submitted", 0))
    orders = int(metrics.get("orders", 0))
    deliveries = int(metrics.get("deliveries", 0))
    reviews = int(metrics.get("reviews_acquired", 0))
    delivery_days = [
        elapsed
        for row in rows
        if row["status"] in {"DELIVERED", "SUCCESS"}
        for elapsed in [_elapsed_days(row.get("ordered_at"), row.get("delivered_at"))]
        if elapsed is not None
    ]
    return {
        "lead_count": inquiries,
        "conversion_rate_pct": _percentage(estimates, inquiries),
        "conversion_rate_formula": "estimates_submitted / inquiries",
        "order_rate_pct": _percentage(orders, estimates),
        "order_rate_formula": "orders / estimates_submitted",
        "average_delivery_days": round(sum(delivery_days) / len(delivery_days), 1) if delivery_days else None,
        "review_acquisition_rate_pct": _percentage(reviews, deliveries),
        "review_acquisition_rate_formula": "reviews_acquired / deliveries",
        "mode": "projection",
        **SAFETY,
    }


def build_customer_success_proposals(
    leads: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = _records(leads)
    candidates = [
        {
            "candidate_id": f"sales1-customer-success-{index:03d}",
            "source_lead_id": str(row.get("lead_id", "")),
            "candidate_type": "customer_success_knowledge",
            "status": "review_required",
            "automatic_registration": False,
            **SAFETY,
        }
        for index, row in enumerate(rows, start=1)
        if row["status"] in {"DELIVERED", "SUCCESS"}
    ]
    return {
        "candidate_count": len(candidates),
        "candidates": candidates,
        "automatic_registration": False,
        "registration_status": "not_registered",
        **SAFETY,
    }


def build_revenue_mapping(records: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    if records is None:
        records = []
    if isinstance(records, (str, bytes, Mapping)):
        raise ValueError("revenue records must be a sequence of mappings")
    verified: list[dict[str, Any]] = []
    input_count = 0
    for value in records:
        if not isinstance(value, Mapping):
            raise ValueError("each revenue record must be a mapping")
        input_count += 1
        row = dict(value)
        status = str(row.get("status", "")).strip().lower()
        evidence = str(row.get("evidence_status", "")).strip().lower()
        if evidence != "verified" or status in {"estimated", "proposal", "unverified"}:
            continue
        verified.append({
            key: deepcopy(row.get(key))
            for key in ("transaction_id", "status", "gross_amount", "fee_amount", "net_amount", "currency", "recorded_at")
            if key in row
        })
    return {
        "target": "Revenue Engine",
        "display_mode": "proposal",
        "verified_actuals": verified,
        "verified_actual_count": len(verified),
        "excluded_count": input_count - len(verified),
        "estimated_display_allowed": False,
        **SAFETY,
    }


def build_website_funnel() -> dict[str, Any]:
    nodes = [
        {"sequence": index, "name": name, "mode": "existing_surface"}
        for index, name in enumerate(WEBSITE_FUNNEL, start=1)
    ]
    edges = [
        {"from": WEBSITE_FUNNEL[index - 1], "to": WEBSITE_FUNNEL[index], "mode": "review_route"}
        for index in range(1, len(WEBSITE_FUNNEL))
    ]
    return {"nodes": nodes, "edges": edges, "status": "local_review", **SAFETY}


def build_local_review(
    *,
    leads: Iterable[Mapping[str, Any]] | None = None,
    local_lp_views: int = 0,
    revenue_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = _records(leads)
    funnel = build_funnel_projection(rows, local_lp_views=local_lp_views)
    pipeline = build_pipeline_projection(rows)
    customer_success = build_customer_success_proposals(rows)
    return {
        "phase": "SALES-1",
        "status": "review_required",
        "mode": "local_review",
        "development_policy_alignment": {
            "first_revenue_priority": True,
            "execution_first": True,
            "customer_first": True,
            "local_first": True,
            "human_review_required": True,
            "new_engine_added": False,
        },
        "inquiry_funnel_dashboard": funnel,
        "lead_pipeline": pipeline,
        "first_customer_card": first_customer_card_template(),
        "sales_recommendations": build_sales_recommendations(),
        "executive_dashboard": {"business_health": build_business_health(funnel, rows), **SAFETY},
        "customer_workspace": {
            "first_customer_card": first_customer_card_template(),
            "post_delivery_knowledge_proposals": deepcopy(customer_success),
            **SAFETY,
        },
        "revenue_engine": build_revenue_mapping(revenue_records),
        "knowledge_platform": deepcopy(customer_success),
        "website_funnel": build_website_funnel(),
        "ui": {
            "design_system": "AIOS Design System v1.0",
            "responsive_min_width_px": RESPONSIVE_MIN_WIDTH,
            "desktop_supported": True,
            "quick_actions_enabled": False,
        },
        **SAFETY,
    }


__all__ = [
    "LeadStatus", "PIPELINE_STATES", "RESPONSIVE_MIN_WIDTH", "SAFETY",
    "WEBSITE_FUNNEL", "build_business_health", "build_customer_success_proposals",
    "build_funnel_projection", "build_local_review", "build_pipeline_projection",
    "build_revenue_mapping", "build_sales_recommendations", "build_website_funnel",
    "first_customer_card_template",
]
