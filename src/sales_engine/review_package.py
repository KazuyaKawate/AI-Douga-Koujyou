"""Deterministic, review-only Sales Review Package."""

from __future__ import annotations

from typing import Any, Sequence

from .models import Confidentiality, SalesRequest, canonical_hash
from .safety import SalesSafetyEnvelope


def build_review_package(
    request: SalesRequest,
    missing_information: Sequence[str],
    proposed_artifacts: Sequence[dict[str, Any]],
    planned_workflow: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    safety = SalesSafetyEnvelope().to_dict()
    body = {
        "request_summary": request.normalized(),
        "missing_information": list(missing_information),
        "proposed_artifacts": list(proposed_artifacts),
        "planned_workflow": list(planned_workflow),
        "confidentiality": request.confidentiality.value,
        "risks": ["Human review is required before any downstream action."],
        "safety_flags": safety,
        "approval_status": "human_review_required",
    }
    return {**body, "content_hash": canonical_hash(body)}
