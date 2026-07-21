"""SALES-2 marketing and content local projections.

This module extends the existing Content Engine with pure, in-memory review
projections.  It has no persistence, network, publication, registration, or
production execution path.
"""

from __future__ import annotations

from copy import deepcopy
from enum import Enum
from typing import Any, Iterable, Mapping


class CampaignStatus(str, Enum):
    IDEA = "IDEA"
    DRAFT = "DRAFT"
    READY = "READY"
    REVIEW = "REVIEW"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"
    ANALYZING = "ANALYZING"
    IMPROVEMENT = "IMPROVEMENT"


CAMPAIGN_STATES = tuple(item.value for item in CampaignStatus)
WEBSITE_FUNNEL = (
    "Website", "Service", "note", "Threads", "Contact", "Inquiry",
    "Customer", "Review", "Case Study",
)
RESPONSIVE_MIN_WIDTH = 360

SAFETY: dict[str, bool] = {
    "local_first": True,
    "dry_run": True,
    "proposal_only": True,
    "projection_only": True,
    "review_required": True,
    "execute_allowed": False,
    "quick_actions_enabled": False,
    "google_write_allowed": False,
    "workspace_write_allowed": False,
    "mail_send_allowed": False,
    "sns_post_allowed": False,
    "note_post_allowed": False,
    "website_update_allowed": False,
    "production_change_allowed": False,
    "knowledge_registration_allowed": False,
    "learning_registration_allowed": False,
    "external_request_sent": False,
}


def _rows(values: Iterable[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if values is None:
        return []
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError("campaigns must be a sequence of mappings")
    result: list[dict[str, Any]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise ValueError("each campaign must be a mapping")
        row = dict(value)
        status = str(row.get("status", "IDEA")).strip().upper()
        if status not in CAMPAIGN_STATES:
            raise ValueError(f"invalid SALES-2 campaign status: {status}")
        row["status"] = status
        row["channel"] = str(row.get("channel", "")).strip().lower()
        result.append(row)
    return result


def _non_negative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator * 100, 1) if denominator else None


def build_content_planner() -> dict[str, Any]:
    groups = {
        "article_candidates": (
            "AIOSで初収益までの作業を可視化する方法",
            "Local Firstで小さく始める業務AI導入",
        ),
        "threads_candidates": (
            "今日のAIOS改善ログを短文で紹介",
            "初収益までに後回しにした機能を共有",
        ),
        "lp_improvement_candidates": (
            "ファーストビューで対象顧客と成果を明確化",
            "問い合わせ前の不安をFAQへ接続",
        ),
        "cta_candidates": (
            "サービス内容を確認する",
            "相談前FAQを確認する",
        ),
        "faq_candidates": (
            "AIOSは何を支援できますか",
            "公開前に人間レビューはありますか",
        ),
    }
    return {
        key: [
            {
                "proposal_id": f"sales2-{key.replace('_candidates', '').replace('_', '-')}-{index:02d}",
                "title": title,
                "status": "review_required",
                **SAFETY,
            }
            for index, title in enumerate(titles, start=1)
        ]
        for key, titles in groups.items()
    } | {"mode": "proposal", **SAFETY}


def build_campaign_timeline(
    campaigns: Iterable[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    rows = _rows(campaigns)
    return {
        "states": list(CAMPAIGN_STATES),
        "counts": {state: sum(row["status"] == state for row in rows) for state in CAMPAIGN_STATES},
        "campaign_count": len(rows),
        "records": deepcopy(rows),
        "mode": "local_projection",
        **SAFETY,
    }


def build_marketing_dashboard(
    campaigns: Iterable[Mapping[str, Any]] | None = None,
    *,
    lp_update_count: int = 0,
    inquiry_route_count: int = 0,
    review_count: int = 0,
) -> dict[str, Any]:
    rows = _rows(campaigns)
    lp_updates = _non_negative_int(lp_update_count, "lp_update_count")
    inquiry_routes = _non_negative_int(inquiry_route_count, "inquiry_route_count")
    reviews = _non_negative_int(review_count, "review_count")
    published_articles = sum(
        row["status"] in {"PUBLISHED", "ANALYZING", "IMPROVEMENT"}
        and row["channel"] in {"article", "note"}
        for row in rows
    )
    scheduled_posts = sum(row["status"] == "SCHEDULED" for row in rows)
    return {
        "metrics": {
            "published_article_count": published_articles,
            "scheduled_post_count": scheduled_posts,
            "lp_update_count": lp_updates,
            "inquiry_route_count": inquiry_routes,
            "review_count": reviews,
        },
        "actual_data_present": bool(rows or lp_updates or inquiry_routes or reviews),
        "mode": "projection",
        **SAFETY,
    }


def build_ai_recommendations() -> list[dict[str, Any]]:
    items = (
        ("write-note", "今日はnoteを書く", "note"),
        ("threads-candidate", "Threads投稿候補をレビュー", "Threads"),
        ("add-faq", "FAQ追加候補をレビュー", "Website"),
        ("improve-lp", "LP改善候補をレビュー", "Beta LP"),
        ("improve-cta", "CTA改善候補をレビュー", "Website"),
    )
    return [
        {
            "proposal_id": f"sales2-{proposal_id}",
            "title": title,
            "target": target,
            "status": "review_required",
            "evidence_status": "local_fixture",
            **SAFETY,
        }
        for proposal_id, title, target in items
    ]


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


def build_marketing_health(
    dashboard: Mapping[str, Any],
    timeline: Mapping[str, Any],
    *,
    improvement_proposal_count: int,
) -> dict[str, Any]:
    metrics = dict(dashboard.get("metrics", {}))
    counts = dict(timeline.get("counts", {}))
    proposals = _non_negative_int(improvement_proposal_count, "improvement_proposal_count")
    campaign_count = int(timeline.get("campaign_count", 0))
    published = sum(int(counts.get(state, 0)) for state in ("PUBLISHED", "ANALYZING", "IMPROVEMENT"))
    scheduled = int(counts.get("SCHEDULED", 0))
    reviews = int(metrics.get("review_count", 0))
    lp_updates = int(metrics.get("lp_update_count", 0))
    return {
        "article_count": int(metrics.get("published_article_count", 0)),
        "posting_rate_pct": _rate(published, campaign_count),
        "posting_rate_formula": "published_or_later / campaign_count",
        "review_rate_pct": _rate(reviews, published),
        "review_rate_formula": "reviews / published_or_later",
        "lp_update_rate_pct": _rate(lp_updates, lp_updates + scheduled),
        "lp_update_rate_formula": "lp_updates / (lp_updates + scheduled)",
        "improvement_proposal_count": proposals,
        "mode": "projection",
        **SAFETY,
    }


def build_learning_proposals() -> dict[str, Any]:
    proposals = [
        {
            "proposal_id": "sales2-learning-funnel-01",
            "title": "離脱が確認された導線の改善仮説をレビュー",
            "status": "review_required",
            **SAFETY,
        },
        {
            "proposal_id": "sales2-learning-content-01",
            "title": "反応が確認できたテーマの再現条件をレビュー",
            "status": "review_required",
            **SAFETY,
        },
    ]
    return {
        "improvement_candidates": proposals,
        "candidate_count": len(proposals),
        "registration_status": "not_registered",
        **SAFETY,
    }


def build_local_review(
    *,
    campaigns: Iterable[Mapping[str, Any]] | None = None,
    lp_update_count: int = 0,
    inquiry_route_count: int = 0,
    review_count: int = 0,
) -> dict[str, Any]:
    rows = _rows(campaigns)
    timeline = build_campaign_timeline(rows)
    dashboard = build_marketing_dashboard(
        rows,
        lp_update_count=lp_update_count,
        inquiry_route_count=inquiry_route_count,
        review_count=review_count,
    )
    planner = build_content_planner()
    learning = build_learning_proposals()
    improvement_count = (
        len(planner["lp_improvement_candidates"])
        + len(planner["cta_candidates"])
        + len(planner["faq_candidates"])
        + learning["candidate_count"]
    )
    return {
        "phase": "SALES-2",
        "status": "review_required",
        "mode": "local_review",
        "development_policy_alignment": {
            "first_revenue_priority": True,
            "website_note_threads_integrated": True,
            "existing_engines_only": True,
            "new_engine_added": False,
        },
        "content_planner": planner,
        "marketing_dashboard": dashboard,
        "campaign_timeline": timeline,
        "ai_recommendations": build_ai_recommendations(),
        "website_funnel": build_website_funnel(),
        "executive_dashboard": {
            "marketing_health": build_marketing_health(
                dashboard, timeline, improvement_proposal_count=improvement_count,
            ),
            **SAFETY,
        },
        "learning": learning,
        "existing_surface_mapping": {
            "Website": "website_funnel",
            "Beta LP": "content_planner.lp_improvement_candidates",
            "Executive Dashboard": "executive_dashboard.marketing_health",
            "Commander": "ai_recommendations",
            "Revenue Engine": "marketing_dashboard",
            "Knowledge Platform": "read_reference_only",
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
    "CAMPAIGN_STATES", "RESPONSIVE_MIN_WIDTH", "SAFETY", "WEBSITE_FUNNEL",
    "CampaignStatus", "build_ai_recommendations", "build_campaign_timeline",
    "build_content_planner", "build_learning_proposals", "build_local_review",
    "build_marketing_dashboard", "build_marketing_health", "build_website_funnel",
]
