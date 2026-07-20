"""DAILY-1 local, read-only operational projection.

This module reads existing local configuration only. It never writes files,
contacts Google Workspace, registers Knowledge, changes a queue, or executes a
Commander/Learning proposal.
"""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any, Mapping

from src.utils.config import PROJECT_ROOT


SAFETY: dict[str, bool] = {
    "local_first": True,
    "approval_required": True,
    "review_required": True,
    "execute_allowed": False,
    "dry_run": True,
    "external_communication_allowed": False,
    "workspace_write_allowed": False,
    "google_write_allowed": False,
    "mail_send_allowed": False,
    "sns_post_allowed": False,
    "production_change_allowed": False,
    "contract_allowed": False,
    "payment_allowed": False,
    "knowledge_registration_allowed": False,
    "learning_registration_allowed": False,
    "quick_actions_enabled": False,
    "git_push_executed": False,
    "release_executed": False,
    "engine_changed": False,
    "schema_changed": False,
    "queue_changed": False,
}

FIRST_CUSTOMER_STAGES: tuple[dict[str, str], ...] = (
    {"key": "inquiry_received", "label": "問い合わせ受領", "evidence_type": "inquiry receipt"},
    {"key": "hearing", "label": "ヒアリング", "evidence_type": "hearing record"},
    {"key": "estimate", "label": "見積", "evidence_type": "estimate review"},
    {"key": "approval", "label": "承認", "evidence_type": "owner approval"},
    {"key": "production", "label": "制作", "evidence_type": "local production review"},
    {"key": "delivery", "label": "納品", "evidence_type": "delivery receipt"},
    {"key": "review", "label": "レビュー", "evidence_type": "customer review consent"},
    {"key": "case_study", "label": "ケーススタディ", "evidence_type": "publication consent"},
)

LIMITED_CUSTOMER_STAGES: tuple[dict[str, str], ...] = (
    {"key": "inquiry_received", "label": "Inquiry", "evidence_type": "inquiry receipt"},
    {"key": "hearing", "label": "Hearing", "evidence_type": "hearing record"},
    {"key": "estimate", "label": "Estimate", "evidence_type": "estimate review"},
    {"key": "approval", "label": "Approval", "evidence_type": "owner approval"},
    {"key": "production", "label": "Production", "evidence_type": "local production review"},
    {"key": "delivery", "label": "Delivery", "evidence_type": "delivery receipt"},
    {"key": "review", "label": "Review", "evidence_type": "customer review consent"},
    {"key": "case_study", "label": "Case Study", "evidence_type": "publication consent"},
    {"key": "revenue_verification", "label": "Revenue Verification", "evidence_type": "verified actual revenue"},
    {"key": "knowledge_candidate", "label": "Knowledge Candidate", "evidence_type": "candidate review"},
)


def build_first_customer_readiness(
    evidence_records: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate and project eight first-customer Evidence stages in memory."""
    records = {} if evidence_records is None else evidence_records
    if not isinstance(records, Mapping):
        raise ValueError("evidence records must be a mapping")
    allowed = {stage["key"] for stage in FIRST_CUSTOMER_STAGES}
    unknown = set(records) - allowed
    if unknown:
        raise ValueError(f"unknown first customer stage: {sorted(unknown)[0]}")
    items: list[dict[str, Any]] = []
    for sequence, stage in enumerate(FIRST_CUSTOMER_STAGES, start=1):
        raw = records.get(stage["key"], {})
        if not isinstance(raw, Mapping):
            raise ValueError(f'evidence {stage["key"]} must be a mapping')
        status = str(raw.get("evidence_status", "MISSING")).upper()
        if status not in {"MISSING", "VERIFIED", "REJECTED"}:
            raise ValueError(f'evidence {stage["key"]} has invalid status')
        if status in {"VERIFIED", "REJECTED"}:
            for field in ("evidence_id", "observed_at", "source", "approved_by"):
                if not str(raw.get(field, "")).strip():
                    raise ValueError(f'evidence {stage["key"]} missing {field}')
        items.append({
            "sequence": sequence,
            **deepcopy(stage),
            "evidence_id": raw.get("evidence_id", f"B3-EV-{sequence:03d}"),
            "evidence_status": status,
            "observed_at": raw.get("observed_at"),
            "source": raw.get("source"),
            "approved_by": raw.get("approved_by"),
            "reason": raw.get("reason", "Evidence not received" if status == "MISSING" else None),
            "persisted": False,
            **SAFETY,
        })
    verified = sum(item["evidence_status"] == "VERIFIED" for item in items)
    return {
        "items": items,
        "verified_count": verified,
        "total_count": len(items),
        "progress_pct": round(verified / len(items) * 100, 1),
        "complete": verified == len(items),
        "persisted": False,
        **SAFETY,
    }


def build_limited_customer_checklist(
    evidence_records: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the BETA-4 ten-stage Evidence checklist without registration."""
    records = {} if evidence_records is None else evidence_records
    if not isinstance(records, Mapping):
        raise ValueError("evidence records must be a mapping")
    allowed = {stage["key"] for stage in LIMITED_CUSTOMER_STAGES}
    unknown = set(records) - allowed
    if unknown:
        raise ValueError(f"unknown limited customer stage: {sorted(unknown)[0]}")
    items: list[dict[str, Any]] = []
    for sequence, stage in enumerate(LIMITED_CUSTOMER_STAGES, start=1):
        raw = records.get(stage["key"], {})
        if not isinstance(raw, Mapping):
            raise ValueError(f'evidence {stage["key"]} must be a mapping')
        status = str(raw.get("evidence_status", "MISSING")).upper()
        if status not in {"MISSING", "VERIFIED", "REJECTED"}:
            raise ValueError(f'evidence {stage["key"]} has invalid status')
        if status in {"VERIFIED", "REJECTED"}:
            for field in ("evidence_id", "observed_at", "source", "approved_by"):
                if not str(raw.get(field, "")).strip():
                    raise ValueError(f'evidence {stage["key"]} missing {field}')
        items.append({
            "sequence": sequence,
            **deepcopy(stage),
            "evidence_id": raw.get("evidence_id", f"B4-EV-{sequence:03d}"),
            "evidence_status": status,
            "observed_at": raw.get("observed_at"),
            "source": raw.get("source"),
            "approved_by": raw.get("approved_by"),
            "reason": raw.get("reason", "Evidence not received" if status == "MISSING" else None),
            "persisted": False,
            **SAFETY,
        })
    verified = sum(item["evidence_status"] == "VERIFIED" for item in items)
    return {
        "items": items,
        "verified_count": verified,
        "total_count": len(items),
        "progress_pct": round(verified / len(items) * 100, 1),
        "complete": verified == len(items),
        "knowledge_registered_count": 0,
        "learning_registered_count": 0,
        "persisted": False,
        **SAFETY,
    }


class DailyOperationProjection:
    """Build the DAILY-1 dashboard payload from existing local facts."""

    def __init__(self, *, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root)

    def build(
        self,
        *,
        operation_date: str | None = None,
        workspace_projection: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        as_of = operation_date or date.today().isoformat()
        owner = self._load_json("config/owner_configuration.json")
        workspace = self._load_json("config/google_workspace.json")

        owner_decisions = owner.get("owner_decisions", [])
        if not isinstance(owner_decisions, list):
            owner_decisions = []
        unresolved = [
            item for item in owner_decisions
            if isinstance(item, dict) and item.get("final_value") in (None, "")
        ]
        dashboard = owner.get("dashboard", {}) if isinstance(owner.get("dashboard"), dict) else {}
        revenue = self._metric(dashboard, "revenue", default=0)
        customers = self._metric(dashboard, "customers", default=0)
        projects = self._metric(dashboard, "projects", default=0)

        workspace_enabled = workspace.get("enabled") is True
        auth = workspace.get("auth", {}) if isinstance(workspace.get("auth"), dict) else {}
        auth_mode = str(auth.get("mode", "disabled"))
        workspace_ready = workspace_enabled and auth_mode != "disabled"
        gwos4 = self._workspace_projection(workspace_projection)

        tasks = self._tasks(len(unresolved))
        proposal = {
            "proposal_id": f"daily-commander-{as_of}",
            "title": "初収益に近い日次作業のレビュー順序",
            "reason": "Owner未確定値を先に解消し、note・Threads・公式サイトの公開判断に必要な前提を揃える。",
            "proposed_steps": [task["title"] for task in tasks],
            "status": "review_required",
            "proposal_only": True,
            "workspace_context": deepcopy(gwos4.get("commander", {})),
            **SAFETY,
        }
        knowledge = {
            "candidate_count": 0,
            "registration_status": "not_registered",
            "next_gate": "verified evidence -> redaction -> domain review -> knowledge review",
            "automatic_registration": False,
            "reason": "DAILY-1では承認済み案件Evidenceが確認できないため、Knowledge候補を生成・登録しない。",
            **SAFETY,
        }
        learning = {
            "proposal_id": f"daily-learning-{as_of}",
            "hypothesis": "Owner未確定値を解消すると、初収益向け公開物のレビュー停滞を減らせる。",
            "evidence": f"owner_configuration.json の未確定Owner Decision: {len(unresolved)}件",
            "primary_kpi": "未確定Owner Decision件数",
            "target": 0,
            "status": "review_required",
            "proposal_only": True,
            "automatic_implementation": False,
            **SAFETY,
        }
        return {
            "phase": "DAILY-1",
            "operation_date": as_of,
            "status": "review_required",
            "safety": dict(SAFETY),
            "executive_dashboard": {
                "verified_revenue_jpy": revenue,
                "verified_customers": customers,
                "verified_active_projects": projects,
                "owner_decisions_unresolved": len(unresolved),
                "today_task_count": len(tasks),
                "workspace_projection_status": "read_projection_ready" if gwos4 else ("read_ready" if workspace_ready else "not_connected"),
                "workspace_read_counts": deepcopy(gwos4.get("source_counts", {})),
                "knowledge_candidate_count": 0,
                "learning_proposal_count": 1,
            },
            "todays_tasks": tasks,
            "commander": proposal,
            "customer_workspace": {
                "mode": "read_projection",
                "verified_customers": customers,
                "verified_active_projects": projects,
                "raw_customer_content_exposed": False,
                "workspace_projection": deepcopy(gwos4.get("customer_workspace", {})),
                **SAFETY,
            },
            "google_workspace": gwos4.get("google_workspace") or {
                "mode": "operational_read_projection",
                "connection_status": "configured" if workspace_ready else "not_connected",
                "auth_mode": auth_mode,
                "allowed": ["sheets_read", "drive_metadata_read", "calendar_read", "gmail_metadata_read"],
                "gmail_body_read_allowed": False,
                "drive_content_read_allowed": False,
                "external_request_sent": False,
                **SAFETY,
            },
            "knowledge_registration": knowledge,
            "learning_proposal": learning,
            "daily_summary": {
                "confirmed_facts": [
                    f"検証済み売上: {revenue} JPY",
                    f"検証済み顧客: {customers}件",
                    f"検証済み進行案件: {projects}件",
                    f"Owner未確定値: {len(unresolved)}件",
                    f"Google Workspace: {'read ready' if workspace_ready else 'not connected'}",
                ],
                "inferences": [learning["hypothesis"]],
                "unknowns": [item.get("name", item.get("id", "unknown")) for item in unresolved],
                "completion_condition": "全項目を人間がレビューし、必要な別Operationを個別承認する。",
                **SAFETY,
            },
        }

    def build_business_home(self, *, operation_date: str | None = None) -> dict[str, Any]:
        """Integrate existing Engine projections into OPERATION-1 Business Home.

        All inputs are existing local projections.  No persistence, connection,
        queue mutation, registration, publication, contract, or payment occurs.
        """
        from src.content_engine.marketing import build_campaign_timeline, build_marketing_dashboard
        from src.sales_engine.acquisition import build_funnel_projection, build_pipeline_projection
        from src.sales_engine.delivery_cycle import build_cycle_projection
        from src.sales_engine.owner_decision_freeze import build_decision_dashboard

        daily = self.build(operation_date=operation_date)
        sales_pipeline = build_pipeline_projection()
        inquiry = build_funnel_projection()
        delivery = build_cycle_projection()
        marketing_timeline = build_campaign_timeline()
        marketing = build_marketing_dashboard()
        owner = build_decision_dashboard()
        metrics = daily["executive_dashboard"]
        unresolved = metrics["owner_decisions_unresolved"]
        active_projects = metrics["verified_active_projects"]
        verified_revenue = metrics["verified_revenue_jpy"]

        if unresolved:
            priority = "Owner未決事項をReviewし、販売開始条件を確定する"
            bottleneck = f"Owner未決事項 {unresolved}件"
            risk = "価格・税・窓口・SLA等が未決のため販売開始できない"
            next_action = "Owner Decision Dashboardで最優先項目をReviewする"
        elif active_projects:
            priority = "進行案件のDelivery blockerを確認する"
            bottleneck = "進行案件の完了Evidence未確認"
            risk = "納期・受領・レビューEvidence不足"
            next_action = "Delivery一覧をReviewする"
        else:
            priority = "初回問い合わせ獲得に近いSales候補をReviewする"
            bottleneck = "検証済み問い合わせ0件"
            risk = "初収益へ接続する顧客Evidenceがない"
            next_action = "Sales候補と問い合わせ導線をReviewする"

        daily_flow_names = (
            "Morning", "Executive確認", "Today's Tasks", "Sales", "Delivery",
            "Marketing", "Learning", "Review", "End of Day",
        )
        daily_flow = [
            {
                "sequence": index,
                "name": name,
                "status": "CURRENT" if index == 1 else "PENDING_REVIEW",
                "execute_allowed": False,
            }
            for index, name in enumerate(daily_flow_names, start=1)
        ]
        commander = {
            "proposal_id": f'operation1-priority-{daily["operation_date"]}',
            "question": "今日は何を優先すべきか",
            "proposal": priority,
            "basis": bottleneck,
            "status": "PROPOSAL",
            "proposal_only": True,
            **SAFETY,
        }
        learning = {
            "candidate_id": f'operation1-learning-{daily["operation_date"]}',
            "title": "本日の改善候補",
            "proposal": daily["learning_proposal"]["hypothesis"],
            "evidence": daily["learning_proposal"]["evidence"],
            "status": "PROPOSAL",
            "proposal_only": True,
            "registered": False,
            **SAFETY,
        }
        return {
            "phase": "OPERATION-1 DAILY BUSINESS MODE",
            "operation_date": daily["operation_date"],
            "status": "REVIEW_REQUIRED",
            "todays_focus": priority,
            "daily_flow": daily_flow,
            "todays_tasks": deepcopy(daily["todays_tasks"]),
            "projects": {
                "records": deepcopy(delivery["records"]),
                "active_count": active_projects,
                "projection_count": delivery["counts"]["record_count"],
                **SAFETY,
            },
            "inquiries": {
                "metrics": deepcopy(inquiry["metrics"]),
                "records": deepcopy(sales_pipeline["records"]),
                **SAFETY,
            },
            "revenue": {
                "verified_revenue_jpy": verified_revenue,
                "recognition_basis": "VERIFIED_ACTUAL_ONLY",
                **SAFETY,
            },
            "marketing": {
                "metrics": deepcopy(marketing["metrics"]),
                "timeline_counts": deepcopy(marketing_timeline["counts"]),
                **SAFETY,
            },
            "commander": commander,
            "learning": learning,
            "owner_unresolved": {
                "count": unresolved,
                "items": deepcopy(daily["daily_summary"]["unknowns"]),
                "oa_decision_proposal_count": owner["counts"]["PROPOSAL"],
                **SAFETY,
            },
            "executive": {
                "todays_kpi": {
                    "verified_revenue_jpy": verified_revenue,
                    "inquiries": inquiry["metrics"]["inquiries"],
                    "active_projects": active_projects,
                    "published_articles": marketing["metrics"]["published_article_count"],
                    "owner_unresolved": unresolved,
                },
                "todays_priority": priority,
                "current_bottleneck": bottleneck,
                "risk": risk,
                "next_action": next_action,
                **SAFETY,
            },
            "quick_actions": [
                {"label": label, "enabled": False}
                for label in ("Sales", "Delivery", "Marketing", "Learning", "Review", "End of Day")
            ],
            "existing_engine_integration": {
                "Business": "DailyOperationProjection",
                "Sales": "sales_engine.acquisition",
                "Delivery": "sales_engine.delivery_cycle",
                "Marketing": "content_engine.marketing",
                "Commander": "proposal projection",
                "Learning": "daily learning proposal",
                "Owner": "owner decision projection",
            },
            "new_engine_added": False,
            **SAFETY,
        }

    def build_business_execution_mode(self, *, operation_date: str | None = None) -> dict[str, Any]:
        """Build OPERATION-2 as a read-only view over existing projections."""
        home = self.build_business_home(operation_date=operation_date)
        executive = home["executive"]
        tasks = deepcopy(home["todays_tasks"])
        priority_rows = [
            {"rank": 1, "priority": executive["todays_priority"], "basis": executive["current_bottleneck"], "status": "REVIEW_REQUIRED"},
            {"rank": 2, "priority": executive["next_action"], "basis": executive["risk"], "status": "PROPOSAL"},
            {"rank": 3, "priority": "End of Dayで未完了・Evidence・翌日候補を確認する", "basis": "日次運用を再現可能に閉じる", "status": "PENDING_REVIEW"},
        ]
        routes = {
            "business_home": "pages/47_Daily_Operation.py",
            "commander": "pages/45_Commander_Console.py",
            "sales": "pages/52_Sales_Acquisition.py",
            "marketing": "pages/53_Marketing_Content.py",
            "delivery": "pages/55_Delivery_Case_Study.py",
            "learning": "pages/50_Note_Workspace.py",
            "executive": "pages/8_Dashboard.py",
            "review": "pages/51_Mobile_Review_Hub.py",
        }
        return {
            **home,
            "phase": "OPERATION-2 BUSINESS EXECUTION MODE",
            "entrypoint": "Business Home",
            "todays_priorities": priority_rows,
            "commander_daily_mission": {
                "mission": home["commander"]["proposal"],
                "basis": home["commander"]["basis"],
                "status": "PROPOSAL",
                **SAFETY,
            },
            "sales_queue": {
                "records": deepcopy(home["inquiries"]["records"]),
                "count": len(home["inquiries"]["records"]),
                "empty_message": "Sales候補は0件です。既存Sales画面で導線をReviewしてください。",
                **SAFETY,
            },
            "marketing_queue": {
                "records": [deepcopy(home["marketing"]["metrics"]), deepcopy(home["marketing"]["timeline_counts"])],
                "count": sum(int(value) for value in home["marketing"]["timeline_counts"].values() if isinstance(value, (int, float))),
                "empty_message": "Marketing実行候補は0件です。公開・投稿は行いません。",
                **SAFETY,
            },
            "delivery_queue": {
                "records": deepcopy(home["projects"]["records"]),
                "count": len(home["projects"]["records"]),
                "empty_message": "進行Delivery候補は0件です。",
                **SAFETY,
            },
            "learning_proposal": deepcopy(home["learning"]),
            "executive_summary": {
                **deepcopy(executive),
                "task_count": len(tasks),
                "sales_queue_count": len(home["inquiries"]["records"]),
                "delivery_queue_count": len(home["projects"]["records"]),
                **SAFETY,
            },
            "end_of_day_summary": {
                "completed_count": sum(task.get("status") == "completed" for task in tasks),
                "review_required_count": sum(task.get("status") == "review_required" for task in tasks),
                "verified_revenue_jpy": home["revenue"]["verified_revenue_jpy"],
                "unresolved_owner_count": home["owner_unresolved"]["count"],
                "close_condition": "人間が全Queue・Evidence・未決事項・翌日優先候補をReviewする",
                **SAFETY,
            },
            "navigation_routes": routes,
            "quick_actions": [
                {"label": label, "enabled": False, "reason": "Projection only / Human Review Required"}
                for label in ("Execute Mission", "Send Sales", "Publish Marketing", "Update Delivery", "Register Learning", "Close Day")
            ],
            "new_engine_added": False,
        }

    def build_real_operation(
        self,
        *,
        operation_date: str | None = None,
        evidence_records: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Build BETA-3 real-operation preparation from existing projections."""
        business = self.build_business_home(operation_date=operation_date)
        readiness = build_first_customer_readiness(evidence_records)
        owner_unresolved = business["owner_unresolved"]["count"]
        owner_total = 11
        owner_approved = max(owner_total - owner_unresolved, 0)
        incomplete = [item for item in readiness["items"] if item["evidence_status"] != "VERIFIED"]
        blockers = [
            {
                "blocker_id": f'B3-BL-{item["sequence"]:03d}',
                "type": "FIRST_CUSTOMER_EVIDENCE",
                "label": item["label"],
                "status": item["evidence_status"],
            }
            for item in incomplete
        ]
        if owner_unresolved:
            blockers.insert(0, {
                "blocker_id": "B3-BL-OWNER",
                "type": "OWNER_APPROVAL",
                "label": f"Owner未承認事項 {owner_unresolved}件",
                "status": "BLOCKED",
            })
        if blockers:
            first = blockers[0]
            next_action = (
                "Owner未承認事項を1件Reviewする"
                if first["type"] == "OWNER_APPROVAL"
                else f'{first["label"]}のEvidenceをReviewする'
            )
        else:
            next_action = "初回受注開始可否をHuman Reviewする"
        owner_pct = round(owner_approved / owner_total * 100, 1)
        operational_readiness = round((readiness["progress_pct"] + owner_pct) / 2, 1)
        commander = {
            "question": "次に行うべき1つの行動",
            "proposal": next_action,
            "proposal_only": True,
            "status": "PROPOSAL",
            "action_count": 1,
            **SAFETY,
        }
        learning = {
            "title": "First Customer改善提案",
            "proposal": (
                "Evidence取得順序を標準化し、未確認段階を1つずつ解消する"
                if incomplete else "完了Evidenceの再現性をHuman Reviewする"
            ),
            "basis": f'未確認またはRejected Evidence: {len(incomplete)}件',
            "proposal_only": True,
            "status": "PROPOSAL",
            "registered": False,
            **SAFETY,
        }
        return {
            "phase": "BETA-3 REAL OPERATION PREPARATION",
            "operation_date": business["operation_date"],
            "status": "REVIEW_REQUIRED",
            "highest_priority_task": next_action,
            "inquiry_status": deepcopy(business["inquiries"]),
            "project_progress": deepcopy(business["projects"]),
            "verified_actual_revenue": deepcopy(business["revenue"]),
            "owner_unapproved": deepcopy(business["owner_unresolved"]),
            "launch_blockers": blockers,
            "commander": commander,
            "learning": learning,
            "first_customer_readiness": readiness,
            "executive": {
                "first_revenue_progress_pct": readiness["progress_pct"],
                "first_revenue_progress_basis": "VERIFIED first-customer stages / 8",
                "launch_blocker_count": len(blockers),
                "operational_readiness_pct": operational_readiness,
                "operational_readiness_basis": "(first revenue progress + Owner approval %) / 2",
                "verified_actual_revenue_jpy": business["revenue"]["verified_revenue_jpy"],
                **SAFETY,
            },
            "quick_actions": [
                {"label": label, "enabled": False}
                for label in ("Inquiry", "Hearing", "Estimate", "Approve", "Production", "Delivery", "Review", "Case Study")
            ],
            "existing_engine_integration": deepcopy(business["existing_engine_integration"]),
            "new_engine_added": False,
            **SAFETY,
        }

    def build_limited_customer_activation(
        self,
        *,
        operation_date: str | None = None,
        evidence_records: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Build BETA-4 limited-customer activation as a safe read projection."""
        from src.sales_engine.limited_beta_preparation import LIMITED_BETA_CONFIGURATION

        real = self.build_real_operation(operation_date=operation_date)
        checklist = build_limited_customer_checklist(evidence_records)
        capacity_limit = int(LIMITED_BETA_CONFIGURATION["recruitment_limit"])
        current_count = int(LIMITED_BETA_CONFIGURATION["current_intake_count"])
        owner_unapproved = int(real["owner_unapproved"]["count"])
        owner_total = 11
        owner_approved = max(owner_total - owner_unapproved, 0)
        incomplete = [item for item in checklist["items"] if item["evidence_status"] != "VERIFIED"]
        blockers = [
            {
                "blocker_id": f'B4-BL-{item["sequence"]:03d}',
                "type": "CUSTOMER_EVIDENCE",
                "label": item["label"],
                "status": item["evidence_status"],
            }
            for item in incomplete
        ]
        if owner_unapproved:
            blockers.insert(0, {
                "blocker_id": "B4-BL-OWNER",
                "type": "OWNER_APPROVAL",
                "label": f"Owner未承認事項 {owner_unapproved}件",
                "status": "BLOCKED",
            })
        configured_remaining = max(capacity_limit - current_count, 0)
        available_count = configured_remaining if not blockers else 0
        stop_reason = blockers[0]["label"] if blockers else "なし（Human activation review required）"
        if blockers:
            next_human_action = (
                "Owner未承認事項を1件Reviewする"
                if blockers[0]["type"] == "OWNER_APPROVAL"
                else f'{blockers[0]["label"]}のEvidenceをReviewする'
            )
        else:
            next_human_action = "限定顧客受付開始の可否をHuman Reviewする"
        owner_pct = round(owner_approved / owner_total * 100, 1)
        beta_completion = round((checklist["progress_pct"] + owner_pct) / 2, 1)
        operational_health = "REVIEW_READY" if not blockers else "BLOCKED"
        return {
            "phase": "BETA-4 LIMITED CUSTOMER ACTIVATION",
            "operation_date": real["operation_date"],
            "status": "REVIEW_REQUIRED",
            "customer_activation": {
                "configured_capacity": capacity_limit,
                "available_capacity": available_count,
                "current_intake_count": current_count,
                "configured_remaining_capacity": configured_remaining,
                "intake_allowed": False,
                "stop_reason": stop_reason,
                **SAFETY,
            },
            "launch_blockers": blockers,
            "owner_approval": {
                "approved_count": owner_approved,
                "unapproved_count": owner_unapproved,
                "total_count": owner_total,
                "approval_pct": owner_pct,
                **SAFETY,
            },
            "evidence": deepcopy(checklist["items"]),
            "first_customer_checklist": checklist,
            "commander": {
                "question": "次に人間が実行する唯一の作業",
                "proposal": next_human_action,
                "proposal_only": True,
                "action_count": 1,
                "status": "PROPOSAL",
                **SAFETY,
            },
            "learning": {
                "title": "改善候補",
                "proposal": (
                    "未確認Evidenceを受付順に1件ずつ解消する"
                    if incomplete else "限定顧客運用Evidenceの再現性をReviewする"
                ),
                "proposal_only": True,
                "registered": False,
                "status": "PROPOSAL",
                **SAFETY,
            },
            "executive": {
                "first_customer_progress_pct": checklist["progress_pct"],
                "first_customer_progress_basis": "VERIFIED checklist items / 10",
                "beta_completion_pct": beta_completion,
                "beta_completion_basis": "(first customer progress + Owner approval %) / 2",
                "verified_revenue_jpy": real["verified_actual_revenue"]["verified_revenue_jpy"],
                "verified_revenue_basis": "VERIFIED_ACTUAL_ONLY",
                "operational_health": operational_health,
                "launch_blocker_count": len(blockers),
                **SAFETY,
            },
            "quick_actions": [
                {"label": stage["label"], "enabled": False}
                for stage in LIMITED_CUSTOMER_STAGES
            ],
            "existing_engine_integration": deepcopy(real["existing_engine_integration"]),
            "new_engine_added": False,
            **SAFETY,
        }

    @staticmethod
    def _workspace_projection(value: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(value, dict) or value.get("phase") != "GWOS-4" or value.get("validation_status") != "valid":
            return {}
        consumers = value.get("consumers", {}) if isinstance(value.get("consumers"), dict) else {}
        source_counts = value.get("source_counts", {}) if isinstance(value.get("source_counts"), dict) else {}
        return {
            "source_counts": deepcopy(source_counts),
            "commander": deepcopy(consumers.get("commander", {})),
            "customer_workspace": deepcopy(consumers.get("customer_workspace", {})),
            "google_workspace": {
                "mode": "operational_read_projection",
                "connection_status": "read_projection_ready",
                "projection_id": value.get("projection_id"),
                "source_counts": deepcopy(source_counts),
                "daily_projection": deepcopy(consumers.get("daily_operation", {})),
                "network_request_observed": value.get("network_request_observed") is True,
                "workspace_read_only": True,
                "approval_required": True,
                "review_required": True,
                "execute_allowed": True,
                "execution_scope": "operational_workspace_read_only",
                "dry_run": True,
                "workspace_write_allowed": False,
                "mail_send_allowed": False,
                "knowledge_write_allowed": False,
                "production_change_allowed": False,
                "external_request_sent": False,
            },
        }

    def _load_json(self, relative: str) -> dict[str, Any]:
        path = self.root / relative
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        return dict(value) if isinstance(value, dict) else {}

    @staticmethod
    def _metric(dashboard: dict[str, Any], name: str, *, default: int) -> int:
        item = dashboard.get(name, {})
        value = item.get("value", default) if isinstance(item, dict) else default
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else default

    @staticmethod
    def _tasks(unresolved_count: int) -> list[dict[str, Any]]:
        rows = [
            {
                "task_id": "daily-owner-review",
                "title": f"Owner未確定値 {unresolved_count}件をレビュー",
                "priority": "high",
                "basis": "owner_configuration.json",
                "next_gate": "human_review",
            },
            {
                "task_id": "daily-first-revenue-review",
                "title": "初収益候補のEvidenceと公開前条件をレビュー",
                "priority": "high",
                "basis": "Revenue First policy",
                "next_gate": "human_review",
            },
            {
                "task_id": "daily-summary-review",
                "title": "Daily Summaryの事実・推測・不明点をレビュー",
                "priority": "medium",
                "basis": "DAILY-1 safety contract",
                "next_gate": "human_review",
            },
        ]
        return [{**row, "status": "review_required", "proposal_only": True, **SAFETY} for row in rows]
