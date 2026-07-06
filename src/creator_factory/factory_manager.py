from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.utils.json_store import load_json, save_json_atomic

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = ROOT / "data"

PROJECT_STATUSES = [
    "planning",
    "queued",
    "generating",
    "reviewing",
    "approved",
    "exported",
    "archived",
]

PIPELINES = {
    "note": {"label": "Note Pipeline", "content_type": "note_article", "estimated_runtime_minutes": 25, "estimated_token_usage": 1800},
    "seo_blog": {"label": "SEO Blog Pipeline", "content_type": "seo_article", "estimated_runtime_minutes": 35, "estimated_token_usage": 2600},
    "sns": {"label": "SNS Pipeline", "content_type": "sns_thread", "estimated_runtime_minutes": 15, "estimated_token_usage": 900},
    "affiliate": {"label": "Affiliate Pipeline", "content_type": "affiliate_article", "estimated_runtime_minutes": 30, "estimated_token_usage": 2200},
    "business_report": {"label": "Business Report Pipeline", "content_type": "business_report", "estimated_runtime_minutes": 20, "estimated_token_usage": 1600},
}

TEMPLATE_TYPES = {
    "note_article": "# Note Article\n\nPurpose:\nAudience:\nOutline:\nKey points:\nCall to action:",
    "seo_article": "# SEO Article\n\nKeyword:\nSearch intent:\nOutline:\nInternal links:\nMeta description:",
    "sns_thread": "# SNS Thread\n\nHook:\nPosts:\nHashtags:\nCall to action:",
    "affiliate_article": "# Affiliate Article\n\nProduct:\nDisclosure:\nBenefits:\nComparison:\nCall to action:",
    "business_report": "# Business Report\n\nPeriod:\nKPIs:\nInsights:\nRisks:\nNext actions:",
}

KNOWLEDGE_TYPES = [
    "reusable_prompt",
    "writing_style",
    "tone_preset",
    "business_knowledge",
    "prompt_snippet",
]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _json_path(directory: Path, item_id: str) -> Path:
    return directory / f"{item_id}.json"


class CreatorFactoryManager:
    """Local-only creator production manager."""

    def __init__(self, data_root: str | Path = DEFAULT_DATA_ROOT) -> None:
        self.data_root = Path(data_root)
        self.projects_dir = self.data_root / "projects"
        self.templates_dir = self.data_root / "templates"
        self.knowledge_dir = self.data_root / "knowledge"
        self.production_dir = self.data_root / "production"
        self.history_dir = self.production_dir / "history"
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        for directory in (self.projects_dir, self.templates_dir, self.knowledge_dir, self.production_dir, self.history_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def create_project(
        self,
        title: str,
        *,
        description: str = "",
        category: str = "creator",
        target_platform: str = "note",
        priority: str = "normal",
        status: str = "planning",
    ) -> dict[str, Any]:
        if status not in PROJECT_STATUSES:
            status = "planning"
        project = {
            "id": _new_id("proj"),
            "title": title,
            "description": description,
            "category": category,
            "target_platform": target_platform,
            "priority": priority,
            "status": status,
            "created_at": _now(),
            "updated_at": _now(),
        }
        save_json_atomic(_json_path(self.projects_dir, project["id"]), project)
        return project

    def list_projects(self, status: str | None = None) -> list[dict[str, Any]]:
        projects = self._read_all(self.projects_dir)
        if status:
            projects = [project for project in projects if project.get("status") == status]
        return sorted(projects, key=lambda row: row.get("updated_at", ""), reverse=True)

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        data = load_json(_json_path(self.projects_dir, project_id), default=None)
        return data if isinstance(data, dict) else None

    def update_project_status(self, project_id: str, status: str) -> dict[str, Any] | None:
        if status not in PROJECT_STATUSES:
            return None
        project = self.get_project(project_id)
        if project is None:
            return None
        project["status"] = status
        project["updated_at"] = _now()
        save_json_atomic(_json_path(self.projects_dir, project_id), project)
        return project

    def create_template(self, name: str, template_type: str, body: str | None = None, *, description: str = "") -> dict[str, Any]:
        if template_type not in TEMPLATE_TYPES:
            template_type = "note_article"
        template = {
            "id": _new_id("tpl"),
            "name": name,
            "description": description,
            "template_type": template_type,
            "body": body if body is not None else TEMPLATE_TYPES[template_type],
            "version": 1,
            "history": [],
            "created_at": _now(),
            "updated_at": _now(),
        }
        save_json_atomic(_json_path(self.templates_dir, template["id"]), template)
        return template

    def list_templates(self, template_type: str | None = None) -> list[dict[str, Any]]:
        templates = self._read_all(self.templates_dir)
        if template_type:
            templates = [tpl for tpl in templates if tpl.get("template_type") == template_type]
        return sorted(templates, key=lambda row: row.get("updated_at", ""), reverse=True)

    def update_template(
        self,
        template_id: str,
        *,
        name: str | None = None,
        body: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any] | None:
        template = self._load_template(template_id)
        if template is None:
            return None
        template.setdefault("history", []).insert(0, {
            "version": template.get("version", 1),
            "name": template.get("name", ""),
            "description": template.get("description", ""),
            "body": template.get("body", ""),
            "saved_at": _now(),
        })
        if name is not None:
            template["name"] = name
        if body is not None:
            template["body"] = body
        if description is not None:
            template["description"] = description
        template["version"] = int(template.get("version", 1)) + 1
        template["updated_at"] = _now()
        save_json_atomic(_json_path(self.templates_dir, template_id), template)
        return template

    def duplicate_template(self, template_id: str) -> dict[str, Any] | None:
        template = self._load_template(template_id)
        if template is None:
            return None
        return self.create_template(
            f"{template.get('name', 'Template')} Copy",
            template.get("template_type", "note_article"),
            template.get("body", ""),
            description=template.get("description", ""),
        )

    def add_knowledge_item(self, title: str, knowledge_type: str, content: str, *, tags: list[str] | None = None) -> dict[str, Any]:
        if knowledge_type not in KNOWLEDGE_TYPES:
            knowledge_type = "business_knowledge"
        item = {
            "id": _new_id("kb"),
            "title": title,
            "knowledge_type": knowledge_type,
            "content": content,
            "tags": tags or [],
            "created_at": _now(),
            "updated_at": _now(),
        }
        save_json_atomic(_json_path(self.knowledge_dir, item["id"]), item)
        return item

    def list_knowledge(self, knowledge_type: str | None = None) -> list[dict[str, Any]]:
        items = self._read_all(self.knowledge_dir)
        if knowledge_type:
            items = [item for item in items if item.get("knowledge_type") == knowledge_type]
        return sorted(items, key=lambda row: row.get("updated_at", ""), reverse=True)

    def enqueue_production(
        self,
        pipeline: str,
        title: str,
        *,
        project_id: str = "",
        template_id: str = "",
        priority: str = "normal",
        due_date: str | None = None,
    ) -> dict[str, Any]:
        if pipeline not in PIPELINES:
            raise ValueError(f"Unsupported pipeline: {pipeline}")
        spec = PIPELINES[pipeline]
        item = {
            "id": _new_id("prod"),
            "pipeline": pipeline,
            "pipeline_label": spec["label"],
            "project_id": project_id,
            "template_id": template_id,
            "title": title,
            "priority": priority,
            "status": "queued",
            "approval_status": "not_submitted",
            "export_status": "not_exported",
            "estimated_runtime_minutes": spec["estimated_runtime_minutes"],
            "estimated_token_usage": spec["estimated_token_usage"],
            "due_date": due_date or date.today().isoformat(),
            "output_ref": "",
            "created_at": _now(),
            "updated_at": _now(),
        }
        save_json_atomic(_json_path(self.production_dir, item["id"]), item)
        if project_id:
            self.update_project_status(project_id, "queued")
        return item

    def list_production(self, status: str | None = None) -> list[dict[str, Any]]:
        items = [row for row in self._read_all(self.production_dir) if row.get("id") and row.get("pipeline")]
        if status:
            items = [item for item in items if item.get("status") == status]
        return sorted(items, key=lambda row: row.get("updated_at", ""), reverse=True)

    def update_production_status(
        self,
        production_id: str,
        status: str,
        *,
        approval_status: str | None = None,
        export_status: str | None = None,
        output_ref: str | None = None,
    ) -> dict[str, Any] | None:
        item = self._load_production(production_id)
        if item is None:
            return None
        item["status"] = status
        if approval_status is not None:
            item["approval_status"] = approval_status
        if export_status is not None:
            item["export_status"] = export_status
        if output_ref is not None:
            item["output_ref"] = output_ref
        item["updated_at"] = _now()
        save_json_atomic(_json_path(self.production_dir, production_id), item)
        if status in ("completed", "failed", "exported"):
            save_json_atomic(_json_path(self.history_dir, production_id), item)
        return item

    def pipeline_summary(self) -> dict[str, dict[str, Any]]:
        items = self.list_production()
        summary: dict[str, dict[str, Any]] = {}
        for pipeline, spec in PIPELINES.items():
            rows = [item for item in items if item.get("pipeline") == pipeline]
            summary[pipeline] = {
                "label": spec["label"],
                "queue": sum(1 for item in rows if item.get("status") == "queued"),
                "status": _pipeline_status(rows),
                "output_count": sum(1 for item in rows if item.get("status") in ("completed", "exported")),
                "estimated_runtime": sum(int(item.get("estimated_runtime_minutes", 0)) for item in rows if item.get("status") == "queued"),
                "estimated_token_usage": sum(int(item.get("estimated_token_usage", 0)) for item in rows if item.get("status") == "queued"),
                "approval_status": _dominant(rows, "approval_status", "not_submitted"),
                "export_status": _dominant(rows, "export_status", "not_exported"),
            }
        return summary

    def content_calendar(self, days: int = 30) -> list[dict[str, Any]]:
        cutoff = date.today() + timedelta(days=days)
        calendar = []
        for item in self.list_production():
            try:
                due_date = date.fromisoformat(item.get("due_date", ""))
            except ValueError:
                continue
            if due_date <= cutoff:
                calendar.append({
                    "date": item.get("due_date", ""),
                    "title": item.get("title", ""),
                    "pipeline": item.get("pipeline_label", item.get("pipeline", "")),
                    "status": item.get("status", ""),
                    "project_id": item.get("project_id", ""),
                })
        return sorted(calendar, key=lambda row: row["date"])

    def revenue_estimator(self) -> dict[str, Any]:
        items = self.list_production()
        exported = [item for item in items if item.get("export_status") == "exported" or item.get("status") == "exported"]
        approved = [item for item in items if item.get("approval_status") == "approved"]
        rejected = [item for item in items if item.get("approval_status") == "rejected"]
        completed = [item for item in items if item.get("status") in ("completed", "exported")]
        total_reviewed = len(approved) + len(rejected)
        avg_time = int(sum(int(item.get("estimated_runtime_minutes", 0)) for item in completed) / len(completed)) if completed else 0
        monthly_volume = len([item for item in items if str(item.get("created_at", "")).startswith(date.today().isoformat()[:7])])
        return {
            "articles_produced": len(completed),
            "exports_completed": len(exported),
            "approval_rate": round(len(approved) / total_reviewed * 100, 1) if total_reviewed else 0.0,
            "rejection_rate": round(len(rejected) / total_reviewed * 100, 1) if total_reviewed else 0.0,
            "average_production_time": avg_time,
            "estimated_monthly_production_volume": monthly_volume,
            "income_prediction_enabled": False,
        }

    def dashboard_metrics(self) -> dict[str, Any]:
        projects = self.list_projects()
        production = self.list_production()
        today = date.today().isoformat()
        month = today[:7]
        queued = [item for item in production if item.get("status") == "queued"]
        reviewing = [item for item in production if item.get("approval_status") in ("pending_review", "revision_requested")]
        export_queue = [item for item in production if item.get("approval_status") == "approved" and item.get("export_status") != "exported"]
        completed = [item for item in production if item.get("status") in ("completed", "exported")]
        avg_runtime = int(sum(int(item.get("estimated_runtime_minutes", 0)) for item in completed) / len(completed)) if completed else 0
        return {
            "active_projects": sum(1 for project in projects if project.get("status") not in ("archived",)),
            "production_queue": len(queued),
            "review_queue": len(reviewing),
            "export_queue": len(export_queue),
            "today_output": sum(1 for item in completed if str(item.get("updated_at", "")).startswith(today)),
            "weekly_output": _count_since(completed, date.today() - timedelta(days=7)),
            "monthly_output": sum(1 for item in completed if str(item.get("updated_at", "")).startswith(month)),
            "average_runtime": avg_runtime,
            "total_projects": len(projects),
            "total_templates": len(self.list_templates()),
            "knowledge_items": len(self.list_knowledge()),
            "local_first": True,
            "external_apis_enabled": False,
        }

    def _load_template(self, template_id: str) -> dict[str, Any] | None:
        data = load_json(_json_path(self.templates_dir, template_id), default=None)
        return data if isinstance(data, dict) else None

    def _load_production(self, production_id: str) -> dict[str, Any] | None:
        data = load_json(_json_path(self.production_dir, production_id), default=None)
        return data if isinstance(data, dict) else None

    @staticmethod
    def _read_all(directory: Path) -> list[dict[str, Any]]:
        rows = []
        if not directory.exists():
            return rows
        for path in directory.glob("*.json"):
            data = load_json(path, default=None)
            if isinstance(data, dict):
                rows.append(data)
        return rows


def creator_factory_summary(data_root: str | Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    return CreatorFactoryManager(data_root).dashboard_metrics()


def _dominant(rows: list[dict[str, Any]], field: str, default: str) -> str:
    if not rows:
        return default
    values: dict[str, int] = {}
    for row in rows:
        value = row.get(field, default)
        values[value] = values.get(value, 0) + 1
    return sorted(values.items(), key=lambda pair: pair[1], reverse=True)[0][0]


def _pipeline_status(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "idle"
    if any(row.get("status") == "generating" for row in rows):
        return "generating"
    if any(row.get("status") == "queued" for row in rows):
        return "queued"
    if any(row.get("status") == "reviewing" for row in rows):
        return "reviewing"
    return "idle"


def _count_since(items: list[dict[str, Any]], cutoff: date) -> int:
    count = 0
    for item in items:
        try:
            if date.fromisoformat(str(item.get("updated_at", ""))[:10]) >= cutoff:
                count += 1
        except ValueError:
            continue
    return count
