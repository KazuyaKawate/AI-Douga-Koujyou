"""Project-level settings and series management."""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

from src.utils.config import PROJECT_ROOT

PROJECT_SETTINGS_PATH = PROJECT_ROOT / "config" / "project_settings.json"

GENRE_OPTIONS = [
    "解説・教育", "エンタメ", "ニュース・情報",
    "ビジネス・マーケティング", "Vlog・日常", "ゲーム",
    "テクノロジー", "料理・グルメ", "その他",
]
LANGUAGE_OPTIONS = ["ja", "en", "zh", "ko", "es", "fr", "de"]


# ── Load / Save ────────────────────────────────────────────────────────────────

def load_project_settings() -> dict:
    if PROJECT_SETTINGS_PATH.exists():
        try:
            data = json.loads(PROJECT_SETTINGS_PATH.read_text(encoding="utf-8"))
            # Back-fill defaults for missing keys
            data.setdefault("project", _default_project())
            data.setdefault("series", [])
            return data
        except Exception:
            pass
    return _default_settings()


def save_project_settings(data: dict) -> None:
    data["project"]["updated_at"] = datetime.now().isoformat()
    PROJECT_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROJECT_SETTINGS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Project info ───────────────────────────────────────────────────────────────

def get_project_info() -> dict:
    return load_project_settings()["project"]


def update_project_info(updates: dict) -> dict:
    data = load_project_settings()
    data["project"].update(updates)
    save_project_settings(data)
    return data["project"]


# ── Series ─────────────────────────────────────────────────────────────────────

def list_series() -> list[dict]:
    return load_project_settings().get("series", [])


def get_series(series_id: str) -> dict | None:
    return next((s for s in list_series() if s["id"] == series_id), None)


def add_series(name: str, description: str = "") -> dict:
    data  = load_project_settings()
    now   = datetime.now().isoformat()
    entry = {
        "id":          f"series_{uuid.uuid4().hex[:8]}",
        "name":        name.strip(),
        "description": description.strip(),
        "episode_ids": [],
        "created_at":  now,
        "updated_at":  now,
    }
    data["series"].append(entry)
    save_project_settings(data)
    return entry


def update_series(series_id: str, updates: dict) -> dict | None:
    data = load_project_settings()
    for s in data["series"]:
        if s["id"] == series_id:
            s.update(updates)
            s["updated_at"] = datetime.now().isoformat()
            save_project_settings(data)
            return s
    return None


def delete_series(series_id: str) -> bool:
    data     = load_project_settings()
    original = len(data["series"])
    data["series"] = [s for s in data["series"] if s["id"] != series_id]
    if len(data["series"]) < original:
        save_project_settings(data)
        return True
    return False


def add_episode_to_series(series_id: str, episode_id: str) -> dict | None:
    data = load_project_settings()
    for s in data["series"]:
        if s["id"] == series_id:
            if episode_id not in s["episode_ids"]:
                s["episode_ids"].append(episode_id)
                s["updated_at"] = datetime.now().isoformat()
            save_project_settings(data)
            return s
    return None


def remove_episode_from_series(series_id: str, episode_id: str) -> dict | None:
    data = load_project_settings()
    for s in data["series"]:
        if s["id"] == series_id:
            s["episode_ids"] = [e for e in s["episode_ids"] if e != episode_id]
            s["updated_at"]  = datetime.now().isoformat()
            save_project_settings(data)
            return s
    return None


def set_episode_order_in_series(series_id: str, ordered_ids: list[str]) -> dict | None:
    return update_series(series_id, {"episode_ids": ordered_ids})


# ── Defaults ───────────────────────────────────────────────────────────────────

def _default_project() -> dict:
    now = datetime.now().isoformat()
    return {
        "name":           "AI動画工場プロジェクト",
        "description":    "",
        "target_channel": "",
        "genre":          GENRE_OPTIONS[0],
        "language":       "ja",
        "created_at":     now,
        "updated_at":     now,
    }


def _default_settings() -> dict:
    return {"project": _default_project(), "series": []}
