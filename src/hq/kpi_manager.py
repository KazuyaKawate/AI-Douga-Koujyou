"""KPI Manager — loads and saves daily KPI data from config/kpi_targets.json."""
import json
from datetime import date
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "kpi_targets.json"

KPI_META = [
    ("sales_target", "今日の売上目標", "円", False),
    ("sales_actual", "今日の売上実績", "円", True),
    ("note_posts",   "note投稿数",     "件", True),
    ("video_count",  "動画制作数",     "本", True),
    ("sns_posts",    "SNS投稿数",      "件", True),
    ("sales_calls",  "営業件数",       "件", True),
    ("dev_tasks",    "開発タスク数",   "件", True),
]

_DEFAULT_TARGETS = {
    "sales_target": 50000,
    "note_posts": 1,
    "video_count": 1,
    "sns_posts": 3,
    "sales_calls": 5,
    "dev_tasks": 3,
}

_DEFAULT_ACTUALS = {k: 0 for k in ("sales_actual", "note_posts", "video_count", "sns_posts", "sales_calls", "dev_tasks")}


def load_kpi() -> dict:
    today = date.today().isoformat()
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if data.get("date") != today:
                data["date"] = today
                data["actuals"] = _DEFAULT_ACTUALS.copy()
                _save(data)
            return data
        except Exception:
            pass
    data = {"date": today, "targets": _DEFAULT_TARGETS.copy(), "actuals": _DEFAULT_ACTUALS.copy()}
    _save(data)
    return data


def save_kpi(data: dict) -> None:
    _save(data)


def _save(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def update_actual(key: str, value: int) -> dict:
    data = load_kpi()
    data["actuals"][key] = value
    _save(data)
    return data


def get_kpi_rows(data: dict) -> list[dict]:
    """Return list of dicts for display: key, label, unit, target, actual, pct, is_actual."""
    targets = data.get("targets", _DEFAULT_TARGETS)
    actuals = data.get("actuals", _DEFAULT_ACTUALS)
    rows = []
    for key, label, unit, is_actual in KPI_META:
        if is_actual:
            # Find corresponding target key
            target_key = key if key in targets else key.replace("actual", "target")
            if key == "sales_actual":
                target = targets.get("sales_target", 0)
            else:
                target = targets.get(key, 0)
            actual = actuals.get(key, 0)
            pct = min(int(actual / target * 100), 100) if target > 0 else 0
        else:
            target = targets.get(key, 0)
            actual = target  # target is the value itself
            pct = 100
        rows.append({
            "key": key,
            "label": label,
            "unit": unit,
            "target": target,
            "actual": actual,
            "pct": pct,
            "is_actual": is_actual,
        })
    return rows
