from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from src.commander.monetization_flow import CommanderMonetizationFlow
from src.operations.phase9_release import PHASE9_STATE_PATH, Phase9LaunchManager
from src.publish_engine.phase8_workflow import Phase8PublishWorkflow
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Phase9RevenueManager:
    """Phase 9 revenue preparation with an immutable Production-OFF safety gate."""

    CHANNELS = ("note", "threads")

    def __init__(self, path: str | Path = PHASE9_STATE_PATH, *, root: str | Path = PROJECT_ROOT) -> None:
        self.path = Path(path)
        self.root = Path(root)
        self.launch = Phase9LaunchManager(self.path, root=self.root)
        self.phase8 = Phase8PublishWorkflow(path=self.root / "config" / "phase8_publish_feedback.json")
        self.monetization = CommanderMonetizationFlow(root=self.root)

    def load_state(self) -> dict[str, Any]:
        state = self.launch.load_state()
        state.update(
            {
                "enabled": True,
                "local_first": True,
                "dry_run": True,
                "review_required": True,
                "production_actions_enabled": False,
            }
        )
        state.setdefault("phase", "Phase 9 Revenue Preparation")
        state.setdefault("priority", "first_revenue")
        state.setdefault("requested_publish_mode", "dry_run")
        state.setdefault("effective_publish_mode", "dry_run")
        state.setdefault("mode_requests", [])
        return state

    def save_state(self, state: dict[str, Any]) -> None:
        state.update(
            {
                "enabled": True,
                "local_first": True,
                "dry_run": True,
                "review_required": True,
                "production_actions_enabled": False,
                "effective_publish_mode": "dry_run",
                "updated_at": _now(),
            }
        )
        save_json_atomic(self.path, state)

    def request_publish_mode(self, requested_mode: str) -> dict[str, Any]:
        if requested_mode not in {"dry_run", "production_preview"}:
            raise ValueError("unsupported publish mode")
        state = self.load_state()
        state["requested_publish_mode"] = requested_mode
        result = {
            "requested_mode": requested_mode,
            "effective_mode": "dry_run",
            "production_actions_enabled": False,
            "review_required": True,
            "status": "dry_run_active" if requested_mode == "dry_run" else "production_locked",
            "message": "Dry Runを維持しています。" if requested_mode == "dry_run" else "Production準備は確認のみです。本番投稿はロックされています。",
            "created_at": _now(),
        }
        state.setdefault("mode_requests", []).insert(0, result)
        state["mode_requests"] = state["mode_requests"][:50]
        self.save_state(state)
        return result

    def safety_status(self) -> dict[str, Any]:
        state = self.load_state()
        publish = load_json(self.root / "config" / "publish_engine.json", default={}) or {}
        workspace = load_json(self.root / "config" / "google_workspace.json", default={}) or {}
        checks = {
            "local_first": state.get("local_first") is True,
            "dry_run": state.get("dry_run") is True and publish.get("dry_run_default", True) is True,
            "review_required": state.get("review_required") is True and workspace.get("review_required", True) is True,
            "production_off": state.get("production_actions_enabled") is False and workspace.get("production_actions_enabled", False) is False,
            "manual_publish": publish.get("publish_mode", "manual") == "manual",
        }
        return {"ok": all(checks.values()), "checks": checks, **checks}

    def preflight(self, channel: str) -> dict[str, Any]:
        if channel not in self.CHANNELS:
            raise ValueError("unsupported channel")
        safety = self.safety_status()
        if channel == "note":
            connector_checks = {
                "account_configured": bool(os.getenv("NOTE_ACCOUNT_ID")),
                "credential_configured": bool(os.getenv("NOTE_API_TOKEN")),
                "preview_supported": True,
            }
            api = "note connector"
        else:
            connector_checks = {
                "account_configured": bool(os.getenv("THREADS_USER_ID") or os.getenv("THREADS_ACCOUNT_ID")),
                "credential_configured": bool(os.getenv("THREADS_ACCESS_TOKEN")),
                "official_meta_api": True,
                "preview_supported": True,
            }
            api = "Meta official Threads API"
        ready_for_dry_run = safety["ok"] and connector_checks["preview_supported"]
        ready_for_production = False
        return {
            "channel": channel,
            "connector": api,
            "safety": safety,
            "checks": connector_checks,
            "ready_for_dry_run": ready_for_dry_run,
            "ready_for_production": ready_for_production,
            "production_block_reason": "production_actions_enabled=False",
            "review_required": True,
            "effective_mode": "dry_run",
        }

    def unified_history(self) -> list[dict[str, Any]]:
        phase8 = self.phase8.load_state()
        rows: list[dict[str, Any]] = []
        for item in phase8.get("review_items", []):
            media = str(item.get("media", "")).lower()
            if media not in self.CHANNELS:
                continue
            rows.append(
                {
                    "id": item.get("review_id", ""),
                    "channel": media,
                    "title": item.get("title", ""),
                    "status": item.get("status", "pending_review"),
                    "dry_run": True,
                    "review_required": True,
                    "published_url": item.get("published_url", ""),
                    "updated_at": item.get("reviewed_at") or item.get("created_at", ""),
                    "source": "publish_review",
                }
            )
        for workflow in self.monetization.load().get("workflows", []):
            stage = workflow.get("stage", "ApprovalRequired")
            status = {
                "ApprovalRequired": "pending_review",
                "Approved": "approved",
                "DryRunSucceeded": "publish_waiting",
                "DryRunFailed": "dry_run_failed",
            }.get(stage, str(stage).lower())
            for channel in self.CHANNELS:
                content = workflow.get(channel, {})
                rows.append(
                    {
                        "id": f"{workflow.get('workflow_id', '')}:{channel}",
                        "channel": channel,
                        "title": content.get("title", ""),
                        "status": status,
                        "dry_run": True,
                        "review_required": True,
                        "published_url": "",
                        "updated_at": workflow.get("updated_at", workflow.get("created_at", "")),
                        "source": "commander",
                    }
                )
        for log in phase8.get("publish_logs", []):
            channel = str(log.get("media", "")).lower()
            if channel not in self.CHANNELS:
                continue
            rows.append(
                {
                    "id": log.get("publish_log_id", log.get("review_id", "")),
                    "channel": channel,
                    "title": log.get("title", ""),
                    "status": "published",
                    "dry_run": bool(log.get("dry_run", True)),
                    "review_required": True,
                    "published_url": log.get("published_url", ""),
                    "updated_at": log.get("published_at", ""),
                    "source": "manual_publish_log",
                }
            )
        rows.sort(key=lambda row: str(row.get("updated_at", "")), reverse=True)
        return rows

    def revenue_summary(self) -> dict[str, Any]:
        phase8 = self.phase8.load_state()
        history = self.unified_history()
        counts = {
            "review_waiting": 0,
            "approved": 0,
            "publish_waiting": 0,
            "published": 0,
        }
        for row in history:
            status = row.get("status")
            if status in {"pending_review", "revision_requested", "approval_waiting"}:
                counts["review_waiting"] += 1
            elif status == "approved":
                counts["approved"] += 1
            elif status in {"publish_waiting", "dry_run", "dry_run_completed"}:
                counts["publish_waiting"] += 1
            elif status in {"published", "published_manual"}:
                counts["published"] += 1
        revenue = sum(int(row.get("revenue", 0) or 0) for row in phase8.get("revenue_tracking", []))
        post_count = len([row for row in history if row.get("channel") in self.CHANNELS])
        return {
            "revenue": revenue,
            "post_count": post_count,
            **counts,
            "history_count": len(history),
            "safety": self.safety_status(),
            "production_actions_enabled": False,
            "effective_mode": "dry_run",
        }

    def progress(self) -> dict[str, Any]:
        safety = self.safety_status()
        note = self.preflight("note")
        threads = self.preflight("threads")
        features = {
            "note_preflight": note["ready_for_dry_run"],
            "threads_preflight": threads["ready_for_dry_run"],
            "commander_flow": True,
            "unified_history": True,
            "dashboard_summary": True,
            "production_off": safety["production_off"],
        }
        completed = sum(1 for value in features.values() if value)
        return {"percent": round(completed / len(features) * 100), "features": features}
