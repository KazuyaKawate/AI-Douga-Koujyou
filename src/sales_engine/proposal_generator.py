"""Deterministic commercial proposal draft generation for Sales Engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .models import SalesRequest, canonical_hash, stable_artifact_id
from .safety import SalesSafetyEnvelope


SECTION_ORDER = (
    ("executive_summary", "Executive Summary"),
    ("customer_problems", "Customer Problems"),
    ("recommended_service", "Recommended Service"),
    ("expected_benefits", "Expected Benefits"),
    ("deliverables", "Deliverables"),
    ("timeline", "Timeline"),
    ("estimated_price_range", "Estimated Price Range"),
    ("review_notes", "Review Notes"),
    ("next_action", "Next Action"),
)


@dataclass(frozen=True)
class ProposalDraft:
    """Review-only proposal represented as structured data and Markdown."""

    proposal_id: str
    request_id: str
    title: str
    version: str
    status: str
    sections: dict[str, str]
    markdown: str
    content_hash: str
    safety: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "request_id": self.request_id,
            "title": self.title,
            "version": self.version,
            "status": self.status,
            "sections": dict(self.sections),
            "markdown": self.markdown,
            "content_hash": self.content_hash,
            "safety": dict(self.safety),
        }


class ProposalGenerator:
    """Generate deterministic drafts without executing any commercial action."""

    def generate(self, request: SalesRequest | Mapping[str, Any]) -> ProposalDraft:
        normalized = request if isinstance(request, SalesRequest) else SalesRequest(**request)
        sections = self._sections(normalized)
        title = f"Commercial Proposal Draft — {normalized.business_name}"
        markdown = self._markdown(title, sections)
        safety = SalesSafetyEnvelope().to_dict()
        identity = {
            "request_id": normalized.request_id,
            "title": title,
            "version": "1",
            "status": "review_required",
            "sections": sections,
            "markdown": markdown,
            "safety": safety,
        }
        return ProposalDraft(
            proposal_id=stable_artifact_id(normalized.request_id, "proposal", "1"),
            request_id=normalized.request_id,
            title=title,
            version="1",
            status="review_required",
            sections=sections,
            markdown=markdown,
            content_hash=canonical_hash(identity),
            safety=safety,
        )

    @staticmethod
    def _sections(request: SalesRequest) -> dict[str, str]:
        artifacts = ", ".join(request.requested_artifacts)
        notes = request.notes or "No additional customer notes were provided."
        return {
            "executive_summary": (
                f"This draft proposes {request.service_name} for {request.business_name}, "
                f"serving {request.target_customer} in the {request.industry} sector. "
                f"It is intended for human review and does not constitute a binding offer."
            ),
            "customer_problems": request.customer_problem,
            "recommended_service": (
                f"Provide {request.service_name} focused on the stated outcome: "
                f"{request.desired_outcome}. Scope must be confirmed during review."
            ),
            "expected_benefits": (
                f"The proposed work is expected to support {request.desired_outcome}. "
                "Benefits are targets, not guarantees, and require customer validation."
            ),
            "deliverables": (
                f"Draft deliverables: {artifacts}. Final scope, acceptance criteria, "
                "and ownership require human approval."
            ),
            "timeline": (
                f"Target deadline: {request.deadline}. Milestones and dependencies "
                "remain to be agreed before work begins."
            ),
            "estimated_price_range": (
                f"Customer-provided planning range: {request.budget_range}. "
                "This is a non-binding estimate subject to scope review."
            ),
            "review_notes": (
                f"Customer notes: {notes} Verify problem statement, scope, benefits, "
                "timeline, pricing, and deliverables before approval."
            ),
            "next_action": (
                "Human reviewer confirms or requests changes to this draft. No sending, "
                "publishing, contracting, invoicing, or production action is authorized."
            ),
        }

    @staticmethod
    def _markdown(title: str, sections: Mapping[str, str]) -> str:
        parts = [f"# {title}", "", "> Status: Review Required", ""]
        for key, heading in SECTION_ORDER:
            parts.extend((f"## {heading}", "", sections[key], ""))
        return "\n".join(parts).rstrip() + "\n"
