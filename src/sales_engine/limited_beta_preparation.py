"""BETA-1 limited launch preparation projections.

Pure read-only, proposal-only structures inside the existing Sales Engine.
There is no persistence, external communication, registration, or execution.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


PHASE = "BETA-1"
RESPONSIVE_MIN_WIDTH = 360

SAFETY: dict[str, bool] = {
    "local_first": True,
    "dry_run": True,
    "proposal_only": True,
    "projection_only": True,
    "template_only": True,
    "read_only": True,
    "review_required": True,
    "execute_allowed": False,
    "quick_actions_enabled": False,
    "google_write_allowed": False,
    "workspace_write_allowed": False,
    "mail_send_allowed": False,
    "inquiry_send_allowed": False,
    "inquiry_acceptance_allowed": False,
    "contract_allowed": False,
    "payment_allowed": False,
    "knowledge_registration_allowed": False,
    "learning_registration_allowed": False,
    "production_allowed": False,
    "external_request_sent": False,
    "git_push_executed": False,
    "release_executed": False,
}

LIMITED_BETA_CONFIGURATION: dict[str, Any] = {
    "recruitment_limit": 1,
    "intake_status": "BLOCKED_PENDING_OWNER_APPROVAL",
    "target_service": "note記事制作スターター（提案候補）",
    "target_service_status": "PROPOSAL",
    "current_intake_count": 0,
    "remaining_capacity": 1,
    "configuration_status": "TEMPLATE",
}

_GATES = (
    ("Launch Gate", "BLOCKED", "Owner承認と他5 Gateの完了が必要"),
    ("Business Gate", "BLOCKED", "価格・税・問い合わせ窓口が未承認"),
    ("Technical Gate", "READY", "Local read-only ProjectionとDryRun contractあり"),
    ("Legal Gate", "BLOCKED", "契約・privacy・ケース公開許諾が未承認"),
    ("Operations Gate", "BLOCKED", "納品・レビュー取得・担当Ownerが未承認"),
    ("Revenue Gate", "BLOCKED", "価格・税・決済条件未承認、verified revenue 0"),
)

_OWNER_CHECKLIST = (
    ("公開確認", "public_confirmation", "公開範囲・表示内容・承認者"),
    ("価格確認", "price_confirmation", "価格・税込税別・見積有効期限"),
    ("問い合わせ先", "inquiry_channel", "正式窓口・対応時間・SLA"),
    ("契約", "contract", "契約主体・条件・同意Evidence"),
    ("納品", "delivery", "納品先・形式・受領確認・rollback"),
    ("レビュー取得", "review_acquisition", "依頼時点・質問・掲載との同意分離"),
    ("ケース公開許諾", "case_publication_consent", "匿名化・成果根拠・明示同意"),
)

_COMMANDER = (
    ("公開前確認", "公開・問い合わせ開始前に全GateのOwner Evidenceを確認", "BLOCKED Gateのまま公開する誤操作"),
    ("不足項目", "価格・税・窓口・契約・納品Owner・公開同意を確定", "未確定条件を推測で補完"),
    ("改善候補", "Owner ChecklistへEvidence IDと有効期限を追加", "古い承認の再利用"),
    ("リスク", "1名上限・受付停止条件・incident連絡経路を再確認", "capacity超過・誤送信・無断公開"),
)


def build_launch_gates() -> list[dict[str, Any]]:
    return [
        {
            "sequence": index,
            "gate": name,
            "status": status,
            "basis": basis,
            **SAFETY,
        }
        for index, (name, status, basis) in enumerate(_GATES, start=1)
    ]


def build_beta_configuration() -> dict[str, Any]:
    config = deepcopy(LIMITED_BETA_CONFIGURATION)
    expected_remaining = config["recruitment_limit"] - config["current_intake_count"]
    if expected_remaining < 0 or config["remaining_capacity"] != expected_remaining:
        raise ValueError("invalid BETA-1 capacity configuration")
    return {**config, **SAFETY}


def build_owner_checklist() -> list[dict[str, Any]]:
    return [
        {
            "sequence": index,
            "item": label,
            "check_id": check_id,
            "required_confirmation": confirmation,
            "status": "PENDING_OWNER_REVIEW",
            "approved_value": None,
            "evidence_id": None,
            **SAFETY,
        }
        for index, (label, check_id, confirmation) in enumerate(_OWNER_CHECKLIST, start=1)
    ]


def build_executive_projection() -> dict[str, Any]:
    gates = build_launch_gates()
    checklist = build_owner_checklist()
    ready_count = sum(gate["status"] == "READY" for gate in gates)
    return {
        "launch_readiness": {
            "status": "NO_GO",
            "ready_gate_count": ready_count,
            "total_gate_count": len(gates),
            "readiness_pct": round(ready_count / len(gates) * 100, 1),
            "basis": "ready gates / total gates",
        },
        "beta_progress": {
            "accepted_count": 0,
            "limit": 1,
            "remaining": 1,
            "progress_pct": 0.0,
            "classification": "PROJECTION_TEMPLATE",
        },
        "remaining_tasks": {
            "count": len(checklist),
            "items": [item["item"] for item in checklist],
            "basis": "pending owner checklist items",
        },
        **SAFETY,
    }


def build_commander_proposals() -> list[dict[str, Any]]:
    return [
        {
            "sequence": index,
            "category": category,
            "proposal": proposal,
            "risk": risk,
            "status": "PROPOSAL",
            **SAFETY,
        }
        for index, (category, proposal, risk) in enumerate(_COMMANDER, start=1)
    ]


def build_customer_workspace_template() -> dict[str, Any]:
    return {
        "beta_customer": {
            "customer_id": "",
            "consent_status": "not_collected",
            "project_status": "not_started",
        },
        "feedback": {
            "feedback_id": "",
            "received": False,
            "publication_consent": False,
        },
        "lessons_learned": {
            "lesson_id": "",
            "candidate_text": "",
            "review_status": "not_started",
        },
        "real_customer_count": 0,
        "persisted": False,
        **SAFETY,
    }


def build_knowledge_candidates() -> dict[str, Any]:
    candidates = [
        {
            "candidate_id": "B1-KC-001",
            "title": "Limited Beta開始Gate判定基準",
            "source": "BETA-1 launch readiness projection",
            "status": "REGISTRATION_CANDIDATE",
            **SAFETY,
        },
        {
            "candidate_id": "B1-KC-002",
            "title": "Owner Checklist Evidence要件",
            "source": "BETA-1 owner checklist template",
            "status": "REGISTRATION_CANDIDATE",
            **SAFETY,
        },
    ]
    return {
        "candidates": candidates,
        "candidate_count": len(candidates),
        "registered_count": 0,
        "registration_status": "NOT_REGISTERED",
        **SAFETY,
    }


def build_limited_launch_preparation() -> dict[str, Any]:
    executive = build_executive_projection()
    return {
        "phase": PHASE,
        "status": "REVIEW_READY_LAUNCH_BLOCKED",
        "mode": "LIMITED_LAUNCH_PREPARATION",
        "launch_readiness_dashboard": {"gates": build_launch_gates(), **SAFETY},
        "limited_beta_configuration": build_beta_configuration(),
        "owner_checklist": build_owner_checklist(),
        "executive_dashboard": executive,
        "commander": {"proposals": build_commander_proposals(), **SAFETY},
        "customer_workspace": build_customer_workspace_template(),
        "knowledge_platform": build_knowledge_candidates(),
        "sales_engine": {"intake_status": LIMITED_BETA_CONFIGURATION["intake_status"], **SAFETY},
        "revenue_engine": {
            "verified_actual_revenue_jpy": 0,
            "projected_revenue_jpy": 0,
            "price_status": "PENDING_OWNER_REVIEW",
            **SAFETY,
        },
        "marketing_dashboard": {
            "public_recruitment_status": "NOT_PUBLISHED",
            "case_publication_status": "NOT_AUTHORIZED",
            **SAFETY,
        },
        "google_workspace_read_layer": {
            "mode": "READ_ONLY",
            "connected": False,
            "record_count": 0,
            "write_observed": False,
            **SAFETY,
        },
        "existing_surface_mapping": {
            "Sales Engine": "intake status proposal",
            "Customer Workspace": "empty beta/feedback/lessons templates",
            "Executive Dashboard": "readiness/progress/tasks projections",
            "Revenue Engine": "verified actual zero and price pending",
            "Knowledge Platform": "registration candidates only",
            "Marketing Dashboard": "not published/not authorized",
            "Commander": "four non-executable proposals",
            "Google Workspace Read Layer": "disconnected read-only zero-record projection",
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
    "LIMITED_BETA_CONFIGURATION", "PHASE", "RESPONSIVE_MIN_WIDTH", "SAFETY",
    "build_beta_configuration", "build_commander_proposals",
    "build_customer_workspace_template", "build_executive_projection",
    "build_knowledge_candidates", "build_launch_gates",
    "build_limited_launch_preparation", "build_owner_checklist",
]
