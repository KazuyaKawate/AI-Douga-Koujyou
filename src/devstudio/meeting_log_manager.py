"""meeting_log_manager — Meeting notes CRUD for Development Studio."""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

ROOT        = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "config" / "devstudio_meetings.json"


def _default_store() -> dict:
    return {
        "meetings": [
            {
                "meeting_id": "MTG-001",
                "date": "2026-06-27",
                "title": "v5.0 Beta Kickoff",
                "agenda": "Start v5.0 Beta. Define first milestone: Development Studio.",
                "notes": "Agreed to build Development Studio as the OS HQ before adding new factories.",
                "decisions": "Development Studio is milestone 1 of v5.0 Beta.",
                "next_actions": "Build and deploy pages/25_Development_Studio.py.",
            }
        ],
        "meta": {"version": "5.0-beta", "created_at": datetime.now().strftime("%Y-%m-%d")},
    }


def load_meetings() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    data = _default_store()
    save_meetings(data)
    return data


def save_meetings(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_all_meetings() -> list[dict]:
    meetings = load_meetings().get("meetings", [])
    return sorted(meetings, key=lambda m: m.get("date", ""), reverse=True)


def get_meeting(meeting_id: str) -> dict | None:
    return next((m for m in get_all_meetings() if m["meeting_id"] == meeting_id), None)


def get_recent_meetings(n: int = 3) -> list[dict]:
    return get_all_meetings()[:n]


def create_meeting(
    date: str,
    title: str,
    agenda: str,
    notes: str,
    decisions: str,
    next_actions: str,
) -> dict:
    data = load_meetings()
    meetings = data.get("meetings", [])
    idx = len(meetings) + 1
    mtg = {
        "meeting_id": f"MTG-{idx:03d}",
        "date": date,
        "title": title,
        "agenda": agenda,
        "notes": notes,
        "decisions": decisions,
        "next_actions": next_actions,
    }
    meetings.append(mtg)
    data["meetings"] = meetings
    save_meetings(data)
    return mtg


def update_meeting(meeting_id: str, **kwargs) -> dict | None:
    data = load_meetings()
    for mtg in data.get("meetings", []):
        if mtg["meeting_id"] == meeting_id:
            mtg.update(kwargs)
            save_meetings(data)
            return mtg
    return None


def delete_meeting(meeting_id: str) -> bool:
    data = load_meetings()
    before = len(data.get("meetings", []))
    data["meetings"] = [m for m in data.get("meetings", []) if m["meeting_id"] != meeting_id]
    if len(data["meetings"]) < before:
        save_meetings(data)
        return True
    return False
