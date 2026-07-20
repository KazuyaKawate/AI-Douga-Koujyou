"""Pure planning orchestrator; it never invokes injected dependencies."""

from __future__ import annotations

from typing import Any, Mapping

from .models import SalesRequest, SalesValidationError, stable_artifact_id
from .review_package import build_review_package
from .safety import SalesSafetyEnvelope

ALLOWED_DEPENDENCIES = frozenset({
    "business_engine", "content_engine", "lp_engine", "website_engine",
    "common_publish_queue", "mobile_review_hub", "export_manager", "revenue_engine",
})
WORKFLOW = (
    ("lead-intake", "Lead Intake", None),
    ("business-interview", "Business Interview", "business_engine"),
    ("qualification", "Qualification", "business_engine"),
    ("recommendation", "Recommendation", "content_engine"),
    ("artifact-planning", "Artifact Planning", "content_engine"),
    ("human-review", "Human Review", "mobile_review_hub"),
)


class SalesOrchestrator:
    def __init__(self, **dependencies: Any) -> None:
        invalid = sorted(set(dependencies) - ALLOWED_DEPENDENCIES)
        if invalid:
            raise SalesValidationError(f"unsupported dependency: {', '.join(invalid)}")
        self._dependencies = dict(dependencies)

    def plan(self, request: SalesRequest | Mapping[str, Any]) -> dict[str, Any]:
        normalized_request = request if isinstance(request, SalesRequest) else SalesRequest(**request)
        missing = [name for name in ("industry", "customer_problem", "desired_outcome", "budget_range", "deadline")
                   if not getattr(normalized_request, name)]
        status = "blocked" if missing else "planned"
        workflow = [{
            "step_id": step_id, "name": name, "status": status,
            "requires_human_review": True, "engine_reference": engine,
        } for step_id, name, engine in WORKFLOW]
        artifact_plan = [{
            "artifact_id": stable_artifact_id(normalized_request.request_id, artifact_type, "1"),
            "artifact_type": artifact_type, "version": "1", "status": status,
            "confidentiality": normalized_request.confidentiality.value,
        } for artifact_type in normalized_request.requested_artifacts]
        review = build_review_package(normalized_request, missing, artifact_plan, workflow)
        return {
            "normalized_request": normalized_request.normalized(),
            "planned_workflow": workflow,
            "requested_artifact_plan": artifact_plan,
            "review_package": review,
            "safety_summary": SalesSafetyEnvelope().to_dict(),
            "missing_information_list": missing,
        }
