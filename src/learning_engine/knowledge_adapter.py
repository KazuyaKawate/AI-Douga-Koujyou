from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable, Iterable, Mapping

from src.learning_engine.consumer_context import ConsumerContext
from src.learning_engine.consumer_filters import KnowledgeFilter
from src.learning_engine.consumer_metrics import KnowledgeMetrics
from src.learning_engine.knowledge_models import KnowledgeDocument


DocumentProvider = Callable[[], Iterable[KnowledgeDocument | Mapping[str, Any]]]


class KnowledgeAdapter:
    """Read-only adapter over an explicitly injected, caller-controlled provider."""

    def __init__(self, provider: DocumentProvider, metrics: KnowledgeMetrics | None = None) -> None:
        if not callable(provider):
            raise TypeError("A callable document provider must be injected.")
        self._provider = provider
        self._metrics = metrics or KnowledgeMetrics()

    @property
    def metrics(self) -> KnowledgeMetrics:
        return self._metrics

    def read(
        self, context: ConsumerContext, selection: KnowledgeFilter | None = None,
    ) -> tuple[dict[str, Any], ...]:
        filter_ = selection or KnowledgeFilter()
        documents = tuple(self._normalize(item) for item in self._provider())
        accepted: list[dict[str, Any]] = []
        rejected = 0
        for document in documents:
            if not context.policy.allows(document):
                rejected += 1
                continue
            if filter_.matches(document):
                accepted.append(deepcopy(document))
        self._metrics.record(considered=len(documents), returned=len(accepted), rejected_by_policy=rejected)
        return tuple(accepted)

    @staticmethod
    def _normalize(item: KnowledgeDocument | Mapping[str, Any]) -> dict[str, Any]:
        if isinstance(item, KnowledgeDocument):
            return item.to_dict()
        if isinstance(item, Mapping):
            return deepcopy(dict(item))
        raise TypeError("Knowledge provider items must be KnowledgeDocument or mapping values.")

