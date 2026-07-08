from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.core.development_constitution import development_review, prioritize_improvements


class CodingPlanner:
    def plan(self, issue: str, repository: dict[str, Any]) -> dict[str, Any]:
        target_files = repository.get("selected_files", [])
        candidate = {
            "instruction": issue,
            "target_files": target_files,
            "estimated_revenue": 18000 if self._revenue_aligned(issue) else 5000,
            "estimated_effort": max(15, min(90, len(target_files) * 8 or 20)),
            "risk": "medium" if len(target_files) > 6 else "low",
            "profitability": 40 if self._revenue_aligned(issue) else 20,
        }
        ranked = prioritize_improvements([candidate])[0]
        return {
            "plan_id": f"cp-{uuid4().hex[:10]}",
            "issue": issue,
            "target_files": target_files,
            "steps": [
                "Repository解析",
                "Development Constitution Review",
                "最小差分生成",
                "Review",
                "pytest",
                "compileall",
                "Commit候補生成",
                "Knowledge保存",
            ],
            "constitution_review": development_review(ranked, context={"knowledge_duplication": "checked_by_coding_engine"}),
            "priority": ranked,
        }

    @staticmethod
    def _revenue_aligned(text: str) -> bool:
        lowered = text.lower()
        return any(token in lowered for token in ("revenue", "roi", "収益", "初収益", "business", "note", "threads"))
