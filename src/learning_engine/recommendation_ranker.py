from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from src.learning_engine.recommendation_context import RecommendationContext
from src.learning_engine.recommendation_policy import RecommendationPolicy


def _text(value: Any) -> str:
    return str(value).strip().lower()


def knowledge_score(document: Mapping[str, Any]) -> float:
    score = document.get("score", {})
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        return max(0.0, min(100.0, float(score)))
    if not isinstance(score, Mapping):
        return 0.0
    if isinstance(score.get("overall"), (int, float)) and not isinstance(score["overall"], bool):
        return max(0.0, min(100.0, float(score["overall"])))
    values = [float(value) for key, value in score.items()
              if key != "score_id" and isinstance(value, (int, float)) and not isinstance(value, bool)]
    return max(0.0, min(100.0, sum(values) / len(values))) if values else 0.0


@dataclass(frozen=True)
class RankedKnowledge:
    document: Mapping[str, Any]
    rank_score: float
    components: Mapping[str, float]


class RecommendationRanker:
    """Pure deterministic scorer; input order never resolves ties."""

    def __init__(self, policy: RecommendationPolicy) -> None:
        self._policy = policy

    def rank(self, documents: Sequence[Mapping[str, Any]], context: RecommendationContext) -> tuple[RankedKnowledge, ...]:
        profile = self._policy.profile(context.consumer_type)
        ranked = [self._score(document, context, profile) for document in documents]
        ranked.sort(key=lambda item: (-item.rank_score, self._identity(item.document)))
        return tuple(ranked)

    def _score(self, document: Mapping[str, Any], context: RecommendationContext,
               profile: Mapping[str, tuple[str, ...]]) -> RankedKnowledge:
        tags = {_text(item.get("name", "") if isinstance(item, Mapping) else item) for item in document.get("tags", [])}
        desired_tags = set(context.tags) or set(profile["tags"])
        category = _text(document.get("category", ""))
        desired_categories = set(context.categories) or set(profile["categories"])
        source = document.get("source", {})
        source_type = _text(source.get("source_type", "") if isinstance(source, Mapping) else source)
        metadata = document.get("metadata", {})
        review = _text(document.get("review_status", metadata.get("review_status", "") if isinstance(metadata, Mapping) else ""))
        components = {
            "tag": len(tags & desired_tags) / max(1, len(desired_tags)),
            "category": float(category in desired_categories),
            "citation": float(bool(document.get("citations", ()))),
            "knowledge_score": knowledge_score(document) / 100.0,
            "review": float(review == "approved"),
            "source_type": float(not context.source_types or source_type in context.source_types),
        }
        total = sum(components[name] * weight for name, weight in self._policy.weights.items())
        return RankedKnowledge(document=document, rank_score=round(total, 6), components=components)

    @staticmethod
    def _identity(document: Mapping[str, Any]) -> str:
        document_id = _text(document.get("document_id", ""))
        if document_id:
            return document_id
        canonical = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
