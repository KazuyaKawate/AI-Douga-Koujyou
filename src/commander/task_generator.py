from __future__ import annotations

from typing import Any

from src.commander.task_models import CommanderLearningTask, commander_priority_weight
from src.learning_engine.business_pattern_models import normalize_aios_priority
from src.learning_engine.learning_models import clamp_confidence, require_dry_run


class CommanderTaskGenerator:
    """Convert Learning Engine ranking rows into pending Commander suggestions."""

    def generate_tasks(
        self,
        rankings: list[dict[str, Any]],
        *,
        patterns: list[dict[str, Any]] | None = None,
        limit: int = 10,
        dry_run: bool = True,
    ) -> list[dict[str, Any]]:
        require_dry_run(dry_run)
        pattern_map = {str(row.get("pattern_id", "")): row for row in patterns or []}
        tasks = [self.from_ranking(row, pattern_map=pattern_map) for row in rankings[: max(0, limit)]]
        return sorted(
            tasks,
            key=lambda item: (
                -commander_priority_weight(str(item.get("priority", "LOW"))),
                int(item.get("estimated_profit_days", 9999)),
                -int(item.get("confidence", 0)),
                str(item.get("task_id", "")),
            ),
        )

    def from_ranking(
        self,
        ranking: dict[str, Any],
        *,
        pattern_map: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        pattern = (pattern_map or {}).get(str(ranking.get("candidate_id", "")), {})
        report = self._report(pattern)
        candidate_name = str(ranking.get("candidate_name") or pattern.get("name") or "Untitled Candidate")
        priority = self._priority(ranking, pattern, report)
        source = {
            "engine": "learning_engine",
            "source_type": "candidate_ranking",
            "candidate_id": ranking.get("candidate_id", ""),
            "pattern_id": pattern.get("pattern_id", ranking.get("candidate_id", "")),
            "rank": ranking.get("rank", 0),
            "total_score": ranking.get("total_score", 0),
        }
        task = CommanderLearningTask(
            title=f"Review first-revenue task: {candidate_name}",
            description=str(ranking.get("recommended_action") or ranking.get("priority_reason") or ""),
            priority=priority,
            estimated_profit_days=self._int_value(report, pattern, "estimated_first_profit_days", 90),
            estimated_initial_cost=self._int_value(report, pattern, "estimated_initial_cost", 0),
            automation_ratio=self._int_value(report, pattern, "automation_ratio", 0),
            manual_ratio=self._int_value(report, pattern, "manual_work_ratio", 100),
            recommended_phase=str(
                ranking.get("recommended_current_phase")
                or report.get("recommended_current_phase")
                or pattern.get("recommended_current_phase")
                or "Phase6-5 Commander Review"
            ),
            source=source,
            confidence=self._confidence(ranking, pattern),
            risk=self._risks(pattern),
            business_category=str(pattern.get("category") or pattern.get("business_category") or "Other"),
            dry_run=True,
        ).to_dict()
        task["task_id"] = f"cmd-learn-{source['candidate_id'] or source['rank']}"
        return task

    @staticmethod
    def _priority(ranking: dict[str, Any], pattern: dict[str, Any], report: dict[str, Any]) -> str:
        explicit = report.get("aios_priority") or pattern.get("aios_priority")
        if explicit:
            return normalize_aios_priority(str(explicit))
        score = int(ranking.get("total_score", 0) or 0)
        if score >= 70:
            return "HIGH"
        if score >= 45:
            return "MEDIUM"
        return "LOW"

    @staticmethod
    def _confidence(ranking: dict[str, Any], pattern: dict[str, Any]) -> int:
        values = [ranking.get("total_score", 0), pattern.get("confidence", 0)]
        return clamp_confidence(max(int(value or 0) for value in values))

    @staticmethod
    def _report(pattern: dict[str, Any]) -> dict[str, Any]:
        report = pattern.get("reproducibility_report")
        return dict(report) if isinstance(report, dict) else {}

    @staticmethod
    def _risks(pattern: dict[str, Any]) -> list[str]:
        risks = pattern.get("risks", [])
        if not isinstance(risks, list):
            return ["情報不足"]
        return [str(risk).strip() for risk in risks if str(risk).strip()]

    @staticmethod
    def _int_value(report: dict[str, Any], pattern: dict[str, Any], key: str, default: int) -> int:
        value = report.get(key, pattern.get(key, default))
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
