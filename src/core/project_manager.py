"""ProjectManager — project CRUD for Creator Factory OS project-centric model.

A Project is the top-level unit. Factories are modules within a project.
"""
from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "config" / "projects.json"

PROJECT_STATUSES = ("active", "paused", "completed", "archived")
STATUS_LABELS = {
    "active":    "稼働中",
    "paused":    "一時停止",
    "completed": "完了",
    "archived":  "アーカイブ",
}
STATUS_ICONS = {
    "active":    "🟢",
    "paused":    "🟡",
    "completed": "✅",
    "archived":  "⬜",
}

ALL_FACTORY_NAMES = (
    "AI動画工場",
    "note投稿工場",
    "SNS投稿工場",
    "承認アシスタント",
    "営業工場",
    "会計監査工場",
)


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class Project:
    project_id: str
    name: str
    owner: str
    factories: list[str]
    status: str = "active"
    revenue: int = 0
    priority: int = 3           # 1 (highest) – 5 (lowest)
    progress: float = 0.0       # 0–100
    description: str = ""
    created_at: str = ""
    updated_at: str = ""

    def get_summary(self) -> dict:
        return {
            "project_id":  self.project_id,
            "name":        self.name,
            "owner":       self.owner,
            "factories":   self.factories,
            "status":      self.status,
            "status_label": STATUS_LABELS.get(self.status, self.status),
            "status_icon":  STATUS_ICONS.get(self.status, "⚪"),
            "revenue":     self.revenue,
            "priority":    self.priority,
            "progress":    self.progress,
            "description": self.description,
            "factory_count": len(self.factories),
            "created_at":  self.created_at,
            "updated_at":  self.updated_at,
        }

    def add_factory(self, factory_name: str) -> None:
        if factory_name not in self.factories:
            self.factories.append(factory_name)
            self.updated_at = datetime.now().strftime("%Y-%m-%d")

    def remove_factory(self, factory_name: str) -> None:
        if factory_name in self.factories:
            self.factories.remove(factory_name)
            self.updated_at = datetime.now().strftime("%Y-%m-%d")

    def to_dict(self) -> dict:
        return {
            "project_id":  self.project_id,
            "name":        self.name,
            "owner":       self.owner,
            "factories":   self.factories,
            "status":      self.status,
            "revenue":     self.revenue,
            "priority":    self.priority,
            "progress":    self.progress,
            "description": self.description,
            "created_at":  self.created_at,
            "updated_at":  self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        return cls(
            project_id=  d.get("project_id",  ""),
            name=        d.get("name",         ""),
            owner=       d.get("owner",        ""),
            factories=   d.get("factories",    []),
            status=      d.get("status",       "active"),
            revenue=     d.get("revenue",      0),
            priority=    d.get("priority",     3),
            progress=    d.get("progress",     0.0),
            description= d.get("description",  ""),
            created_at=  d.get("created_at",   ""),
            updated_at=  d.get("updated_at",   ""),
        )


# ── Default data ───────────────────────────────────────────────────────────────

def _default_store() -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "projects": [
            {
                "project_id":  "proj_creator_factory",
                "name":        "Creator Factory",
                "owner":       "自分",
                "factories":   list(ALL_FACTORY_NAMES),
                "status":      "active",
                "revenue":     0,
                "priority":    1,
                "progress":    0.0,
                "description": "メインクリエイターファクトリー — 全工場を統合",
                "created_at":  today,
                "updated_at":  today,
            }
        ],
        "meta": {
            "version":    "4.5.1",
            "created_at": today,
        },
    }


# ── CRUD ──────────────────────────────────────────────────────────────────────

def load_projects() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    data = _default_store()
    save_projects(data)
    return data


def save_projects(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_project(
    name: str,
    owner: str = "自分",
    factories: list[str] | None = None,
    description: str = "",
    priority: int = 3,
) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    project = {
        "project_id":  "proj_" + uuid.uuid4().hex[:8],
        "name":        name,
        "owner":       owner,
        "factories":   factories or [],
        "status":      "active",
        "revenue":     0,
        "priority":    priority,
        "progress":    0.0,
        "description": description,
        "created_at":  today,
        "updated_at":  today,
    }
    data = load_projects()
    data["projects"].append(project)
    save_projects(data)
    return project


def update_project(project_id: str, **kwargs) -> tuple[bool, str]:
    data = load_projects()
    for p in data["projects"]:
        if p["project_id"] == project_id:
            allowed = {"name", "owner", "factories", "status", "revenue",
                       "priority", "progress", "description"}
            for k, v in kwargs.items():
                if k in allowed:
                    p[k] = v
            p["updated_at"] = datetime.now().strftime("%Y-%m-%d")
            save_projects(data)
            return True, "更新しました"
    return False, "プロジェクトが見つかりません"


def delete_project(project_id: str) -> tuple[bool, str]:
    data = load_projects()
    before = len(data["projects"])
    data["projects"] = [p for p in data["projects"] if p["project_id"] != project_id]
    if len(data["projects"]) == before:
        return False, "プロジェクトが見つかりません"
    save_projects(data)
    return True, "削除しました"


def get_all_projects() -> list[Project]:
    data = load_projects()
    return [Project.from_dict(p) for p in data.get("projects", [])]


def get_project(project_id: str) -> Project | None:
    data = load_projects()
    for p in data.get("projects", []):
        if p["project_id"] == project_id:
            return Project.from_dict(p)
    return None


def get_active_projects() -> list[Project]:
    return [p for p in get_all_projects() if p.status == "active"]
