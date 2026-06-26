"""Task Manager — loads and saves daily tasks from config/daily_tasks.json."""
import json
from datetime import date
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "daily_tasks.json"

CATEGORIES = [
    "AI動画工場",
    "note投稿工場",
    "SNS投稿工場",
    "営業工場",
    "会計監査工場",
    "開発",
    "経営",
]

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
PRIORITY_LABEL = {"high": "🔴 高", "medium": "🟡 中", "low": "🟢 低"}
STATUS_LABEL = {"pending": "⏸ 未着手", "in_progress": "🔄 進行中", "done": "✅ 完了"}

_DEFAULT_TASKS: list[dict] = []


def load_tasks() -> dict:
    today = date.today().isoformat()
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if data.get("date") != today:
                for t in data.get("tasks", []):
                    if t.get("status") != "done":
                        t["status"] = "pending"
                data["date"] = today
                _save(data)
            return data
        except Exception:
            pass
    data = {"date": today, "tasks": list(_DEFAULT_TASKS)}
    _save(data)
    return data


def save_tasks(data: dict) -> None:
    _save(data)


def _save(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_task_status(task_id: str, new_status: str) -> dict:
    data = load_tasks()
    for t in data.get("tasks", []):
        if t["id"] == task_id:
            t["status"] = new_status
            break
    _save(data)
    return data


def get_task_stats(data: dict) -> dict:
    tasks = data.get("tasks", [])
    total = len(tasks)
    done = sum(1 for t in tasks if t["status"] == "done")
    in_progress = sum(1 for t in tasks if t["status"] == "in_progress")
    pending = sum(1 for t in tasks if t["status"] == "pending")
    pct = int(done / total * 100) if total > 0 else 0
    return {"total": total, "done": done, "in_progress": in_progress, "pending": pending, "pct": pct}


def get_tasks_by_category(data: dict) -> dict[str, list]:
    result: dict[str, list] = {cat: [] for cat in CATEGORIES}
    for t in data.get("tasks", []):
        cat = t.get("category", "開発")
        if cat in result:
            result[cat].append(t)
    return result
