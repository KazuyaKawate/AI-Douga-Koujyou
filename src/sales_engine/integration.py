"""Deterministic, plan-only adapters for Sales Engine integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .models import SalesRequest, SalesValidationError, canonical_hash
from .safety import SalesSafetyEnvelope


@dataclass(frozen=True)
class AdapterDefinition:
    name: str
    capability: str
    mode: str


ADAPTERS = (
    AdapterDefinition("commander_chat", "request_entry", "input_only"),
    AdapterDefinition("business_engine", "business_context", "read_only"),
    AdapterDefinition("content_engine", "content_context", "read_only"),
    AdapterDefinition("lp_engine", "lp_generation", "plan_only"),
    AdapterDefinition("website_engine", "website_generation", "plan_only"),
    AdapterDefinition("common_publish_queue", "review_package_routing", "adapter_only"),
    AdapterDefinition("mobile_review_hub", "human_review_routing", "adapter_only"),
    AdapterDefinition("export_manager", "export_routing", "plan_only"),
    AdapterDefinition("revenue_engine", "revenue_handoff", "plan_only"),
)
ADAPTER_NAMES = frozenset(item.name for item in ADAPTERS)


def _validate_dependencies(dependencies: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(dependencies, Mapping):
        raise SalesValidationError("dependencies must be a mapping")
    unknown = sorted(set(dependencies) - ADAPTER_NAMES)
    if unknown:
        raise SalesValidationError(f"unknown adapter: {', '.join(unknown)}")
    invalid = sorted(name for name, adapter in dependencies.items() if adapter is None)
    if invalid:
        raise SalesValidationError(f"adapter must not be None: {', '.join(invalid)}")
    return dict(dependencies)


class SalesIntegrationPlanner:
    """Build integration metadata without invoking any supplied adapter."""

    def __init__(self, dependencies: Mapping[str, Any] | None = None, **adapters: Any) -> None:
        if dependencies is not None and adapters:
            raise SalesValidationError("provide dependencies or keyword adapters, not both")
        self._dependencies = _validate_dependencies(dependencies if dependencies is not None else adapters)

    def build_plan(self, request: SalesRequest | Mapping[str, Any]) -> dict[str, Any]:
        normalized = request if isinstance(request, SalesRequest) else SalesRequest(**request)
        sequence = [
            {
                "sequence": index,
                "adapter": item.name,
                "capability": item.capability,
                "mode": item.mode,
                "status": "planned",
                "configured": item.name in self._dependencies,
            }
            for index, item in enumerate(ADAPTERS, start=1)
        ]
        graph = [
            {"from": ADAPTERS[index - 1].name, "to": ADAPTERS[index].name, "status": "planned"}
            for index in range(1, len(ADAPTERS))
        ]
        routing = {item.name: item.capability for item in ADAPTERS}
        plan_id = f"sales-integration-{canonical_hash({'request_id': normalized.request_id, 'routing': routing})[:24]}"
        return {
            "plan_id": plan_id,
            "request_id": normalized.request_id,
            "status": "planned",
            "engine_routing_plan": routing,
            "dependency_graph": graph,
            "execution_sequence": sequence,
            "review_package_routing": {
                "queue_adapter": "common_publish_queue",
                "review_adapter": "mobile_review_hub",
                "status": "planned",
            },
            "export_routing": {"adapter": "export_manager", "status": "planned"},
            "revenue_handoff_plan": {"adapter": "revenue_engine", "status": "planned"},
            "safety_summary": SalesSafetyEnvelope().to_dict(),
        }


__all__ = ["ADAPTERS", "ADAPTER_NAMES", "AdapterDefinition", "SalesIntegrationPlanner"]
