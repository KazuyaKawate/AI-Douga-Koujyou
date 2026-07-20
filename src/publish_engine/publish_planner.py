from __future__ import annotations

from datetime import datetime
from typing import Any

from src.learning_engine.learning_models import require_dry_run
from src.publish_engine.publish_models import PublishPlan, scheduled_time_for_rank, trim_text


SUPPORTED_PLATFORMS = ("note", "Threads", "Website")
PRIORITY_WEIGHT = {"HIGH": 95, "MEDIUM": 65, "LOW": 35}


class PublishPlanner:
    """Build local draft publish rows from content_plan entries."""

    def build_publish_plan(
        self,
        content_rows: list[dict[str, Any]],
        *,
        dry_run: bool = True,
    ) -> list[dict[str, Any]]:
        require_dry_run(dry_run)
        ordered_content = sorted(content_rows, key=self._content_sort_key)
        plans: list[dict[str, Any]] = []
        base_time = datetime.now().replace(microsecond=0)
        for content in ordered_content:
            for platform in SUPPORTED_PLATFORMS:
                rank = len(plans) + 1
                plans.append(self.build_platform_plan(content, platform, rank=rank, base_time=base_time))
        return plans

    def build_platform_plan(
        self,
        content: dict[str, Any],
        platform: str,
        *,
        rank: int,
        base_time: datetime,
    ) -> dict[str, Any]:
        source = dict(content.get("source", {}) or {})
        title = self.platform_title(content, platform)
        body = self.platform_body(content, platform)
        priority = self.publish_priority(content, platform)
        return PublishPlan(
            content_id=str(content.get("content_id", "")),
            platform=platform,
            title=title,
            body=body,
            hashtags=list(content.get("hashtags", []) or []),
            seo_title=trim_text(title, 60),
            seo_description=trim_text(str(content.get("summary", "")) or body, 120),
            publish_priority=priority,
            scheduled_time=scheduled_time_for_rank(rank, base_time),
            source={
                "engine": "content_engine",
                "source_type": "content_plan",
                "content_id": content.get("content_id", ""),
                "plan_id": source.get("plan_id", ""),
                "task_id": source.get("task_id", ""),
                "priority": source.get("priority", ""),
                "confidence": source.get("confidence", content.get("confidence", 50)),
                "estimated_first_profit_days": source.get("estimated_first_profit_days", content.get("estimated_first_profit_days", 9999)),
            },
            dry_run=True,
        ).to_dict()

    def platform_title(self, content: dict[str, Any], platform: str) -> str:
        title = str(content.get("title", "AIOS content draft"))
        if platform == "Threads":
            return trim_text(f"Threads: {title}", 80)
        if platform == "Website":
            return trim_text(f"LP: {title}", 80)
        return trim_text(title, 80)

    def platform_body(self, content: dict[str, Any], platform: str) -> str:
        cta = str(content.get("cta", "レビュー後にDryRunで確認する"))
        if platform == "Threads":
            outline = list(content.get("threads_outline", []) or [])[:20]
            return "\n".join([str(item) for item in outline] + [f"CTA: {cta}"]).strip()
        if platform == "Website":
            outline = list(content.get("website_outline", []) or [])
            return "\n".join([str(item) for item in outline] + [f"CTA: {cta}"]).strip()
        outline = list(content.get("note_outline", []) or [])
        return "\n\n".join([str(item) for item in outline] + [f"CTA: {cta}"]).strip()

    def publish_priority(self, content: dict[str, Any], platform: str) -> int:
        source = dict(content.get("source", {}) or {})
        priority = str(source.get("priority", content.get("priority", "MEDIUM"))).upper()
        score = PRIORITY_WEIGHT.get(priority, 50)
        category = str(content.get("category", ""))
        if platform == "note" and category == "note":
            score += 5
        if platform == "Threads" and category == "Threads":
            score += 5
        if platform == "Website" and category == "Website":
            score += 5
        return max(0, min(100, score))

    @staticmethod
    def _content_sort_key(content: dict[str, Any]) -> tuple[int, int, int]:
        source = dict(content.get("source", {}) or {})
        priority = str(source.get("priority", content.get("priority", "MEDIUM"))).upper()
        days = int(source.get("estimated_first_profit_days", content.get("estimated_first_profit_days", 9999)) or 9999)
        confidence = int(source.get("confidence", content.get("confidence", 0)) or 0)
        return (-PRIORITY_WEIGHT.get(priority, 50), days, -confidence)
