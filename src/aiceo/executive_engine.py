"""executive_engine — Read-only data collection for AI CEO Core.

Collects a unified OS snapshot from all available factories.
Never writes to any data store. Never calls external APIs.
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def _read_json(rel: str) -> dict:
    p = ROOT / rel
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def collect_snapshot() -> dict:
    """Return a unified read-only OS snapshot. All fields degrade gracefully."""
    snap: dict = {"collected_at": datetime.now().isoformat()}

    # ── KPI ───────────────────────────────────────────────────────────────────
    try:
        from src.hq.kpi_manager import load_kpi, get_kpi_rows
        kpi_data = load_kpi()
        snap["kpi"] = {
            "date": kpi_data.get("date", ""),
            "targets": kpi_data.get("targets", {}),
            "actuals": kpi_data.get("actuals", {}),
            "rows": get_kpi_rows(kpi_data),
        }
    except Exception:
        snap["kpi"] = {}

    # ── Tasks ─────────────────────────────────────────────────────────────────
    try:
        from src.hq.task_manager import load_tasks, get_task_stats
        tasks_data = load_tasks()
        snap["tasks"] = {
            "tasks": tasks_data.get("tasks", []),
            "stats": get_task_stats(tasks_data),
        }
    except Exception:
        snap["tasks"] = {"tasks": [], "stats": {}}

    # ── Factory Status ────────────────────────────────────────────────────────
    try:
        from src.hq.factory_status import load_factory_status
        snap["factory_status"] = load_factory_status()
    except Exception:
        snap["factory_status"] = {}

    # ── Finance ───────────────────────────────────────────────────────────────
    fin = _read_json("config/revenue_expense.json")
    snap["finance"] = {
        "today": fin.get("today", {}),
        "month": fin.get("month", {}),
    }

    # ── Note Factory ──────────────────────────────────────────────────────────
    note = _read_json("config/note_articles.json")
    arts = note.get("articles", [])
    snap["note"] = {
        "total": len(arts),
        "published": sum(1 for a in arts if a.get("status") == "published"),
        "draft": sum(1 for a in arts if a.get("status") == "draft"),
        "review": sum(1 for a in arts if a.get("status") == "review"),
    }

    # ── SNS Factory ───────────────────────────────────────────────────────────
    sns = _read_json("config/sns_posts.json")
    posts = sns.get("posts", [])
    snap["sns"] = {
        "total": len(posts),
        "published": sum(1 for p in posts if p.get("status") == "published"),
        "scheduled": sum(1 for p in posts if p.get("status") == "scheduled"),
        "draft": sum(1 for p in posts if p.get("status") == "draft"),
    }

    # ── Sales Factory ─────────────────────────────────────────────────────────
    try:
        from src.factories.sales.lead_manager import load_leads, get_factory_summary as _ls
        from src.factories.sales.deal_manager import load_deals, get_factory_summary as _ds
        from src.factories.sales.followup_manager import load_followups, get_followup_summary as _fs
        from src.factories.sales.sales_forecast import calculate_forecast as _fc
        _ld = load_leads(); _dd = load_deals(); _fd = load_followups()
        snap["sales"] = {
            "leads": _ls(_ld),
            "deals": _ds(_dd),
            "followups": _fs(_fd),
            "forecast": _fc(_ld, _dd),
        }
    except Exception:
        snap["sales"] = {}

    # ── Accounting Factory ────────────────────────────────────────────────────
    try:
        from src.factories.accounting.revenue_manager import load_revenue
        from src.factories.accounting.expense_manager import load_expenses
        from src.factories.accounting.subscription_manager import load_subscriptions
        from src.factories.accounting.roi_calculator import calculate_roi
        from src.factories.accounting.audit_checker import check_audits, get_audit_summary
        import datetime as _dt
        _ym = _dt.date.today().strftime("%Y-%m")
        _rd = load_revenue(); _ed = load_expenses(); _sd = load_subscriptions()
        snap["accounting"] = {
            "roi": calculate_roi(_rd, _ed, _sd, _ym),
            "audit": get_audit_summary(check_audits(_rd, _ed, _sd)),
        }
    except Exception:
        snap["accounting"] = {}

    # ── Automation Factory ────────────────────────────────────────────────────
    try:
        from src.factories.automation.workflow_manager import get_workflow_summary
        from src.factories.automation.automation_reporter import get_run_summary
        snap["automation"] = {
            "workflows": get_workflow_summary(),
            "runs": get_run_summary(),
        }
    except Exception:
        snap["automation"] = {}

    # ── Analytics Factory ─────────────────────────────────────────────────────
    try:
        from src.factories.analytics.analytics_collector import collect_snapshot as _anl
        from src.factories.analytics.kpi_analyzer import analyze_kpi, get_kpi_insights
        from src.factories.analytics.factory_analyzer import analyze_factories, get_factory_insights
        from src.factories.analytics.project_analyzer import analyze_projects, get_project_insights
        _s = _anl()
        _ka = analyze_kpi(_s.get("kpi", {}))
        _fa = analyze_factories()
        _pa = analyze_projects()
        snap["analytics"] = {
            "kpi": _ka,
            "factories": _fa,
            "projects": _pa,
            "kpi_insights": get_kpi_insights(_ka),
            "factory_insights": get_factory_insights(_fa),
            "project_insights": get_project_insights(_pa),
        }
    except Exception:
        snap["analytics"] = {}

    # ── Core Registry ─────────────────────────────────────────────────────────
    try:
        from src.core.factory_registry import FactoryRegistry
        from src.core.project_registry import ProjectRegistry
        snap["registry"] = {
            "factories": FactoryRegistry.get_summary(),
            "projects": ProjectRegistry.get_system_summary(),
        }
    except Exception:
        snap["registry"] = {}

    # ── Dev Studio ────────────────────────────────────────────────────────────
    try:
        from src.devstudio.roadmap_manager import get_summary as _rm_sum
        from src.devstudio.decision_log_manager import get_open_count, get_all_decisions
        from src.devstudio.release_manager import get_latest_release
        snap["devstudio"] = {
            "roadmap": _rm_sum(),
            "open_decisions": get_open_count(),
            "blocked_decisions": sum(
                1 for d in get_all_decisions() if d.get("status") == "open" and d.get("impact") == "high"
            ),
            "latest_release": get_latest_release(),
        }
    except Exception:
        snap["devstudio"] = {}

    return snap
