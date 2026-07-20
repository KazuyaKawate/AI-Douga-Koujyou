"""SALES-5 beta customer E2E simulator.

Deterministic, anonymous, in-memory projections inside the existing Sales
Engine. Nothing persists, sends, registers, publishes, or changes production.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PHASE = "SALES-5"
RESPONSIVE_MIN_WIDTH = 360
FLOW = (
    "Inquiry", "Hearing", "Estimate", "Approved",
    "Delivery", "Review", "Case Study", "Closed",
)

SAFETY: dict[str, bool] = {
    "local_first": True,
    "dry_run": True,
    "proposal_only": True,
    "projection_only": True,
    "template_only": True,
    "review_required": True,
    "execute_allowed": False,
    "quick_actions_enabled": False,
    "google_write_allowed": False,
    "workspace_write_allowed": False,
    "mail_send_allowed": False,
    "inquiry_send_allowed": False,
    "contract_allowed": False,
    "payment_allowed": False,
    "knowledge_registration_allowed": False,
    "learning_registration_allowed": False,
    "website_update_allowed": False,
    "production_allowed": False,
    "external_request_sent": False,
}

MOCK_PROJECT: dict[str, Any] = {
    "project_id": "SALES5-MOCK-001",
    "customer_id": "ANON-CUSTOMER-001",
    "customer_name": "匿名Beta顧客A（架空）",
    "service_id": "NOTE-STARTER-MOCK",
    "service_name": "note記事制作スターター（架空）",
    "currency": "JPY",
    "estimate_subtotal": 16_500,
    "tax": None,
    "actual_revenue": 0,
    "data_classification": "ANONYMOUS_FIXED_MOCK",
    "real_customer_data_present": False,
}

_TIMESTAMPS = (
    "2026-07-14T09:00:00+09:00", "2026-07-14T09:10:00+09:00",
    "2026-07-14T09:20:00+09:00", "2026-07-14T09:30:00+09:00",
    "2026-07-14T09:40:00+09:00", "2026-07-14T09:50:00+09:00",
    "2026-07-14T10:00:00+09:00", "2026-07-14T10:10:00+09:00",
)

_QA = (
    ("PASS", "匿名固定fixtureと必須項目を確認"),
    ("PASS", "目的・対象・権利・機密のtemplate確認"),
    ("WARNING", "税額と実顧客条件は未確定"),
    ("WARNING", "承認はsimulationであり契約ではない"),
    ("BLOCKED", "実納品・Workspace Write・外部送信を禁止"),
    ("WARNING", "レビューは架空値で実受領ではない"),
    ("BLOCKED", "公開同意がなくCase公開を禁止"),
    ("WARNING", "実入金・実納品なしのためmock closeのみ"),
)

_COMMANDER = (
    ("問い合わせ必須項目を短文化", "実送信前の同意と連絡先", "実顧客情報の混入"),
    ("結論を一文で固定", "素材権利と機密区分", "要件の曖昧さ"),
    ("税・追加修正条件を分離", "単価・納期・有効期限", "見積を売上計上する誤り"),
    ("承認Evidenceを二者で分離", "契約権限と最終承認者", "simulationを契約と誤認"),
    ("checksum確認を標準化", "納品先と受領承認", "外部送信・誤納品"),
    ("改善点を構造化", "引用・掲載可否", "架空評価の実績利用"),
    ("数値根拠と匿名化を再確認", "公開同意・証拠owner", "未承認公開"),
    ("次回提案条件を明文化", "実入金・完了承認", "mockを実績登録"),
)


def _validate_stage(stage: str) -> int:
    if stage not in FLOW:
        raise ValueError(f"invalid SALES-5 stage: {stage}")
    return FLOW.index(stage)


def build_evidence_timeline() -> list[dict[str, Any]]:
    """Return evidence templates for all eight stages."""
    return [
        {
            "sequence": index,
            "stage": stage,
            "evidence_id": f"S5-EV-{index:03d}",
            "timestamp": _TIMESTAMPS[index - 1],
            "status": "TEMPLATE_READY",
            "evidence_class": "MOCK_TEMPLATE",
            **SAFETY,
        }
        for index, stage in enumerate(FLOW, start=1)
    ]


def build_qa_review() -> list[dict[str, Any]]:
    return [
        {
            "sequence": index, "stage": stage, "result": result,
            "basis": basis, "mode": "proposal_only", **SAFETY,
        }
        for index, (stage, (result, basis)) in enumerate(zip(FLOW, _QA), start=1)
    ]


def build_commander_review() -> list[dict[str, Any]]:
    return [
        {
            "sequence": index,
            "stage": stage,
            "improvement_proposal": improvement,
            "confirmation_required": confirmation,
            "risk": risk,
            "status": "PROPOSAL",
            **SAFETY,
        }
        for index, (stage, (improvement, confirmation, risk)) in enumerate(
            zip(FLOW, _COMMANDER), start=1
        )
    ]


def build_executive_replay() -> list[dict[str, Any]]:
    """Build projection-only frames as each simulated stage becomes current."""
    frames: list[dict[str, Any]] = []
    for index, stage in enumerate(FLOW, start=1):
        estimate_visible = index >= 3
        approved = index >= 4
        case_candidate = 1 if index >= 7 else 0
        frames.append(
            {
                "sequence": index,
                "stage": stage,
                "business_health": {
                    "simulated_progress_pct": round(index / len(FLOW) * 100, 1),
                    "qa_result": _QA[index - 1][0],
                    "system_status": "SAFE_DRY_RUN",
                },
                "revenue_projection": {
                    "estimate_subtotal_jpy": MOCK_PROJECT["estimate_subtotal"] if estimate_visible else 0,
                    "projected_revenue_jpy": MOCK_PROJECT["estimate_subtotal"] if approved else 0,
                    "verified_actual_revenue_jpy": 0,
                    "tax": None,
                    "classification": "PROJECTION_NOT_REVENUE",
                },
                "marketing": {
                    "case_study_candidate_count": case_candidate,
                    "published_count": 0,
                    "status": "CANDIDATE_ONLY" if case_candidate else "NOT_AVAILABLE",
                },
                "customer": {
                    "mock_project_count": 1,
                    "current_stage": stage,
                    "completed_simulated_steps": index,
                    "real_customer_count": 0,
                },
                **SAFETY,
            }
        )
    return frames


def build_customer_workspace(stage: str = "Closed") -> dict[str, Any]:
    current_index = _validate_stage(stage)
    return {
        "visible_projects": [
            {
                **deepcopy(MOCK_PROJECT),
                "current_stage": stage,
                "flow": [
                    {
                        "stage": name,
                        "simulation_status": "SIMULATED" if index <= current_index else "PENDING",
                    }
                    for index, name in enumerate(FLOW)
                ],
            }
        ],
        "visible_project_count": 1,
        "real_customer_count": 0,
        "persisted": False,
        **SAFETY,
    }


def build_knowledge_candidates(stage: str = "Closed") -> dict[str, Any]:
    current_index = _validate_stage(stage)
    candidates: list[dict[str, Any]] = []
    if current_index >= FLOW.index("Review"):
        candidates.append(
            {
                "candidate_id": "S5-KC-001",
                "title": "ヒアリング時に結論を一文で固定する",
                "source_evidence_ids": ["S5-EV-002", "S5-EV-006"],
                "status": "REGISTRATION_CANDIDATE",
                **SAFETY,
            }
        )
    if current_index >= FLOW.index("Case Study"):
        candidates.append(
            {
                "candidate_id": "S5-KC-002",
                "title": "ケース化前の匿名化・同意確認",
                "source_evidence_ids": ["S5-EV-007"],
                "status": "REGISTRATION_CANDIDATE",
                **SAFETY,
            }
        )
    return {
        "candidates": candidates,
        "candidate_count": len(candidates),
        "registered_count": 0,
        "registration_status": "NOT_REGISTERED",
        **SAFETY,
    }


def build_simulator(stage: str = "Closed") -> dict[str, Any]:
    current_index = _validate_stage(stage)
    replay = build_executive_replay()
    return {
        "phase": PHASE,
        "status": "LOCAL_REVIEW_READY",
        "mode": "BETA_CUSTOMER_EXECUTION_SIMULATOR",
        "mock_project": deepcopy(MOCK_PROJECT),
        "flow": list(FLOW),
        "current_stage": stage,
        "evidence_timeline": build_evidence_timeline(),
        "qa_review": build_qa_review(),
        "commander": {"proposals": build_commander_review(), **SAFETY},
        "executive_dashboard": {"replay": replay, "current_projection": replay[current_index], **SAFETY},
        "revenue_engine": {**replay[current_index]["revenue_projection"], **SAFETY},
        "marketing_dashboard": {**replay[current_index]["marketing"], **SAFETY},
        "customer_workspace": build_customer_workspace(stage),
        "knowledge_platform": build_knowledge_candidates(stage),
        "sales_engine": {"simulated_stage": stage, "transition_count": current_index, **SAFETY},
        "existing_surface_mapping": {
            "Sales Engine": "simulated flow and transition projection",
            "Customer Workspace": "one anonymous fixed mock only",
            "Executive Dashboard": "eight replay projection frames",
            "Revenue Engine": "estimate/projection; verified actual remains zero",
            "Marketing Dashboard": "case candidate only; publish remains zero",
            "Commander": "improvement/confirmation/risk proposals",
            "Knowledge Platform": "registration candidates only",
        },
        "development_policy_alignment": {
            "first_revenue_priority": True,
            "existing_engines_only": True,
            "new_engine_added": False,
            "video_automation_added": False,
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
    "FLOW", "MOCK_PROJECT", "PHASE", "RESPONSIVE_MIN_WIDTH", "SAFETY",
    "build_commander_review", "build_customer_workspace", "build_evidence_timeline",
    "build_executive_replay", "build_knowledge_candidates", "build_qa_review", "build_simulator",
]
