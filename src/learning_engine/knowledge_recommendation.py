from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Iterable, Mapping

from src.learning_engine.knowledge_models import KnowledgeDocument
from src.learning_engine.recommendation_context import RecommendationContext
from src.learning_engine.recommendation_policy import RecommendationPolicy
from src.learning_engine.recommendation_ranker import RecommendationRanker, RankedKnowledge, knowledge_score


DocumentProvider = Callable[[], Iterable[KnowledgeDocument | Mapping[str, Any]]]


class KnowledgeRecommendation:
    """Read-only recommendation over an explicitly injected document provider."""

    def __init__(self, provider: DocumentProvider, policy: RecommendationPolicy | None = None,
                 ranker: RecommendationRanker | None = None) -> None:
        if not callable(provider):
            raise TypeError("A callable document provider must be injected.")
        self._provider = provider
        self._policy = policy or RecommendationPolicy()
        self._ranker = ranker or RecommendationRanker(self._policy)

    def recommend(self, context: RecommendationContext) -> tuple[RankedKnowledge, ...]:
        self._policy.profile(context.consumer_type)
        if context.top_n == 0:
            return ()
        documents = (self._normalize(item) for item in self._provider())
        eligible = [document for document in documents if self._matches(document, context)]
        ranked = self._ranker.rank(eligible, context)[:context.top_n]
        return tuple(RankedKnowledge(deepcopy(item.document), item.rank_score, dict(item.components)) for item in ranked)

    def _matches(self, document: Mapping[str, Any], context: RecommendationContext) -> bool:
        if not self._policy.allows(document):
            return False
        tags = {_text(item.get("name", "") if isinstance(item, Mapping) else item) for item in document.get("tags", [])}
        if context.tags and not set(context.tags).intersection(tags):
            return False
        if context.categories and _text(document.get("category", "")) not in context.categories:
            return False
        source = document.get("source", {})
        source_type = _text(source.get("source_type", "") if isinstance(source, Mapping) else source)
        if context.source_types and source_type not in context.source_types:
            return False
        if context.citation_required and not document.get("citations", ()):
            return False
        if knowledge_score(document) < context.min_knowledge_score:
            return False
        metadata = document.get("metadata", {})
        review = _text(document.get("review_status", metadata.get("review_status", "") if isinstance(metadata, Mapping) else ""))
        return not context.review_statuses or review in context.review_statuses

    @staticmethod
    def _normalize(item: KnowledgeDocument | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(item, KnowledgeDocument):
            return item.to_dict()
        if isinstance(item, Mapping):
            return deepcopy(dict(item))
        raise TypeError("Knowledge provider items must be KnowledgeDocument or mapping values.")


def _text(value: Any) -> str:
    return str(value).strip().lower()
