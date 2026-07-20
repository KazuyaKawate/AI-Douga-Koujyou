from __future__ import annotations

from dataclasses import dataclass


def _normalized(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip().lower() for value in values if str(value).strip()}))


@dataclass(frozen=True)
class RecommendationContext:
    """Immutable caller-supplied criteria for one recommendation request."""

    consumer_type: str
    top_n: int = 5
    tags: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    source_types: tuple[str, ...] = ()
    review_statuses: tuple[str, ...] = ("approved",)
    min_knowledge_score: float = 0.0
    citation_required: bool = True

    def __post_init__(self) -> None:
        consumer = self.consumer_type.strip().lower()
        if not consumer:
            raise ValueError("consumer_type is required.")
        if isinstance(self.top_n, bool) or self.top_n < 0:
            raise ValueError("top_n must be a non-negative integer.")
        if not 0 <= float(self.min_knowledge_score) <= 100:
            raise ValueError("min_knowledge_score must be between 0 and 100.")
        object.__setattr__(self, "consumer_type", consumer)
        object.__setattr__(self, "top_n", int(self.top_n))
        object.__setattr__(self, "tags", _normalized(self.tags))
        object.__setattr__(self, "categories", _normalized(self.categories))
        object.__setattr__(self, "source_types", _normalized(self.source_types))
        object.__setattr__(self, "review_statuses", _normalized(self.review_statuses))
        object.__setattr__(self, "min_knowledge_score", float(self.min_knowledge_score))
