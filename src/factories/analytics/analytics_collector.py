"""analytics_collector — read-only data collection from all factory config files."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent.parent
SETTINGS_PATH = ROOT / "config" / "analytics_settings.json"


def _read_json(rel: str) -> dict:
    p = ROOT / rel
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _collect_projects() -> list[dict]:
    try:
        from src.core.project_manager import get_all_projects
        return [p.get_summary() for p in get_all_projects()]
    except Exception:
        return []


def _collect_registry() -> dict:
    try:
        from src.core.factory_registry import FactoryRegistry
        return FactoryRegistry.get_summary()
    except Exception:
        return {}


def _collect_video() -> dict:
    proj_dir = ROOT / "project"
    if not proj_dir.exists():
        return {"total": 0, "with_director": 0, "exported": 0}
    eps = [d for d in proj_dir.iterdir() if d.is_dir() and (d / "episode.json").exists()]
    return {
        "total":         len(eps),
        "with_director": sum(1 for e in eps if (e / "director_plan.json").exists()),
        "exported":      sum(1 for e in eps if (e / "export" / "production_report.json").exists()),
    }


def collect_snapshot() -> dict:
    """Collect a unified data snapshot from all factory config files."""
    return {
        "timestamp":               datetime.now().isoformat(timespec="seconds"),
        "kpi":                     _read_json("config/kpi_targets.json"),
        "factory_status":          _read_json("config/factory_status.json"),
        "tasks":                   _read_json("config/daily_tasks.json"),
        "note":                    _read_json("config/note_articles.json"),
        "sns":                     _read_json("config/sns_posts.json"),
        "sales_leads":             _read_json("config/sales_leads.json"),
        "sales_deals":             _read_json("config/sales_deals.json"),
        "accounting_revenue":      _read_json("config/accounting_revenue.json"),
        "accounting_expenses":     _read_json("config/accounting_expenses.json"),
        "accounting_subscriptions":_read_json("config/accounting_subscriptions.json"),
        "video":                   _collect_video(),
        "projects":                _collect_projects(),
        "factory_registry":        _collect_registry(),
    }


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "snapshot_limit":         30,
        "insights_enabled":       True,
        "kpi_alert_threshold":    50,
        "roi_target_pct":         20,
        "meta": {"version": "4.7"},
    }
