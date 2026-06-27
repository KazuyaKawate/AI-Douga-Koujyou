"""decision_log_manager — Decision log CRUD for Development Studio."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

ROOT        = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "config" / "devstudio_decisions.json"

STATUSES = ["open", "accepted", "rejected", "superseded"]
IMPACTS  = ["high", "medium", "low"]


def _default_store() -> dict:
    return {
        "decisions": [
            {
                "decision_id": "DEC-001",
                "date": "2026-06-27",
                "version": "5.0-beta",
                "theme": "Architecture",
                "decision": "Start v5.0 Beta with Development Studio as first milestone.",
                "reason": "Need a central dev management HQ before adding new factories.",
                "expected_effect": "Better visibility into roadmap, decisions, and release history.",
                "impact": "high",
                "status": "accepted",
            }
        ],
        "meta": {"version": "5.0-beta", "created_at": datetime.now().strftime("%Y-%m-%d")},
    }


def load_decisions() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    data = _default_store()
    save_decisions(data)
    return data


def save_decisions(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_all_decisions() -> list[dict]:
    return load_decisions().get("decisions", [])


def get_decision(decision_id: str) -> dict | None:
    return next((d for d in get_all_decisions() if d["decision_id"] == decision_id), None)


def create_decision(
    date: str,
    version: str,
    theme: str,
    decision: str,
    reason: str,
    expected_effect: str,
    impact: str,
    status: str,
) -> dict:
    data = load_decisions()
    decisions = data.get("decisions", [])
    idx = len(decisions) + 1
    dec = {
        "decision_id": f"DEC-{idx:03d}",
        "date": date,
        "version": version,
        "theme": theme,
        "decision": decision,
        "reason": reason,
        "expected_effect": expected_effect,
        "impact": impact,
        "status": status,
    }
    decisions.append(dec)
    data["decisions"] = decisions
    save_decisions(data)
    return dec


def update_decision(decision_id: str, **kwargs) -> dict | None:
    data = load_decisions()
    for dec in data.get("decisions", []):
        if dec["decision_id"] == decision_id:
            dec.update(kwargs)
            save_decisions(data)
            return dec
    return None


def delete_decision(decision_id: str) -> bool:
    data = load_decisions()
    before = len(data.get("decisions", []))
    data["decisions"] = [d for d in data.get("decisions", []) if d["decision_id"] != decision_id]
    if len(data["decisions"]) < before:
        save_decisions(data)
        return True
    return False


def get_open_count() -> int:
    return sum(1 for d in get_all_decisions() if d.get("status") == "open")
