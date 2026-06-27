"""release_manager — Release record CRUD for Development Studio."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

ROOT        = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "config" / "devstudio_releases.json"

HEALTH_STATUSES = ["green", "yellow", "red", "unknown"]


def _default_store() -> dict:
    return {
        "releases": [
            {
                "release_id": "REL-001",
                "version": "4.8",
                "title": "Automation Factory",
                "date": "2026-06-27",
                "commit_id": "",
                "health_status": "green",
                "summary": "Rule-based workflow automation across all factories.",
                "notes": "7 modules, dry-run default, 5 built-in templates.",
            },
            {
                "release_id": "REL-002",
                "version": "5.0-beta",
                "title": "Development Studio",
                "date": "2026-06-27",
                "commit_id": "",
                "health_status": "green",
                "summary": "OS development headquarters. Roadmap, decisions, releases, health check, git status.",
                "notes": "v5.0 Beta milestone 1.",
            },
        ],
        "meta": {"version": "5.0-beta", "created_at": datetime.now().strftime("%Y-%m-%d")},
    }


def load_releases() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    data = _default_store()
    save_releases(data)
    return data


def save_releases(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_all_releases() -> list[dict]:
    return load_releases().get("releases", [])


def get_release(release_id: str) -> dict | None:
    return next((r for r in get_all_releases() if r["release_id"] == release_id), None)


def get_latest_release() -> dict | None:
    releases = sorted(get_all_releases(), key=lambda r: r.get("date", ""), reverse=True)
    return releases[0] if releases else None


def create_release(
    version: str,
    title: str,
    date: str,
    commit_id: str,
    health_status: str,
    summary: str,
    notes: str,
) -> dict:
    data = load_releases()
    releases = data.get("releases", [])
    idx = len(releases) + 1
    rel = {
        "release_id": f"REL-{idx:03d}",
        "version": version,
        "title": title,
        "date": date,
        "commit_id": commit_id,
        "health_status": health_status,
        "summary": summary,
        "notes": notes,
    }
    releases.append(rel)
    data["releases"] = releases
    save_releases(data)
    return rel


def update_release(release_id: str, **kwargs) -> dict | None:
    data = load_releases()
    for rel in data.get("releases", []):
        if rel["release_id"] == release_id:
            rel.update(kwargs)
            save_releases(data)
            return rel
    return None


def delete_release(release_id: str) -> bool:
    data = load_releases()
    before = len(data.get("releases", []))
    data["releases"] = [r for r in data.get("releases", []) if r["release_id"] != release_id]
    if len(data["releases"]) < before:
        save_releases(data)
        return True
    return False
