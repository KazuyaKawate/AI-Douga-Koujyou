from __future__ import annotations

from pathlib import Path
from typing import Any

from src.content_engine.content_generator import ContentGenerator
from src.learning_engine.learning_models import now_iso, require_dry_run
from src.revenue_engine.revenue_planner import REVENUE_PLAN_PATH
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


CONTENT_PLAN_PATH = PROJECT_ROOT / "config" / "content_plan.json"


class ContentPipeline:
    """Generate local draft content plans from revenue_plan.json."""

    def __init__(
        self,
        *,
        revenue_plan_path: str | Path = REVENUE_PLAN_PATH,
        content_plan_path: str | Path = CONTENT_PLAN_PATH,
        generator: ContentGenerator | None = None,
    ) -> None:
        self.revenue_plan_path = Path(revenue_plan_path)
        self.content_plan_path = Path(content_plan_path)
        self.generator = generator or ContentGenerator()

    def load_revenue_plans(self) -> list[dict[str, Any]]:
        data = load_json(self.revenue_plan_path, default={})
        if not isinstance(data, dict):
            return []
        plans = data.get("plans", [])
        return list(plans) if isinstance(plans, list) else []

    def generate_content_plan(self, *, dry_run: bool = True) -> dict[str, Any]:
        require_dry_run(dry_run)
        revenue_plans = self.load_revenue_plans()
        contents = [self.generator.generate(plan, dry_run=True) for plan in revenue_plans]
        state = {
            "enabled": True,
            "source": "revenue_plan.json",
            "content": contents,
            "summary": {
                "revenue_plan_count": len(revenue_plans),
                "content_count": len(contents),
                "status": "draft",
                "required_review": True,
                "dry_run": True,
                "local_first": True,
                "external_api_enabled": False,
                "production_actions_enabled": False,
                "updated_at": now_iso(),
            },
            "dry_run": True,
            "local_first": True,
            "external_api_enabled": False,
            "production_actions_enabled": False,
            "updated_at": now_iso(),
        }
        save_json_atomic(self.content_plan_path, state)
        return state

    def load_content_plan(self) -> dict[str, Any]:
        data = load_json(self.content_plan_path, default={})
        return dict(data) if isinstance(data, dict) else {}
