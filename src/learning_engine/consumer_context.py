from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from src.learning_engine.consumer_policy import ConsumerPolicy


@dataclass(frozen=True)
class ConsumerContext:
    """Immutable dependency-injection context; it performs no retrieval itself."""

    consumer_id: str
    policy: ConsumerPolicy = field(default_factory=ConsumerPolicy)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        consumer_id = self.consumer_id.strip().lower()
        if not consumer_id:
            raise ValueError("consumer_id is required.")
        object.__setattr__(self, "consumer_id", consumer_id)
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

