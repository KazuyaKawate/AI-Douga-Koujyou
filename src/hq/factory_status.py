"""Factory Status — loads and saves factory status cards from config/factory_status.json."""
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "factory_status.json"

FACTORIES = ["AI動画工場", "note投稿工場", "SNS投稿工場", "営業工場", "会計監査工場", "CEO Dashboard"]

FACTORY_ICONS = {
    "AI動画工場":    "🎬",
    "note投稿工場":  "📝",
    "SNS投稿工場":   "📱",
    "営業工場":      "💼",
    "会計監査工場":  "💰",
    "CEO Dashboard": "🎯",
}

STATUS_COLORS = {
    "active":  "🟢",
    "idle":    "🟡",
    "warning": "🔴",
    "stopped": "⚫",
}

_DEFAULTS = {
    "AI動画工場":    {"status": "idle", "active_items": 0, "completed_today": 0, "warning_count": 0, "next_action": "動画を制作してください"},
    "note投稿工場":  {"status": "idle", "active_items": 0, "completed_today": 0, "warning_count": 0, "next_action": "記事を作成してください"},
    "SNS投稿工場":   {"status": "idle", "active_items": 0, "completed_today": 0, "warning_count": 0, "next_action": "投稿を作成してください"},
    "営業工場":      {"status": "idle", "active_items": 0, "completed_today": 0, "warning_count": 0, "next_action": "営業活動を開始してください"},
    "会計監査工場":  {"status": "idle", "active_items": 0, "completed_today": 0, "warning_count": 0, "next_action": "収支を確認してください"},
    "CEO Dashboard": {"status": "active", "active_items": 1, "completed_today": 0, "warning_count": 0, "next_action": "KPIを確認してください"},
}


def load_factory_status() -> dict:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            for factory, defaults in _DEFAULTS.items():
                if factory not in data:
                    data[factory] = defaults.copy()
            return data
        except Exception:
            pass
    data = {k: v.copy() for k, v in _DEFAULTS.items()}
    _save(data)
    return data


def save_factory_status(data: dict) -> None:
    _save(data)


def _save(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def sync_from_tasks(factory_data: dict, tasks_data: dict) -> dict:
    """Sync factory completed/active counts from task data."""
    from src.hq.task_manager import CATEGORIES
    cat_map = {
        "AI動画工場":   "AI動画工場",
        "note投稿工場": "note投稿工場",
        "SNS投稿工場":  "SNS投稿工場",
        "営業工場":     "営業工場",
        "会計監査工場": "会計監査工場",
    }
    tasks = tasks_data.get("tasks", [])
    for cat, factory_key in cat_map.items():
        cat_tasks = [t for t in tasks if t.get("category") == cat]
        done = sum(1 for t in cat_tasks if t["status"] == "done")
        active = sum(1 for t in cat_tasks if t["status"] == "in_progress")
        if factory_key in factory_data:
            factory_data[factory_key]["completed_today"] = done
            factory_data[factory_key]["active_items"] = active
            if done > 0 or active > 0:
                factory_data[factory_key]["status"] = "active"
    return factory_data
