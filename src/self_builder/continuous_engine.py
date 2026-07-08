from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.business_engine.manager import BusinessEngineStore
from src.core.development_constitution import prioritize_improvements
from src.core.version import OS_VERSION
from src.self_builder import autonomous_builder as ab
from src.self_builder.knowledge_manager import load_knowledge, save_knowledge
from src.self_builder.research_manager import research_scheduler, run_research_team
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import save_json_atomic


CONTINUOUS_PATH = PROJECT_ROOT / "config" / "self_builder_continuous.json"
SPEED_PRESETS = {
    "slow": 3600,
    "normal": 900,
    "fast": 300,
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _parse_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _default_state() -> dict[str, Any]:
    return {
        "enabled": False,
        "speed": "normal",
        "scheduler": {
            "status": "stopped",
            "interval_seconds": SPEED_PRESETS["normal"],
            "heartbeat_at": "",
            "last_tick_at": "",
            "last_result": "Continuous Engine disabled by default.",
        },
        "version": {
            "current": OS_VERSION,
            "history": [
                {
                    "version": OS_VERSION,
                    "reason": "Baseline",
                    "created_at": _now(),
                }
            ],
        },
        "history": [],
        "rollback_history": [],
        "reports": {"weekly": {}, "monthly": {}},
        "roi_trend": [],
        "improvement_ranking": [],
        "agent_uptime": {},
        "updated_at": _now(),
    }


def load_continuous_state(path: str | Path = CONTINUOUS_PATH) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return _default_state()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return _default_state()
    if not isinstance(data, dict):
        return _default_state()
    defaults = _default_state()
    for key, value in defaults.items():
        data.setdefault(key, value)
    data.setdefault("scheduler", {})
    for key, value in defaults["scheduler"].items():
        data["scheduler"].setdefault(key, value)
    data.setdefault("version", {})
    data["version"].setdefault("current", OS_VERSION)
    data["version"].setdefault("history", defaults["version"]["history"])
    data.setdefault("reports", {"weekly": {}, "monthly": {}})
    data["reports"].setdefault("weekly", {})
    data["reports"].setdefault("monthly", {})
    return data


def save_continuous_state(state: dict[str, Any], path: str | Path = CONTINUOUS_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    save_json_atomic(p, state)


def set_continuous_enabled(enabled: bool, path: str | Path = CONTINUOUS_PATH) -> dict[str, Any]:
    state = load_continuous_state(path)
    state["enabled"] = bool(enabled)
    scheduler = state.setdefault("scheduler", {})
    scheduler["status"] = "running" if enabled else "stopped"
    scheduler["heartbeat_at"] = _now()
    scheduler["last_result"] = "Continuous Engine started." if enabled else "Continuous Engine stopped."
    save_continuous_state(state, path)
    return state


def configure_speed(speed: str, path: str | Path = CONTINUOUS_PATH) -> dict[str, Any]:
    state = load_continuous_state(path)
    selected = speed if speed in SPEED_PRESETS else "normal"
    state["speed"] = selected
    state.setdefault("scheduler", {})["interval_seconds"] = SPEED_PRESETS[selected]
    state["scheduler"]["last_result"] = f"Continuous speed set to {selected}."
    save_continuous_state(state, path)
    return state


def scheduler_due(state: dict[str, Any], *, force: bool = False) -> bool:
    if force:
        return True
    last_tick = _parse_time(str(state.get("scheduler", {}).get("last_tick_at", "")))
    if not last_tick:
        return True
    interval = max(int(state.get("scheduler", {}).get("interval_seconds", SPEED_PRESETS["normal"])), 60)
    return datetime.now() >= last_tick + timedelta(seconds=interval)


def continuous_tick(
    *,
    state_path: str | Path = CONTINUOUS_PATH,
    autonomous_state_path: str | Path = ab.AUTONOMOUS_PATH,
    business_store: BusinessEngineStore | None = None,
    force: bool = False,
) -> dict[str, Any]:
    state = load_continuous_state(state_path)
    scheduler = state.setdefault("scheduler", {})
    scheduler["heartbeat_at"] = _now()
    if not state.get("enabled"):
        scheduler["status"] = "stopped"
        scheduler["last_result"] = "Continuous Engine disabled; no improvement loop executed."
        save_continuous_state(state, state_path)
        return state
    if not scheduler_due(state, force=force):
        scheduler["status"] = "running"
        scheduler["last_result"] = "Waiting for next continuous interval."
        save_continuous_state(state, state_path)
        return state

    scheduler["status"] = "running"
    research_updates = run_due_research(force=force)
    ab.set_autonomous_enabled(True, autonomous_state_path)
    before_version = str(state.get("version", {}).get("current", OS_VERSION))
    autonomous_state = ab.autonomous_tick(
        state_path=autonomous_state_path,
        business_store=business_store,
        auto_execute=True,
    )
    latest_run = (autonomous_state.get("history") or [{}])[0]
    approved = latest_run.get("review", {}).get("status") == "approved"

    if approved:
        version_record = bump_version(state, latest_run)
        result = "Continuous improvement approved."
    else:
        version_record = {}
        rollback = rollback_failed_improvement(state, latest_run, before_version, business_store)
        latest_run["rollback_id"] = rollback["rollback_id"]
        result = "Continuous improvement failed; rollback plan recorded."

    cycle = {
        "cycle_id": f"cy-{uuid4().hex[:10]}",
        "status": "approved" if approved else "rolled_back",
        "research_updates": research_updates,
        "run": latest_run,
        "version": version_record,
        "created_at": _now(),
    }
    state.setdefault("history", []).insert(0, cycle)
    state["history"] = state["history"][:300]
    refresh_analytics(state)
    scheduler["last_tick_at"] = _now()
    scheduler["last_result"] = result
    save_continuous_state(state, state_path)
    return state


def run_due_research(*, force: bool = False) -> list[dict[str, Any]]:
    scheduler = research_scheduler()
    if force or scheduler.get("due_agents"):
        return run_research_team("AIOS Continuous Engine")
    return []


def bump_version(state: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    current = str(state.setdefault("version", {}).get("current", OS_VERSION))
    next_version = _next_patch_version(current)
    record = {
        "version": next_version,
        "previous_version": current,
        "run_id": run.get("run_id", ""),
        "reason": run.get("candidate", {}).get("instruction", "Continuous improvement"),
        "created_at": _now(),
    }
    state["version"]["current"] = next_version
    state["version"].setdefault("history", []).insert(0, record)
    return record


def rollback_failed_improvement(
    state: dict[str, Any],
    run: dict[str, Any],
    previous_version: str,
    business_store: BusinessEngineStore | None = None,
) -> dict[str, Any]:
    rollback = {
        "rollback_id": f"rb-{uuid4().hex[:10]}",
        "run_id": run.get("run_id", ""),
        "previous_version": previous_version,
        "restored_version": previous_version,
        "reason": run.get("review", {}).get("status", "not_approved"),
        "created_at": _now(),
    }
    state.setdefault("rollback_history", []).insert(0, rollback)
    state.setdefault("version", {})["current"] = previous_version
    knowledge = load_knowledge()
    knowledge.setdefault("history", []).insert(
        0,
        {
            "history_id": f"hist-{uuid4().hex[:10]}",
            "type": "continuous_rollback",
            "rollback": rollback,
            "created_at": _now(),
        },
    )
    save_knowledge(knowledge)
    if business_store:
        business_store.record_execution(run.get("run_id", ""), "failed", "Continuous Engine rollback recorded")
    return rollback


def refresh_analytics(state: dict[str, Any]) -> dict[str, Any]:
    history = state.get("history", [])
    approved = [cycle for cycle in history if cycle.get("status") == "approved"]
    state["roi_trend"] = _roi_trend(history)
    state["improvement_ranking"] = _improvement_ranking(history)
    state["agent_uptime"] = _agent_uptime(history)
    state["reports"] = {
        "weekly": _report(history, days=7),
        "monthly": _report(history, days=30),
    }
    state["improvement_velocity"] = {
        "approved_total": len(approved),
        "cycles_total": len(history),
        "approval_rate": round(len(approved) / max(len(history), 1) * 100, 1),
    }
    return state


def _next_patch_version(version: str) -> str:
    parts = [int(part) for part in str(version or "0").split(".") if part.isdigit()]
    if not parts:
        return "0.1"
    if len(parts) == 1:
        parts.append(1)
    else:
        parts[-1] += 1
    return ".".join(str(part) for part in parts)


def _roi_for_run(run: dict[str, Any]) -> int:
    candidate = run.get("candidate", {})
    return int(candidate.get("estimated_revenue", 0)) + int(candidate.get("estimated_minutes_saved", 0)) * 120


def _roi_trend(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trend: dict[str, int] = {}
    for cycle in history:
        created = str(cycle.get("created_at", ""))[:10]
        if not created:
            continue
        trend[created] = trend.get(created, 0) + _roi_for_run(cycle.get("run", {}))
    return [{"date": day, "roi": roi} for day, roi in sorted(trend.items())]


def _improvement_ranking(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for cycle in history:
        run = cycle.get("run", {})
        candidate = run.get("candidate", {})
        rows.append(
            {
                "run_id": run.get("run_id", ""),
                "instruction": candidate.get("instruction", ""),
                "status": cycle.get("status", ""),
                "roi": _roi_for_run(run),
                "estimated_revenue": int(candidate.get("estimated_revenue", 0) or 0),
                "estimated_minutes_saved": int(candidate.get("estimated_minutes_saved", 0) or 0),
                "risk": candidate.get("risk", candidate.get("constitution", {}).get("risk", "medium")),
                "effort": int(candidate.get("effort", 0) or 20),
            }
        )
    return prioritize_improvements(rows)[:10]


def _agent_uptime(history: list[dict[str, Any]]) -> dict[str, Any]:
    uptime: dict[str, dict[str, int]] = {}
    for cycle in history:
        for item in cycle.get("run", {}).get("autonomous_agents", []):
            agent = str(item.get("agent", "Unknown"))
            row = uptime.setdefault(agent, {"completed": 0, "total": 0})
            row["total"] += 1
            if item.get("status") == "Completed":
                row["completed"] += 1
    return {
        agent: {
            **row,
            "uptime_rate": round(row["completed"] / max(row["total"], 1) * 100, 1),
        }
        for agent, row in uptime.items()
    }


def _report(history: list[dict[str, Any]], *, days: int) -> dict[str, Any]:
    cutoff = datetime.now() - timedelta(days=days)
    rows = []
    for cycle in history:
        created = _parse_time(str(cycle.get("created_at", "")))
        if created and created >= cutoff:
            rows.append(cycle)
    approved = [cycle for cycle in rows if cycle.get("status") == "approved"]
    roi = sum(_roi_for_run(cycle.get("run", {})) for cycle in rows)
    return {
        "window_days": days,
        "cycles": len(rows),
        "approved": len(approved),
        "rollback": len(rows) - len(approved),
        "roi": roi,
        "generated_at": _now(),
    }
