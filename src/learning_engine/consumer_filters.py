from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


def _normalized(value: Any) -> str:
    return str(value).strip().lower()


@dataclass(frozen=True)
class KnowledgeFilter:
    tags: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    citations: tuple[str, ...] = ()
    min_score: float | None = None
    review_statuses: tuple[str, ...] = ()
    safety_flags: Mapping[str, bool] | None = None

    @classmethod
    def create(
        cls,
        *,
        tags: Sequence[str] = (),
        categories: Sequence[str] = (),
        sources: Sequence[str] = (),
        citations: Sequence[str] = (),
        min_score: float | None = None,
        review_statuses: Sequence[str] = (),
        safety_flags: Mapping[str, bool] | None = None,
    ) -> "KnowledgeFilter":
        return cls(
            tags=tuple(map(_normalized, tags)), categories=tuple(map(_normalized, categories)),
            sources=tuple(map(_normalized, sources)), citations=tuple(map(_normalized, citations)),
            min_score=min_score, review_statuses=tuple(map(_normalized, review_statuses)),
            safety_flags=dict(safety_flags) if safety_flags is not None else None,
        )

    def matches(self, document: Mapping[str, Any]) -> bool:
        tags = {_normalized(item.get("name", "") if isinstance(item, Mapping) else item)
                for item in document.get("tags", [])}
        if self.tags and not set(self.tags).issubset(tags):
            return False
        if self.categories and _normalized(document.get("category", "")) not in self.categories:
            return False

        source = document.get("source", {})
        source_values = {_normalized(source)}
        if isinstance(source, Mapping):
            source_values = {_normalized(source.get(key, "")) for key in ("source_id", "name", "source_type", "uri")}
        if self.sources and not set(self.sources).intersection(source_values):
            return False

        citation_values: set[str] = set()
        for item in document.get("citations", []):
            if isinstance(item, Mapping):
                citation_values.update(_normalized(item.get(key, "")) for key in ("citation_id", "source_id", "locator", "label"))
            else:
                citation_values.add(_normalized(item))
        if self.citations and not set(self.citations).intersection(citation_values):
            return False

        if self.min_score is not None and self._score(document.get("score", {})) < self.min_score:
            return False
        metadata = document.get("metadata", {})
        review_status = document.get("review_status", metadata.get("review_status", "") if isinstance(metadata, Mapping) else "")
        if self.review_statuses and _normalized(review_status) not in self.review_statuses:
            return False
        if self.safety_flags:
            nested = document.get("safety_flags", {})
            for key, expected in self.safety_flags.items():
                actual = document.get(key, nested.get(key) if isinstance(nested, Mapping) else None)
                if actual is not expected:
                    return False
        return True

    @staticmethod
    def _score(score: Any) -> float:
        if isinstance(score, (int, float)):
            return float(score)
        if not isinstance(score, Mapping):
            return 0.0
        if isinstance(score.get("overall"), (int, float)):
            return float(score["overall"])
        values = [float(value) for key, value in score.items()
                  if key != "score_id" and isinstance(value, (int, float)) and not isinstance(value, bool)]
        return sum(values) / len(values) if values else 0.0

