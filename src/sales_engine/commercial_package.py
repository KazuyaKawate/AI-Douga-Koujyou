"""Review package assembly for commercial proposal drafts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from .models import SalesRequest, canonical_hash
from .proposal_generator import ProposalGenerator
from .safety import SalesSafetyEnvelope


@dataclass(frozen=True)
class CommercialPackage:
    """In-memory Markdown and JSON proposal package; no export or queue behavior."""

    package_id: str
    status: str
    markdown: str
    json_data: dict[str, Any]
    review_package: dict[str, Any]
    safety: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "status": self.status,
            "markdown": self.markdown,
            "json": dict(self.json_data),
            "review_package": dict(self.review_package),
            "safety": dict(self.safety),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, indent=2)


def build_commercial_package(
    request: SalesRequest | Mapping[str, Any],
    *,
    generator: ProposalGenerator | None = None,
) -> CommercialPackage:
    """Build an immutable review package without filesystem or external side effects."""
    draft = (generator or ProposalGenerator()).generate(request)
    safety = SalesSafetyEnvelope().to_dict()
    proposal_data = draft.to_dict()
    review = {
        "approval_status": "human_review_required",
        "review_required": True,
        "review_checklist": [
            "Confirm customer problem and desired outcome",
            "Confirm service scope and deliverables",
            "Confirm timeline and dependencies",
            "Confirm estimated price range",
            "Approve or request changes",
        ],
        "prohibited_actions": [
            "send", "publish", "export", "queue", "invoice", "contract", "collect_revenue"
        ],
        "safety_flags": safety,
    }
    package_body = {
        "status": "review_required",
        "proposal": proposal_data,
        "review_package": review,
        "safety": safety,
    }
    return CommercialPackage(
        package_id=f"commercial-package-{canonical_hash(package_body)[:24]}",
        status="review_required",
        markdown=draft.markdown,
        json_data=proposal_data,
        review_package=review,
        safety=safety,
    )
