"""Fail-closed safety values for every Sales Engine result."""

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class SalesSafetyEnvelope:
    execute_allowed: bool = False
    approval_required: bool = True
    review_required: bool = True
    dry_run: bool = True
    production_actions_enabled: bool = False
    external_request_sent: bool = False

    @classmethod
    def enforced(cls, _requested: Mapping[str, Any] | None = None) -> "SalesSafetyEnvelope":
        """Ignore caller flags and always return the safe envelope."""
        return cls()

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)
