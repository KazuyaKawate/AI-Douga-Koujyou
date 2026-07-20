"""Deterministic, review-only quotation draft generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Mapping, Sequence

from .models import SalesRequest, SalesValidationError, canonical_hash, stable_artifact_id
from .safety import SalesSafetyEnvelope


QUOTATION_SECTION_ORDER = (
    "quotation_number",
    "issue_date",
    "validity",
    "customer",
    "service",
    "deliverables",
    "estimated_price_range",
    "optional_items",
    "assumptions",
    "review_notes",
)

SECTION_HEADINGS = {
    "quotation_number": "Quotation Number",
    "issue_date": "Issue Date",
    "validity": "Validity",
    "customer": "Customer",
    "service": "Service",
    "deliverables": "Deliverables",
    "estimated_price_range": "Estimated Price Range",
    "optional_items": "Optional Items",
    "assumptions": "Assumptions",
    "review_notes": "Review Notes",
}


def _decimal(name: str, value: Decimal) -> Decimal:
    if not isinstance(value, Decimal):
        raise SalesValidationError(f"{name} must be Decimal")
    if not value.is_finite() or value < Decimal("0"):
        raise SalesValidationError(f"{name} must be a finite non-negative Decimal")
    return value


def _text_items(name: str, values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise SalesValidationError(f"{name} must be a sequence of strings")
    normalized = tuple(item.strip() for item in values if isinstance(item, str) and item.strip())
    if len(normalized) != len(values):
        raise SalesValidationError(f"{name} must contain non-empty strings")
    return normalized


@dataclass(frozen=True)
class QuotationDraft:
    quotation_id: str
    request_id: str
    quotation_number: str
    status: str
    sections: dict[str, Any]
    markdown: str
    content_hash: str
    safety: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "quotation_id": self.quotation_id,
            "request_id": self.request_id,
            "quotation_number": self.quotation_number,
            "status": self.status,
            "sections": dict(self.sections),
            "markdown": self.markdown,
            "content_hash": self.content_hash,
            "safety": dict(self.safety),
        }


class QuotationGenerator:
    """Create an in-memory quotation draft without tax or commercial execution."""

    def generate(
        self,
        request: SalesRequest | Mapping[str, Any],
        *,
        issue_date: date,
        valid_until: date,
        price_min: Decimal,
        price_max: Decimal,
        currency: str,
        deliverables: Sequence[str],
        optional_items: Sequence[str] = (),
        assumptions: Sequence[str] = (),
    ) -> QuotationDraft:
        normalized = request if isinstance(request, SalesRequest) else SalesRequest(**request)
        if not isinstance(issue_date, date) or not isinstance(valid_until, date):
            raise SalesValidationError("issue_date and valid_until must be date")
        if valid_until < issue_date:
            raise SalesValidationError("valid_until must not precede issue_date")
        minimum = _decimal("price_min", price_min)
        maximum = _decimal("price_max", price_max)
        if maximum < minimum:
            raise SalesValidationError("price_max must be greater than or equal to price_min")
        if not isinstance(currency, str) or not currency.strip():
            raise SalesValidationError("currency is required and must be explicit")
        currency = currency.strip().upper()
        deliverable_items = _text_items("deliverables", deliverables)
        if not deliverable_items:
            raise SalesValidationError("deliverables is required")
        option_items = _text_items("optional_items", optional_items)
        assumption_items = _text_items("assumptions", assumptions)

        quotation_number = f"Q-{canonical_hash([normalized.request_id, issue_date.isoformat()])[:12].upper()}"
        sections: dict[str, Any] = {
            "quotation_number": quotation_number,
            "issue_date": issue_date.isoformat(),
            "validity": f"Valid through {valid_until.isoformat()}, subject to human review.",
            "customer": normalized.business_name,
            "service": normalized.service_name,
            "deliverables": list(deliverable_items),
            "estimated_price_range": {
                "minimum": str(minimum),
                "maximum": str(maximum),
                "currency": currency,
                "basis": "Reference estimate only; not a final price.",
            },
            "optional_items": list(option_items),
            "assumptions": list(assumption_items) + [
                "Tax treatment is not calculated or determined.",
                "Payment terms are not determined.",
                "Legal clauses are not determined.",
            ],
            "review_notes": (
                "Human review is required for scope, price range, currency, tax treatment, "
                "validity, optional items, assumptions, and all commercial terms. This draft "
                "is not an invoice, contract, or binding quotation."
            ),
        }
        markdown = self._markdown(sections)
        safety = SalesSafetyEnvelope().to_dict()
        body = {
            "request_id": normalized.request_id,
            "quotation_number": quotation_number,
            "status": "review_required",
            "sections": sections,
            "markdown": markdown,
            "safety": safety,
        }
        return QuotationDraft(
            quotation_id=stable_artifact_id(normalized.request_id, "quotation", "1"),
            request_id=normalized.request_id,
            quotation_number=quotation_number,
            status="review_required",
            sections=sections,
            markdown=markdown,
            content_hash=canonical_hash(body),
            safety=safety,
        )

    @staticmethod
    def _markdown(sections: Mapping[str, Any]) -> str:
        parts = ["# Quotation Draft", "", "> Status: Review Required", ""]
        for key in QUOTATION_SECTION_ORDER:
            value = sections[key]
            parts.extend((f"## {SECTION_HEADINGS[key]}", ""))
            if key == "estimated_price_range":
                parts.append(
                    f"{value['minimum']}–{value['maximum']} {value['currency']} "
                    f"({value['basis']})"
                )
            elif isinstance(value, list):
                parts.extend(f"- {item}" for item in value)
                if not value:
                    parts.append("- None specified")
            else:
                parts.append(str(value))
            parts.append("")
        return "\n".join(parts).rstrip() + "\n"
