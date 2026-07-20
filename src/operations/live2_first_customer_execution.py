"""LIVE-2 first-customer execution review projection.

Owner-provided local records are copied into an in-memory review package.  This
module does not create Actuals, execute contracts, issue invoices, or communicate
with a customer.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any

from src.revenue_engine.revenue11_analytics import build_dashboard as build_revenue11


RECORD_TYPES = ("inquiries", "crm", "estimates", "contracts", "tasks", "deliveries", "invoices", "evidence")
SAFETY = {
    "local_first": True,
    "dry_run": True,
    "presentation_only": True,
    "owner_review_required": True,
    "execute_allowed": False,
    "production_actions_enabled": False,
    "external_request_sent": False,
    "actual_mutation_allowed": False,
}


def _records(package: dict[str, Any], name: str) -> list[dict[str, Any]]:
    value = package.get(name, {})
    value = value.get("records", []) if isinstance(value, dict) else []
    return deepcopy(value) if isinstance(value, list) else []


def build_execution_review(
    owner_acceptance: dict[str, Any] | None = None,
    actual_package: dict[str, Any] | None = None,
    operation_date: str | None = None,
) -> dict[str, Any]:
    """Project an evidence-based first-customer workflow without mutation."""
    acceptance = deepcopy(owner_acceptance or {})
    package = deepcopy(actual_package or {})
    records = {name: _records(package, name) for name in RECORD_TYPES}
    accepted = (
        acceptance.get("decision") == "GO"
        and bool(str(acceptance.get("owner_name") or "").strip())
        and bool(str(acceptance.get("review_date") or "").strip())
    )
    analytics = build_revenue11(package)
    revenue = analytics["actual"]["business_kpi"]["Revenue"]
    first_inquiry = bool(records["inquiries"])
    completed_case = any(row.get("status") in {"COMPLETED", "ACCEPTED"} for row in records["deliveries"])
    completion = "FIRST_CASE_COMPLETED" if completed_case else "FIRST_INQUIRY_RECORDED" if first_inquiry else "WAITING_FOR_FIRST_INQUIRY"
    today = operation_date or date.today().isoformat()
    evidence_ids = {row.get("evidence_id") for row in records["evidence"] if row.get("evidence_id")}
    return {
        "phase": "LIVE-2 FIRST CUSTOMER EXECUTION",
        "classification": "PRESENTATION ONLY",
        "operation_date": today,
        "owner_acceptance": {"completed": accepted, "status": "ACCEPTED" if accepted else "OWNER REVIEW REQUIRED"},
        "workflow": {name: {"count": len(rows), "records": rows} for name, rows in records.items() if name != "evidence"},
        "verified_revenue_jpy": revenue,
        "revenue11_analytics": deepcopy(analytics),
        "daily_operation_log": {
            "date": today,
            "counts": {name: len(rows) for name, rows in records.items()},
            "verified_revenue_jpy": revenue,
            "status": "REVIEW REQUIRED",
        },
        "evidence_archive": {"count": len(records["evidence"]), "evidence_ids": sorted(evidence_ids), "records": records["evidence"]},
        "completion": {"state": completion, "first_inquiry_recorded": first_inquiry, "first_case_completed": completed_case},
        "separation_contract": {"actual_source": "Owner-provided local evidence only", "projection_source": "Derived read-only analytics", "cross_mutation": False},
        "safety": deepcopy(SAFETY),
    }


def validate_execution_review(result: dict[str, Any]) -> None:
    if result.get("safety") != SAFETY:
        raise ValueError("unsafe LIVE-2 state")
    if result.get("classification") != "PRESENTATION ONLY":
        raise ValueError("Presentation Only required")
    if result.get("separation_contract", {}).get("cross_mutation") is not False:
        raise ValueError("Actual mutation prohibited")
    if result.get("verified_revenue_jpy", 0) < 0:
        raise ValueError("invalid verified revenue")

