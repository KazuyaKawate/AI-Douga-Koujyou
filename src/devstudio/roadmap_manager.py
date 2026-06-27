"""roadmap_manager — Roadmap CRUD for Development Studio."""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path

ROOT        = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "config" / "devstudio_roadmap.json"

STATUSES = ["planned", "in_progress", "completed", "blocked", "archived"]
TYPES    = ["feature", "bugfix", "refactor", "docs", "infra", "milestone"]
PRIORITIES = ["critical", "high", "medium", "low"]


def _default_store() -> dict:
    return {
        "roadmap": [
            {
                "roadmap_id": "RM-001",
                "version": "5.0-beta",
                "title": "Development Studio",
                "type": "milestone",
                "priority": "critical",
                "status": "in_progress",
                "planned_date": "2026-06-27",
                "completed_date": "",
                "notes": "First milestone of v5.0 Beta. Central dev management HQ.",
            }
        ],
        "meta": {"version": "5.0-beta", "created_at": datetime.now().strftime("%Y-%m-%d")},
    }


def load_roadmap() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    data = _default_store()
    save_roadmap(data)
    return data


def save_roadmap(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_all_items() -> list[dict]:
    return load_roadmap().get("roadmap", [])


def get_item(roadmap_id: str) -> dict | None:
    return next((r for r in get_all_items() if r["roadmap_id"] == roadmap_id), None)


def create_item(
    version: str,
    title: str,
    type_: str,
    priority: str,
    status: str,
    planned_date: str,
    completed_date: str,
    notes: str,
) -> dict:
    data = load_roadmap()
    items = data.get("roadmap", [])
    idx = len(items) + 1
    item = {
        "roadmap_id": f"RM-{idx:03d}",
        "version": version,
        "title": title,
        "type": type_,
        "priority": priority,
        "status": status,
        "planned_date": planned_date,
        "completed_date": completed_date,
        "notes": notes,
    }
    items.append(item)
    data["roadmap"] = items
    save_roadmap(data)
    return item


def update_item(roadmap_id: str, **kwargs) -> dict | None:
    data = load_roadmap()
    for item in data.get("roadmap", []):
        if item["roadmap_id"] == roadmap_id:
            item.update(kwargs)
            save_roadmap(data)
            return item
    return None


def delete_item(roadmap_id: str) -> bool:
    data = load_roadmap()
    before = len(data.get("roadmap", []))
    data["roadmap"] = [r for r in data.get("roadmap", []) if r["roadmap_id"] != roadmap_id]
    if len(data["roadmap"]) < before:
        save_roadmap(data)
        return True
    return False


def get_summary() -> dict:
    items = get_all_items()
    return {
        "total": len(items),
        "planned": sum(1 for r in items if r.get("status") == "planned"),
        "in_progress": sum(1 for r in items if r.get("status") == "in_progress"),
        "completed": sum(1 for r in items if r.get("status") == "completed"),
        "blocked": sum(1 for r in items if r.get("status") == "blocked"),
    }
