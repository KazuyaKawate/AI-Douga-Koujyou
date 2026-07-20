"""Review-only commercial workflow for Sales Engine draft planning."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Mapping, Sequence

from .models import SalesRequest, canonical_hash
from .proposal_generator import ProposalGenerator
from .quotation_generator import QuotationGenerator
from .safety import SalesSafetyEnvelope


WORKFLOW_STEPS = (
    ("validation", "Validation"),
    ("proposal-draft", "Proposal Draft"),
    ("quotation-draft", "Quotation Draft"),
    ("lp-planning", "LP Planning"),
    ("sales-review-package", "Sales Review Package"),
)


@dataclass(frozen=True)
class SalesWorkflowResult:
    workflow_plan: tuple[dict[str, Any], ...]
    proposal_draft_reference: dict[str, Any]
    quotation_draft_reference: dict[str, Any]
    lp_planning_reference: dict[str, Any]
    review_package: dict[str, Any]
    safety: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_plan": [dict(step) for step in self.workflow_plan],
            "proposal_draft_reference": dict(self.proposal_draft_reference),
            "quotation_draft_reference": dict(self.quotation_draft_reference),
            "lp_planning_reference": dict(self.lp_planning_reference),
            "review_package": dict(self.review_package),
            "safety": dict(self.safety),
        }


class SalesWorkflow:
    """Build an in-memory review package without execution or registration."""

    def __init__(
        self,
        *,
        proposal_generator: ProposalGenerator | None = None,
        quotation_generator: QuotationGenerator | None = None,
    ) -> None:
        self._proposal_generator = proposal_generator or ProposalGenerator()
        self._quotation_generator = quotation_generator or QuotationGenerator()

    def plan(
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
    ) -> SalesWorkflowResult:
        normalized = request if isinstance(request, SalesRequest) else SalesRequest(**request)
        safety = SalesSafetyEnvelope().to_dict()
        proposal = self._proposal_generator.generate(normalized)
        quotation = self._quotation_generator.generate(
            normalized,
            issue_date=issue_date,
            valid_until=valid_until,
            price_min=price_min,
            price_max=price_max,
            currency=currency,
            deliverables=deliverables,
            optional_items=optional_items,
            assumptions=assumptions,
        )
        workflow_plan = tuple({
            "step_id": step_id,
            "name": name,
            "status": "planned",
            "review_required": True,
        } for step_id, name in WORKFLOW_STEPS)
        proposal_reference = {
            "artifact_type": "proposal",
            "artifact_id": proposal.proposal_id,
            "content_hash": proposal.content_hash,
            "status": proposal.status,
        }
        quotation_reference = {
            "artifact_type": "quotation",
            "artifact_id": quotation.quotation_id,
            "content_hash": quotation.content_hash,
            "status": quotation.status,
        }
        lp_reference_body = {
            "reference_type": "lp_planning",
            "request_id": normalized.request_id,
            "source_artifact_ids": [proposal.proposal_id, quotation.quotation_id],
            "status": "planned",
            "review_required": True,
        }
        lp_reference = {
            **lp_reference_body,
            "content_hash": canonical_hash(lp_reference_body),
        }
        review_body = {
            "request_id": normalized.request_id,
            "status": "review_required",
            "workflow_status": "planned",
            "proposal_draft_reference": proposal_reference,
            "quotation_draft_reference": quotation_reference,
            "lp_planning_reference": lp_reference,
            "safety_flags": safety,
            "prohibited_actions": [
                "execute", "queue_registration", "export", "revenue_update",
                "commander_connection", "external_request",
            ],
        }
        review_package = {**review_body, "content_hash": canonical_hash(review_body)}
        return SalesWorkflowResult(
            workflow_plan=workflow_plan,
            proposal_draft_reference=proposal_reference,
            quotation_draft_reference=quotation_reference,
            lp_planning_reference=lp_reference,
            review_package=review_package,
            safety=safety,
        )
