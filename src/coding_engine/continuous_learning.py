from __future__ import annotations

from typing import Any

from src.core.development_constitution import prioritize_improvements


class CodingContinuousLearning:
    def improvement_candidates(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        candidates = []
        for run in history[:30]:
            tests_ok = bool(run.get("tests", {}).get("ok"))
            review_ok = run.get("review", {}).get("status") == "approved"
            candidates.append(
                {
                    "instruction": "Improve Coding Engine automation from previous run",
                    "source_run_id": run.get("run_id", ""),
                    "estimated_revenue": 12000 if tests_ok and review_ok else 5000,
                    "estimated_effort": 20 if tests_ok else 40,
                    "risk": "low" if review_ok else "medium",
                    "profitability": 35,
                }
            )
        return prioritize_improvements(candidates)[:10]
