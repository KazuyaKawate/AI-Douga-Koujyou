from __future__ import annotations

from pathlib import Path
from typing import Any

from src.learning_engine.candidate_ranking_engine import CandidateRankingEngine
from src.learning_engine.knowledge_store import LEARNING_ENGINE_PATH, KnowledgeStore
from src.learning_engine.learning_models import now_iso, require_dry_run


class CandidateRankingPipeline:
    """Persist local-only ranking results for Business Pattern candidates."""

    def __init__(
        self,
        *,
        store: KnowledgeStore | None = None,
        path: str | Path = LEARNING_ENGINE_PATH,
        engine: CandidateRankingEngine | None = None,
    ) -> None:
        self.store = store or KnowledgeStore(path=path)
        self.engine = engine or CandidateRankingEngine()

    def rank_business_patterns(self, *, dry_run: bool = True) -> list[dict[str, Any]]:
        require_dry_run(dry_run)
        state = self.store.load_state()
        candidates = state.get("business_patterns", [])
        if not isinstance(candidates, list):
            candidates = []
        rankings = self.engine.rank_candidates(candidates, dry_run=True)
        state["candidate_rankings"] = rankings
        state["candidate_ranking_summary"] = {
            "candidate_count": len(candidates),
            "ranking_count": len(rankings),
            "top_candidate_id": rankings[0]["candidate_id"] if rankings else "",
            "dry_run": True,
            "local_first": True,
            "external_api_enabled": False,
            "production_actions_enabled": False,
            "updated_at": now_iso(),
        }
        self.store.save_state(state)
        return rankings

    def rank_candidates(
        self,
        candidates: list[dict[str, Any]],
        *,
        dry_run: bool = True,
    ) -> list[dict[str, Any]]:
        require_dry_run(dry_run)
        return self.engine.rank_candidates(candidates, dry_run=True)

    def load_rankings(self) -> list[dict[str, Any]]:
        state = self.store.load_state()
        rankings = state.get("candidate_rankings", [])
        return list(rankings) if isinstance(rankings, list) else []
