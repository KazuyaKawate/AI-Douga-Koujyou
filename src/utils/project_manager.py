"""Project-level settings, series management, and episode operations.

Extension points (FUTURE):
  - ProjectContext carries user_id / cloud_endpoint / subscription_tier
  - can_use_feature() gates premium capabilities without API changes
  - cloud_sync_series() / cloud_push_episode() hook in here
"""
from __future__ import annotations

import json
import shutil
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


# ── ProjectContext (future-ready extension point) ──────────────────────────────

class ProjectContext:
    """
    Carries per-session metadata.  Currently 'local' only.

    FUTURE additions (add fields here — no callers need to change):
      user_id         : str  — authenticated user (multi-user)
      cloud_endpoint  : str  — cloud sync URL
      subscription_tier: str — free / pro / enterprise
      auth_token      : str  — JWT / API key
    """

    def __init__(self) -> None:
        self.version:           str  = "3.1"
        self.user_id:           str  = "local"
        self.cloud_endpoint:    str  = ""
        self.subscription_tier: str  = "local"
        self.locale:            str  = "ja"
        self.features: dict[str, bool] = {
            "cloud_sync":   False,  # FUTURE
            "multi_user":   False,  # FUTURE
            "auto_publish": False,  # FUTURE
            "analytics_ai": False,  # FUTURE
        }

    def can_use(self, feature: str) -> bool:
        """Gate-check for a feature. Always True locally; hook subscription checks here."""
        return True  # FUTURE: check self.subscription_tier

    def is_cloud(self) -> bool:
        return bool(self.cloud_endpoint)  # FUTURE: real implementation

    def as_dict(self) -> dict:
        return {
            "version":           self.version,
            "user_id":           self.user_id,
            "cloud_endpoint":    self.cloud_endpoint,
            "subscription_tier": self.subscription_tier,
            "locale":            self.locale,
            "features":          self.features,
        }


# ── Load / Save ────────────────────────────────────────────────────────────────

def load_project_settings() -> dict:
    if PROJECT_SETTINGS_PATH.exists():
        try:
            data = json.loads(PROJECT_SETTINGS_PATH.read_text(encoding="utf-8"))
            data.setdefault("project", _default_project())
            data.setdefault("series", [])
            data.setdefault("backup", _default_backup_settings())
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


def get_backup_settings() -> dict:
    return load_project_settings().get("backup", _default_backup_settings())


def update_backup_settings(updates: dict) -> dict:
    data = load_project_settings()
    data.setdefault("backup", _default_backup_settings())
    data["backup"].update(updates)
    save_project_settings(data)
    return data["backup"]


# ── Series ─────────────────────────────────────────────────────────────────────

def list_series(include_archived: bool = False) -> list[dict]:
    all_series = load_project_settings().get("series", [])
    if include_archived:
        return all_series
    return [s for s in all_series if not s.get("archived", False)]


def list_all_series() -> list[dict]:
    return load_project_settings().get("series", [])


def get_series(series_id: str) -> dict | None:
    return next((s for s in list_all_series() if s["id"] == series_id), None)


def add_series(name: str, description: str = "") -> dict:
    data  = load_project_settings()
    now   = datetime.now().isoformat()
    entry = {
        "id":          f"series_{uuid.uuid4().hex[:8]}",
        "name":        name.strip(),
        "description": description.strip(),
        "episode_ids": [],
        "archived":    False,
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


def archive_series(series_id: str, archived: bool = True) -> dict | None:
    return update_series(series_id, {"archived": archived})


def duplicate_series(series_id: str) -> dict | None:
    """Create a new series pointing to the same episodes (no episode file copy)."""
    src = get_series(series_id)
    if not src:
        return None
    now   = datetime.now().isoformat()
    entry = {
        "id":          f"series_{uuid.uuid4().hex[:8]}",
        "name":        src["name"] + " (コピー)",
        "description": src.get("description", ""),
        "episode_ids": list(src.get("episode_ids", [])),
        "archived":    False,
        "created_at":  now,
        "updated_at":  now,
    }
    data = load_project_settings()
    data["series"].append(entry)
    save_project_settings(data)
    return entry


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


# ── Episode operations ─────────────────────────────────────────────────────────

def duplicate_episode(ep_id: str) -> str | None:
    """Copy episode JSON + text files to a new folder. Returns new ep_id or None."""
    src_dir = PROJECT_ROOT / "project" / ep_id
    if not src_dir.exists():
        return None

    # Unique new ID
    new_id = ep_id + "_copy"
    counter = 2
    while (PROJECT_ROOT / "project" / new_id).exists():
        new_id = f"{ep_id}_copy{counter}"
        counter += 1

    dst_dir = PROJECT_ROOT / "project" / new_id
    dst_dir.mkdir(parents=True, exist_ok=True)

    # Copy JSON files (preserving sub-dirs like export/)
    for f in src_dir.rglob("*.json"):
        rel = f.relative_to(src_dir)
        dst = dst_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dst)

    # Copy text / subtitle files (flat in episode root)
    for pattern in ["*.txt", "*.srt"]:
        for f in src_dir.glob(pattern):
            shutil.copy2(f, dst_dir / f.name)

    # Update episode_id + title inside episode.json
    ep_json_dst = dst_dir / "episode.json"
    if ep_json_dst.exists():
        try:
            data          = json.loads(ep_json_dst.read_text(encoding="utf-8"))
            data["episode_id"] = new_id
            old_title     = data.get("title", "")
            data["title"] = (old_title + " (コピー)") if old_title else new_id
            ep_json_dst.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    return new_id


def batch_rename_episodes(renames: dict[str, str]) -> list[str]:
    """Update title in episode.json for each ep_id. Returns list of updated ids."""
    updated: list[str] = []
    for ep_id, new_title in renames.items():
        ep_json = PROJECT_ROOT / "project" / ep_id / "episode.json"
        if not ep_json.exists():
            continue
        try:
            data          = json.loads(ep_json.read_text(encoding="utf-8"))
            data["title"] = new_title.strip()
            ep_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            updated.append(ep_id)
        except Exception:
            pass
    return updated


def archive_episode(ep_id: str, archived: bool = True) -> bool:
    """Set archived flag in production_state.json."""
    ep_dir = PROJECT_ROOT / "project" / ep_id
    if not ep_dir.exists():
        return False
    prod_path = ep_dir / "production_state.json"
    state: dict = {}
    if prod_path.exists():
        try:
            state = json.loads(prod_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    state["archived"] = archived
    try:
        prod_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception:
        return False


def delete_episode(ep_id: str) -> bool:
    """Permanently delete an episode folder. Irreversible."""
    ep_dir = PROJECT_ROOT / "project" / ep_id
    if not ep_dir.exists():
        return False
    try:
        shutil.rmtree(ep_dir)
        # Remove from all series
        data = load_project_settings()
        for s in data["series"]:
            s["episode_ids"] = [e for e in s["episode_ids"] if e != ep_id]
        save_project_settings(data)
        return True
    except Exception:
        return False


def batch_rename_series(renames: dict[str, str]) -> list[str]:
    """Rename series by ID. renames = {series_id: new_name}. Returns updated IDs."""
    updated: list[str] = []
    data = load_project_settings()
    for s in data["series"]:
        if s["id"] in renames:
            s["name"]       = renames[s["id"]].strip()
            s["updated_at"] = datetime.now().isoformat()
            updated.append(s["id"])
    if updated:
        save_project_settings(data)
    return updated


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


def _default_backup_settings() -> dict:
    return {
        "auto_enabled":        True,
        "interval_hours":      24,
        "max_keep":            20,
        "include_project_json": True,
    }


def _default_settings() -> dict:
    return {
        "project": _default_project(),
        "series":  [],
        "backup":  _default_backup_settings(),
    }
