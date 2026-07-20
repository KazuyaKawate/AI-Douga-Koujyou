"""Commander-to-Sales planning adapter (Phase 116).

This module is deliberately in-memory and review-only.  It creates a validated
``SalesRequest`` and invokes only ``SalesWorkflow.plan``; it has no operational
dependencies or persistence surface.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from src.sales_engine.models import SalesRequest, SalesValidationError
from src.sales_engine.safety import SalesSafetyEnvelope
from src.sales_engine.workflow import SalesWorkflow


SALES_INTENT = "sales_planning"
_SALES_TERMS = re.compile(
    r"\b(?:sales|proposal|quotation|quote|estimate|landing\s*page|lp)\b|"
    r"営業|提案書|提案|見積書|見積|ランディングページ",
    re.IGNORECASE,
)
_INDUSTRIES = (
    (re.compile(r"\b(?:restaurant|cafe|bar|diner)\b|飲食店|レストラン|カフェ", re.IGNORECASE), "restaurant"),
    (re.compile(r"\b(?:software|saas)\b|ソフトウェア", re.IGNORECASE), "software"),
    (re.compile(r"\b(?:retail|shop|store)\b|小売|店舗", re.IGNORECASE), "retail"),
)


class CommanderSalesRouter:
    """Normalize Commander chat input into a fail-closed Sales plan."""

    def __init__(self, workflow: SalesWorkflow | None = None) -> None:
        self._workflow = workflow or SalesWorkflow()

    def detect_intent(self, instruction: str) -> str | None:
        text = self._instruction(instruction)
        return SALES_INTENT if _SALES_TERMS.search(text) else None

    def normalize_request(
        self,
        instruction: str,
        request: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        text = self._instruction(instruction)
        supplied = dict(request or {})
        industry = str(supplied.get("industry") or self._detect_industry(text)).strip()
        business_name = str(supplied.get("business_name") or self._default_business_name(industry)).strip()
        defaults: dict[str, Any] = {
            "business_name": business_name,
            "industry": industry,
            "service_name": "sales proposal planning",
            "target_customer": f"prospective customers of {business_name}",
            "customer_problem": "",
            "desired_outcome": "reviewable sales proposal package",
            "budget_range": "",
            "deadline": "",
            "requested_artifacts": ("proposal", "quotation"),
            "notes": text,
            "execute_allowed": False,
            "production_actions_enabled": False,
        }
        defaults.update(supplied)
        # Caller input can never relax the Commander safety boundary.
        defaults["execute_allowed"] = False
        defaults["production_actions_enabled"] = False
        defaults["requested_artifacts"] = tuple(defaults["requested_artifacts"])
        return defaults

    def route(
        self,
        instruction: str,
        request: Mapping[str, Any] | None = None,
        *,
        commercial_terms: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.detect_intent(instruction) != SALES_INTENT:
            raise SalesValidationError("instruction is not a sales planning request")

        normalized = self.normalize_request(instruction, request)
        sales_request = SalesRequest(**normalized)
        terms = dict(commercial_terms or {})
        issue_date = self._date(terms.get("issue_date"), default=date(1970, 1, 1))
        valid_until = self._date(terms.get("valid_until"), default=issue_date)
        price_min = self._decimal(terms.get("price_min", 0), "price_min")
        price_max = self._decimal(terms.get("price_max", price_min), "price_max")
        result = self._workflow.plan(
            sales_request,
            issue_date=issue_date,
            valid_until=valid_until,
            price_min=price_min,
            price_max=price_max,
            currency=str(terms.get("currency", "JPY")),
            deliverables=tuple(terms.get("deliverables") or ("Proposal draft", "Quotation draft", "LP plan")),
            optional_items=tuple(terms.get("optional_items") or ()),
            assumptions=tuple(terms.get("assumptions") or ()),
        ).to_dict()
        safety = SalesSafetyEnvelope().to_dict()
        return {
            "ok": True,
            "intent": SALES_INTENT,
            "route": ["commander", "sales_router", "sales_workflow", "review_package", "stop"],
            "normalized_request": sales_request.normalized(),
            **result,
            **safety,
        }

    @staticmethod
    def _instruction(instruction: str) -> str:
        if not isinstance(instruction, str) or not instruction.strip():
            raise SalesValidationError("instruction is required")
        return instruction.strip()

    @staticmethod
    def _detect_industry(instruction: str) -> str:
        for pattern, industry in _INDUSTRIES:
            if pattern.search(instruction):
                return industry
        return "general"

    @staticmethod
    def _default_business_name(industry: str) -> str:
        return f"Unnamed {industry} business" if industry != "general" else "Unnamed business"

    @staticmethod
    def _date(value: Any, *, default: date) -> date:
        if value in (None, ""):
            return default
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except ValueError as exc:
            raise SalesValidationError("commercial date must use YYYY-MM-DD") from exc

    @staticmethod
    def _decimal(value: Any, name: str) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise SalesValidationError(f"{name} must be numeric") from exc


def plan_sales_request(
    instruction: str,
    request: Mapping[str, Any] | None = None,
    *,
    commercial_terms: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Functional entry point for Commander chat integrations."""
    return CommanderSalesRouter().route(instruction, request, commercial_terms=commercial_terms)
