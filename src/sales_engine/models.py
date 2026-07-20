"""Validated, deterministic Sales Engine domain models."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from .safety import SalesSafetyEnvelope

EPOCH_UTC = "1970-01-01T00:00:00Z"
ARTIFACT_TYPES = frozenset({
    "proposal", "quotation", "invoice", "contract", "recommendation",
    "sales_summary", "artifact_plan", "website review package",
})
ARTIFACT_STATUSES = frozenset({
    "draft", "validation_failed", "review_required", "changes_requested",
    "approved", "cancelled",
})
_SECRET = re.compile(
    r"(?:api[_-]?key|secret|password|passwd|authorization|bearer|private[_-]?key)\s*[:=]\s*\S+",
    re.IGNORECASE,
)


class SalesValidationError(ValueError):
    """Raised when sales input violates validation or safety policy."""


class Confidentiality(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def stable_artifact_id(request_id: str, artifact_type: str, version: str) -> str:
    return f"sales-artifact-{canonical_hash([request_id, artifact_type, version])[:24]}"


def _text(name: str, value: Any, *, required: bool = False) -> str:
    if not isinstance(value, str):
        raise SalesValidationError(f"{name} must be a string")
    normalized = value.strip()
    if required and not normalized:
        raise SalesValidationError(f"{name} is required")
    if _SECRET.search(normalized):
        raise SalesValidationError(f"{name} appears to contain secret information")
    return normalized


def _confidentiality(value: Confidentiality | str) -> Confidentiality:
    try:
        return value if isinstance(value, Confidentiality) else Confidentiality(value)
    except (TypeError, ValueError) as exc:
        raise SalesValidationError("invalid confidentiality") from exc


@dataclass(frozen=True)
class SalesRequest:
    business_name: str
    industry: str
    service_name: str
    target_customer: str
    customer_problem: str
    desired_outcome: str
    budget_range: str
    deadline: str
    requested_artifacts: tuple[str, ...]
    notes: str = ""
    request_id: str = ""
    created_at: str = EPOCH_UTC
    confidentiality: Confidentiality | str = Confidentiality.CONFIDENTIAL
    execute_allowed: bool = False
    production_actions_enabled: bool = False

    def __post_init__(self) -> None:
        fields = (
            ("business_name", self.business_name, True), ("industry", self.industry, False),
            ("service_name", self.service_name, True), ("target_customer", self.target_customer, True),
            ("customer_problem", self.customer_problem, False), ("desired_outcome", self.desired_outcome, False),
            ("budget_range", self.budget_range, False), ("deadline", self.deadline, False),
            ("notes", self.notes, False), ("created_at", self.created_at, True),
        )
        for name, value, required in fields:
            object.__setattr__(self, name, _text(name, value, required=required))
        if self.execute_allowed is True:
            raise SalesValidationError("execute_allowed=true is forbidden")
        if self.production_actions_enabled is True:
            raise SalesValidationError("production_actions_enabled=true is forbidden")
        if isinstance(self.requested_artifacts, (str, bytes)) or not isinstance(self.requested_artifacts, Sequence):
            raise SalesValidationError("requested_artifacts must be a sequence of strings")
        artifacts = tuple(_text("artifact_type", item, required=True) for item in self.requested_artifacts)
        if not artifacts:
            raise SalesValidationError("requested_artifacts is required")
        invalid = sorted(set(artifacts) - ARTIFACT_TYPES)
        if invalid:
            raise SalesValidationError(f"invalid artifact_type: {', '.join(invalid)}")
        object.__setattr__(self, "requested_artifacts", tuple(dict.fromkeys(artifacts)))
        object.__setattr__(self, "confidentiality", _confidentiality(self.confidentiality))
        if self.request_id:
            object.__setattr__(self, "request_id", _text("request_id", self.request_id, required=True))
        else:
            data = self.normalized(include_request_id=False)
            object.__setattr__(self, "request_id", f"sales-request-{canonical_hash(data)[:24]}")

    def normalized(self, *, include_request_id: bool = True) -> dict[str, Any]:
        data = {
            "business_name": self.business_name, "industry": self.industry,
            "service_name": self.service_name, "target_customer": self.target_customer,
            "customer_problem": self.customer_problem, "desired_outcome": self.desired_outcome,
            "budget_range": self.budget_range, "deadline": self.deadline,
            "requested_artifacts": list(self.requested_artifacts), "notes": self.notes,
            "created_at": self.created_at, "confidentiality": self.confidentiality.value,
        }
        if include_request_id:
            data["request_id"] = self.request_id
        return data


@dataclass(frozen=True)
class SalesArtifact:
    request_id: str
    artifact_type: str
    version: str
    title: str
    content: str
    confidentiality: Confidentiality | str = Confidentiality.CONFIDENTIAL
    status: str = "review_required"
    created_at: str = EPOCH_UTC
    safety: SalesSafetyEnvelope = field(default_factory=SalesSafetyEnvelope)
    artifact_id: str = field(init=False)
    content_hash: str = field(init=False)

    def __post_init__(self) -> None:
        for name in ("request_id", "artifact_type", "version", "title", "content", "created_at"):
            object.__setattr__(self, name, _text(name, getattr(self, name), required=True))
        if self.artifact_type not in ARTIFACT_TYPES:
            raise SalesValidationError("invalid artifact_type")
        if self.status not in ARTIFACT_STATUSES:
            raise SalesValidationError("invalid artifact status")
        object.__setattr__(self, "confidentiality", _confidentiality(self.confidentiality))
        object.__setattr__(self, "safety", SalesSafetyEnvelope.enforced(asdict(self.safety)))
        object.__setattr__(self, "artifact_id", stable_artifact_id(self.request_id, self.artifact_type, self.version))
        object.__setattr__(self, "content_hash", canonical_hash({
            "request_id": self.request_id, "artifact_type": self.artifact_type,
            "version": self.version, "title": self.title, "content": self.content,
            "confidentiality": self.confidentiality.value, "status": self.status,
            "created_at": self.created_at, "safety": self.safety.to_dict(),
        }))
