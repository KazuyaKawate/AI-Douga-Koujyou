"""SALES-4 delivery-to-sales-cycle local projections.

Pure in-memory review models inside the existing Sales Engine.  This module has
no save, send, publish, registration, website update, production, or external
I/O path.
"""

from __future__ import annotations

from copy import deepcopy
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from .offer_conversion import build_revenue_proposal_payload


class DeliveryCycleStatus(str, Enum):
    DELIVERY_PENDING = "DELIVERY_PENDING"
    DELIVERED = "DELIVERED"
    REVIEWED = "REVIEWED"
    CASE_READY = "CASE_READY"
    REPROPOSED = "REPROPOSED"
    CLOSED = "CLOSED"


CYCLE_STATES = tuple(item.value for item in DeliveryCycleStatus)
CYCLE_ROUTE = (
    "Delivery", "Review", "Case Study", "FAQ", "Knowledge", "Marketing", "Sales",
)
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
    "review_send_allowed": False,
    "case_publish_allowed": False,
    "knowledge_registration_allowed": False,
    "learning_registration_allowed": False,
    "website_update_allowed": False,
    "production_allowed": False,
    "external_request_sent": False,
}


def _records(values: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if values is None:
        return []
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError("delivery records must be a sequence of mappings")
    rows: list[dict[str, Any]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise ValueError("each delivery record must be a mapping")
        row = dict(value)
        status = str(row.get("status", "DELIVERY_PENDING")).strip().upper()
        if status not in CYCLE_STATES:
            raise ValueError(f"invalid SALES-4 delivery status: {status}")
        row["status"] = status
        for flag in ("delivery_complete", "review_received", "case_approved", "reproposal_created"):
            if flag in row and not isinstance(row[flag], bool):
                raise ValueError(f"{flag} must be boolean")
        rows.append(row)
    return rows


def _percentage(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator * 100, 1) if denominator else None


def delivery_workspace_template() -> dict[str, Any]:
    return {
        "deliverables": [],
        "delivery_date": "",
        "completion_confirmed": False,
        "review_status": "not_requested",
        "case_publication_allowed": False,
        "real_customer_data_present": False,
        **SAFETY,
    }


def review_workspace_template() -> dict[str, Any]:
    return {
        "review_request": "",
        "improvement_points": [],
        "satisfaction": None,
        "next_proposal": "",
        "persisted": False,
        **SAFETY,
    }


def case_study_proposal() -> dict[str, Any]:
    return {
        "challenge": "",
        "solution": "",
        "outcome": "",
        "learning": "",
        "reproduction_points": [],
        "publication_status": "blocked",
        "persisted": False,
        **SAFETY,
    }


def build_faq_candidates(
    records: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = _records(records)
    candidates = [
        {
            "proposal_id": f"sales4-faq-{index:03d}",
            "source_delivery_id": str(row.get("delivery_id", "")),
            "question": "案件で確認されたFAQ論点をどのように説明するか？",
            "source_topic_present": True,
            "answer_draft": "",
            "status": "review_required",
            **SAFETY,
        }
        for index, row in enumerate(rows, start=1)
        if isinstance(row.get("faq_seed"), str) and str(row["faq_seed"]).strip()
    ]
    return {
        "candidate_count": len(candidates),
        "candidates": candidates,
        "registration_status": "not_registered",
        **SAFETY,
    }


def build_cycle_projection(
    records: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = _records(records)
    delivered_states = {"DELIVERED", "REVIEWED", "CASE_READY", "REPROPOSED", "CLOSED"}
    reviewed_states = {"REVIEWED", "CASE_READY", "REPROPOSED"}
    delivered = sum(row.get("delivery_complete", row["status"] in delivered_states) for row in rows)
    reviews = sum(row.get("review_received", row["status"] in reviewed_states) for row in rows)
    cases = sum(row.get("case_approved", row["status"] in {"CASE_READY", "REPROPOSED"}) for row in rows)
    reproposals = sum(row.get("reproposal_created", row["status"] == "REPROPOSED") for row in rows)
    faq = build_faq_candidates(rows)
    return {
        "metrics": {
            "delivery_completion_rate_pct": _percentage(delivered, len(rows)),
            "review_rate_pct": _percentage(reviews, delivered),
            "case_study_rate_pct": _percentage(cases, reviews),
            "faq_candidate_count": faq["candidate_count"],
            "reproposal_rate_pct": _percentage(reproposals, delivered),
        },
        "counts": {
            "record_count": len(rows),
            "delivered_count": delivered,
            "review_count": reviews,
            "case_study_count": cases,
            "reproposal_count": reproposals,
        },
        "formulas": {
            "delivery_completion_rate_pct": "delivered / delivery records",
            "review_rate_pct": "reviews / delivered",
            "case_study_rate_pct": "case approved / reviews",
            "reproposal_rate_pct": "reproposals / delivered",
        },
        "records": deepcopy(rows),
        **SAFETY,
    }


def build_commander_proposals() -> list[dict[str, Any]]:
    items = (
        ("additional-service", "追加サービス提案をレビュー", "Sales Engine"),
        ("review-acquisition", "レビュー取得候補をレビュー", "Customer Workspace"),
        ("case-study", "ケース化候補をレビュー", "Marketing Dashboard"),
        ("improvement", "改善候補をレビュー", "Commander"),
    )
    return [
        {
            "proposal_id": f"sales4-{proposal_id}",
            "title": title,
            "target": target,
            "status": "review_required",
            **SAFETY,
        }
        for proposal_id, title, target in items
    ]


def customer_workspace_template() -> dict[str, Any]:
    return {
        "reviews": [],
        "case_studies": [],
        "referrals": [],
        "next_proposals": [],
        "real_customer_data_present": False,
        **SAFETY,
    }


def build_cycle_route() -> dict[str, Any]:
    nodes = [
        {"sequence": index, "name": name, "mode": "existing_surface_or_proposal"}
        for index, name in enumerate(CYCLE_ROUTE, start=1)
    ]
    edges = [
        {"from": CYCLE_ROUTE[index - 1], "to": CYCLE_ROUTE[index], "mode": "review_route"}
        for index in range(1, len(CYCLE_ROUTE))
    ]
    return {"nodes": nodes, "edges": edges, "status": "local_review", **SAFETY}


def build_local_review(
    *,
    delivery_records: Iterable[Mapping[str, Any]] | None = None,
    revenue_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = _records(delivery_records)
    faq = build_faq_candidates(rows)
    projection = build_cycle_projection(rows)
    return {
        "phase": "SALES-4",
        "status": "review_required",
        "mode": "local_review",
        "development_policy_alignment": {
            "first_revenue_priority": True,
            "retention_cycle_priority": True,
            "existing_engines_only": True,
            "new_engine_added": False,
        },
        "delivery_workspace": delivery_workspace_template(),
        "review_workspace": review_workspace_template(),
        "case_study_builder": case_study_proposal(),
        "faq_candidates": faq,
        "executive_dashboard": {"business_health": projection, **SAFETY},
        "commander": {"proposals": build_commander_proposals(), **SAFETY},
        "customer_workspace": customer_workspace_template(),
        "knowledge_platform": {
            "candidate_count": faq["candidate_count"],
            "registration_status": "not_registered",
            **SAFETY,
        },
        "marketing_dashboard": {
            "case_candidate_count": projection["counts"]["case_study_count"],
            "faq_candidate_count": faq["candidate_count"],
            **SAFETY,
        },
        "revenue_engine": build_revenue_proposal_payload(revenue_records),
        "sales_engine": {"reproposal_count": projection["counts"]["reproposal_count"], **SAFETY},
        "cycle_route": build_cycle_route(),
        "existing_surface_mapping": {
            "Sales Engine": "sales_engine+delivery/review/case proposals",
            "Customer Workspace": "customer_workspace",
            "Knowledge Platform": "knowledge_platform candidates only",
            "Marketing Dashboard": "marketing_dashboard",
            "Executive Dashboard": "executive_dashboard.business_health",
            "Revenue Engine": "revenue_engine verified proposal payload",
            "Commander": "commander.proposals",
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
    "CYCLE_ROUTE", "CYCLE_STATES", "RESPONSIVE_MIN_WIDTH", "SAFETY",
    "DeliveryCycleStatus", "build_commander_proposals", "build_cycle_projection",
    "build_cycle_route", "build_faq_candidates", "build_local_review",
    "case_study_proposal", "customer_workspace_template",
    "delivery_workspace_template", "review_workspace_template",
]
