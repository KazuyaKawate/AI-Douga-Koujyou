"""MARKETING-1 local presentation package.

No persistence, network, publishing, contracting, payment, or production path.
Actual metrics are accepted only with explicit verified evidence.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping


SAFETY = {
    "local_first": True, "dry_run": True, "presentation_only": True,
    "approval_required": True, "review_required": True,
    "execute_allowed": False, "production_actions_enabled": False,
    "external_request_sent": False,
}

SERVICES = (
    {"service_id": "mkt1-ai-consulting", "name": "AI活用コンサル", "scope": "業務整理・AI活用診断・導入ロードマップ", "price": "個別見積", "status": "OWNER REVIEW REQUIRED"},
    {"service_id": "mkt1-web-ai-ops", "name": "HP制作＋AI運用", "scope": "構成・原稿・ローカル制作・運用設計", "price": "個別見積", "status": "OWNER REVIEW REQUIRED"},
    {"service_id": "mkt1-note-threads", "name": "note/Threads運用", "scope": "企画・独自構成・投稿案・改善レビュー", "price": "個別見積", "status": "OWNER REVIEW REQUIRED"},
)

SALES_KIT = (
    ("サービス紹介", "reports/MARKETING1_SALES_KIT.md#サービス紹介"),
    ("料金表", "reports/MARKETING1_SALES_KIT.md#料金表"),
    ("見積テンプレート", "reports/MARKETING1_SALES_KIT.md#見積テンプレート"),
    ("契約テンプレート", "reports/MARKETING1_SALES_KIT.md#契約テンプレート"),
    ("FAQ", "reports/MARKETING1_SALES_KIT.md#faq"),
)

EVIDENCE_TYPES = ("inquiry", "sales", "order")


def _non_negative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def build_dashboard(*, posts: int = 0, lp_visits: int = 0, inquiries: int = 0,
                    improvement_tasks: int = 0, verified_actual: bool = False) -> dict[str, Any]:
    values = {name: _non_negative_int(value, name) for name, value in {
        "posts": posts, "lp_visits": lp_visits, "inquiries": inquiries,
        "improvement_tasks": improvement_tasks,
    }.items()}
    if any(values.values()) and not verified_actual:
        raise ValueError("non-zero metrics require verified_actual evidence")
    values["cv_rate_pct"] = round(inquiries / lp_visits * 100, 1) if lp_visits else None
    return {"metrics": values, "classification": "ACTUAL" if verified_actual else "NO ACTUAL", **SAFETY}


def build_evidence_registry(records: Iterable[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    rows = []
    for record in records or ():
        row = dict(record)
        if row.get("evidence_type") not in EVIDENCE_TYPES:
            raise ValueError("invalid evidence_type")
        if row.get("status") != "VERIFIED" or not str(row.get("evidence_id", "")).strip():
            raise ValueError("evidence requires VERIFIED status and evidence_id")
        rows.append(row)
    return {"records": rows, "verified_count": len(rows), "templates": list(EVIDENCE_TYPES), **SAFETY}


def build_review() -> dict[str, Any]:
    return {
        "phase": "MARKETING-1 FIRST CUSTOMER ACQUISITION",
        "phase_status": "OWNER REVIEW REQUIRED",
        "service_catalog": deepcopy(SERVICES),
        "sales_kit": [{"name": name, "local_ref": ref, **SAFETY} for name, ref in SALES_KIT],
        "landing_page_review": {
            "cta": "PASS: visible disabled CTA; activation requires Owner review",
            "inquiry_route": "PASS: Contact section present; sending remains disabled",
            "mobile": "PASS: viewport and responsive stylesheet present",
            "local_ref": "ui/public-preview/index.html",
            **SAFETY,
        },
        "marketing_dashboard": build_dashboard(),
        "evidence_registry": build_evidence_registry(),
        **SAFETY,
    }


__all__ = ["EVIDENCE_TYPES", "SAFETY", "SERVICES", "build_dashboard", "build_evidence_registry", "build_review"]
