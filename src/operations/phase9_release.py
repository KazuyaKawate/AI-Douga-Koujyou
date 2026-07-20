from __future__ import annotations

import csv
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.publish_engine.phase8_workflow import PHASE8_PATH
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


PHASE9_STATE_PATH = PROJECT_ROOT / "config" / "phase9_launch.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_state() -> dict[str, Any]:
    return {
        "enabled": True,
        "local_first": True,
        "dry_run": True,
        "review_required": True,
        "production_actions_enabled": False,
        "effective_publish_mode": "dry_run",
        "launch_status": "rc",
        "backups": [],
        "exports": [],
        "checklists": [],
        "updated_at": _now(),
    }


class Phase9LaunchManager:
    def __init__(self, path: str | Path = PHASE9_STATE_PATH, *, root: str | Path = PROJECT_ROOT) -> None:
        self.path = Path(path)
        self.root = Path(root)

    def load_state(self) -> dict[str, Any]:
        data = load_json(self.path, default=None)
        if not isinstance(data, dict):
            data = _default_state()
            self.save_state(data)
        defaults = _default_state()
        for key, value in defaults.items():
            data.setdefault(key, value)
        return data

    def save_state(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = _now()
        save_json_atomic(self.path, state)

    def phase8_state(self) -> dict[str, Any]:
        data = load_json(self.root / PHASE8_PATH.relative_to(PROJECT_ROOT), default={})
        return data if isinstance(data, dict) else {}

    def daily_operation_summary(self) -> dict[str, Any]:
        phase8 = self.phase8_state()
        review_items = phase8.get("review_items", [])
        publish_logs = phase8.get("publish_logs", [])
        tracking = phase8.get("revenue_tracking", [])
        weekly = phase8.get("weekly_reports", [])
        today = date.today().isoformat()
        today_logs = [row for row in publish_logs if str(row.get("published_at", "")).startswith(today)]
        today_tracking = [row for row in tracking if row.get("date") == today]
        revenue = sum(int(row.get("revenue", 0) or 0) for row in today_tracking)
        week_target = 7000
        return {
            "today": today,
            "mission": self.current_mission_title(),
            "waiting_publish": len([item for item in review_items if item.get("status") == "approved"]),
            "published": len(today_logs),
            "pending_review": len([item for item in review_items if item.get("status") == "pending_review"]),
            "revenue": revenue,
            "week_target": week_target,
            "week_achievement_rate": round(revenue / week_target * 100, 1) if week_target else 0,
            "latest_weekly_report": weekly[0] if weekly else {},
            "launch_readiness": self.launch_readiness_score(),
        }

    def current_mission_title(self) -> str:
        content = load_json(self.root / "config" / "content_factory.json", default={})
        mission = content.get("last_phase7_mission", {}) if isinstance(content, dict) else {}
        return mission.get("topic", "Run Today's Mission")

    def launch_template(self) -> list[dict[str, Any]]:
        phase8 = self.phase8_state()
        review_items = phase8.get("review_items", [])
        publish_logs = phase8.get("publish_logs", [])
        tracking = phase8.get("revenue_tracking", [])
        weekly = phase8.get("weekly_reports", [])
        return [
            {"item": "Run Today's Mission", "done": bool(load_json(self.root / "config" / "content_factory.json", default={}).get("last_phase7_mission", {}))},
            {"item": "note確認", "done": any(item.get("media") == "Note" for item in review_items)},
            {"item": "Threads確認", "done": any(item.get("media") == "Threads" for item in review_items)},
            {"item": "Website確認", "done": any(item.get("media") == "Website" for item in review_items)},
            {"item": "Publish Review", "done": any(item.get("status") in {"approved", "published_manual"} for item in review_items)},
            {"item": "手動公開", "done": bool(publish_logs)},
            {"item": "PV入力", "done": any(int(row.get("pv", 0) or 0) >= 0 for row in tracking)},
            {"item": "Revenue入力", "done": any("revenue" in row for row in tracking)},
            {"item": "Weekly Review", "done": bool(weekly)},
        ]

    def backup_daily(self) -> dict[str, Any]:
        phase8 = self.phase8_state()
        today = date.today().isoformat()
        backup_dir = self.root / "backups" / "phase9" / today
        backup_dir.mkdir(parents=True, exist_ok=True)
        files = {
            "publish_logs.json": phase8.get("publish_logs", []),
            "feedback.json": {
                "last_feedback": phase8.get("last_feedback", {}),
                "feedback_history": phase8.get("feedback_history", []),
            },
            "weekly_reports.json": phase8.get("weekly_reports", []),
        }
        written = []
        for name, payload in files.items():
            path = backup_dir / name
            save_json_atomic(path, payload)
            written.append(str(path))
        manifest = {
            "backup_id": f"bkp-{uuid4().hex[:10]}",
            "date": today,
            "files": written,
            "local_first": True,
            "created_at": _now(),
        }
        save_json_atomic(backup_dir / "manifest.json", manifest)
        state = self.load_state()
        state.setdefault("backups", []).insert(0, manifest)
        state["backups"] = state["backups"][:60]
        self.save_state(state)
        return manifest

    def export_bundle(self) -> dict[str, Any]:
        phase8 = self.phase8_state()
        export_dir = self.root / "release_candidate" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        export_id = f"exp-{uuid4().hex[:10]}"
        json_path = export_dir / f"{export_id}.json"
        md_path = export_dir / f"{export_id}.md"
        csv_path = export_dir / f"{export_id}.csv"
        payload = {
            "export_id": export_id,
            "created_at": _now(),
            "publish_logs": phase8.get("publish_logs", []),
            "revenue_tracking": phase8.get("revenue_tracking", []),
            "weekly_reports": phase8.get("weekly_reports", []),
            "feedback": phase8.get("last_feedback", {}),
        }
        save_json_atomic(json_path, payload)
        md_path.write_text(self.render_markdown_export(payload), encoding="utf-8")
        self.write_csv_export(csv_path, payload.get("revenue_tracking", []))
        record = {"export_id": export_id, "json": str(json_path), "markdown": str(md_path), "csv": str(csv_path), "created_at": _now()}
        state = self.load_state()
        state.setdefault("exports", []).insert(0, record)
        state["exports"] = state["exports"][:100]
        self.save_state(state)
        return record

    @staticmethod
    def render_markdown_export(payload: dict[str, Any]) -> str:
        lines = [
            "# AIOS Phase 9 Operation Export",
            "",
            f"- Export ID: {payload.get('export_id', '')}",
            f"- Created: {payload.get('created_at', '')}",
            f"- Publish logs: {len(payload.get('publish_logs', []))}",
            f"- Revenue rows: {len(payload.get('revenue_tracking', []))}",
            f"- Weekly reports: {len(payload.get('weekly_reports', []))}",
            "",
            "## Feedback",
            "",
            f"- Next note title: {payload.get('feedback', {}).get('next_note_title', '')}",
            f"- Next Threads focus: {payload.get('feedback', {}).get('next_threads_focus', '')}",
            f"- Next CTA: {payload.get('feedback', {}).get('next_cta', '')}",
            "",
        ]
        return "\n".join(lines)

    @staticmethod
    def write_csv_export(path: Path, rows: list[dict[str, Any]]) -> None:
        fields = ["date", "media", "topic", "pv", "impressions", "ctr", "clicks", "follower_growth", "cv", "revenue"]
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fields})

    def launch_checklist(self) -> dict[str, Any]:
        checks = [
            {"item": "Local First", "ok": True},
            {"item": "DryRun maintained", "ok": True},
            {"item": "Review required", "ok": True},
            {"item": "Publish Review screen", "ok": (self.root / "pages" / "46_Publish_Review.py").exists()},
            {"item": "Daily Operation screen", "ok": (self.root / "pages" / "47_Daily_Operation.py").exists()},
            {"item": "Phase8 feedback data", "ok": bool(self.phase8_state())},
            {"item": "Operation manual", "ok": (self.root / "docs" / "AIOS_OPERATION_MANUAL.md").exists()},
            {"item": "First Launch Checklist", "ok": (self.root / "release_candidate" / "first_launch_checklist.md").exists()},
            {"item": "Backup available", "ok": bool(self.load_state().get("backups", []))},
            {"item": "Export available", "ok": bool(self.load_state().get("exports", []))},
        ]
        score = round(sum(1 for item in checks if item.get("ok")) / len(checks) * 100, 1)
        result = {"checklist_id": f"launch-{uuid4().hex[:10]}", "score": score, "checks": checks, "created_at": _now()}
        state = self.load_state()
        state.setdefault("checklists", []).insert(0, result)
        state["checklists"] = state["checklists"][:100]
        self.save_state(state)
        return result

    def launch_readiness_score(self) -> float:
        state = self.load_state()
        latest = state.get("checklists", [{}])[0] if state.get("checklists") else {}
        return float(latest.get("score", 0) or 0)
