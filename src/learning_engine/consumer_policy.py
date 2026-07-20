from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ConsumerPolicy:
    """Non-executing policy attached to every knowledge consumer context."""

    execute_allowed: bool = False
    approval_required: bool = True
    review_required: bool = True
    dry_run: bool = True
    production_actions_enabled: bool = False
    external_request_sent: bool = False

    def __post_init__(self) -> None:
        if (
            self.execute_allowed is not False
            or self.approval_required is not True
            or self.review_required is not True
            or self.dry_run is not True
            or self.production_actions_enabled is not False
            or self.external_request_sent is not False
        ):
            raise ValueError("Phase 119 consumer safety policy cannot be relaxed.")

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)

    def allows(self, document: Mapping[str, Any]) -> bool:
        """Return True only when a document retains all mandatory safety flags."""
        flags = document.get("safety_flags", {})
        if not isinstance(flags, Mapping):
            flags = {}
        value = lambda name: document.get(name, flags.get(name))
        return (
            value("execute_allowed") is False
            and value("approval_required") is True
            and value("review_required") is True
            and value("dry_run") is True
            and value("production_actions_enabled") is False
            and value("external_request_sent") is False
        )
