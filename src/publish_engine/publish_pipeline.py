from __future__ import annotations

from pathlib import Path
from typing import Any

from src.content_engine.content_pipeline import CONTENT_PLAN_PATH
from src.learning_engine.learning_models import now_iso, require_dry_run
from src.publish_engine.publish_planner import PublishPlanner
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


PUBLISH_PLAN_PATH = PROJECT_ROOT / "config" / "publish_plan.json"


class PublishPipeline:
    """Generate local draft publish_plan.json from content_plan.json."""

    def __init__(
        self,
        *,
        content_plan_path: str | Path = CONTENT_PLAN_PATH,
        publish_plan_path: str | Path = PUBLISH_PLAN_PATH,
        planner: PublishPlanner | None = None,
    ) -> None:
        self.content_plan_path = Path(content_plan_path)
        self.publish_plan_path = Path(publish_plan_path)
        self.planner = planner or PublishPlanner()

    def load_content(self) -> list[dict[str, Any]]:
        data = load_json(self.content_plan_path, default={})
        if not isinstance(data, dict):
            return []
        content = data.get("content", [])
        return list(content) if isinstance(content, list) else []

    def generate_publish_plan(self, *, dry_run: bool = True) -> dict[str, Any]:
        require_dry_run(dry_run)
        content_rows = self.load_content()
        publish_rows = self.planner.build_publish_plan(content_rows, dry_run=True)
        state = {
            "enabled": True,
            "source": "content_plan.json",
            "publish_queue": publish_rows,
            "summary": {
                "content_count": len(content_rows),
                "publish_count": len(publish_rows),
                "status": "draft",
                "approval_status": "pending_review",
                "publish_status": "draft",
                "review_required": True,
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
        save_json_atomic(self.publish_plan_path, state)
        return state

    def load_publish_plan(self) -> dict[str, Any]:
        data = load_json(self.publish_plan_path, default={})
        return dict(data) if isinstance(data, dict) else {}
