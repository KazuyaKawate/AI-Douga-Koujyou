from __future__ import annotations

from typing import Any

from src.learning_engine.knowledge_models import KnowledgeScore


class KnowledgeScorer:
    def score(self, *, relevance: int = 0, reliability: int = 0,
              reproducibility: int = 0, revenue_potential: int = 0) -> dict[str, Any]:
        return KnowledgeScore(relevance=relevance, reliability=reliability,
                              reproducibility=reproducibility,
                              revenue_potential=revenue_potential).to_dict()
