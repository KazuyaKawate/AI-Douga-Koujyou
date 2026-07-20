from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.content_factory.content_manager import ContentFactoryManager
from src.publish_engine.approval_manager import ApprovalManager
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import save_json_atomic


PHASE8_PATH = PROJECT_ROOT / "config" / "phase8_publish_feedback.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_state() -> dict[str, Any]:
    return {
        "enabled": True,
        "local_first": True,
        "review_required": True,
        "external_publish_enabled": False,
        "review_items": [],
        "publish_logs": [],
        "revenue_tracking": [],
        "feedback_history": [],
        "weekly_reports": [],
        "last_feedback": {},
        "updated_at": _now(),
    }


class Phase8PublishWorkflow:
    """Review-to-manual-publish feedback loop for Phase 8.

    This class never posts externally. It prepares review records, stores manual
    publish logs, accepts revenue data, and writes feedback for the next mission.
    """

    def __init__(self, path: str | Path = PHASE8_PATH, *, content_manager: ContentFactoryManager | None = None) -> None:
        self.path = Path(path)
        self.content_manager = content_manager or ContentFactoryManager()
        self.approval = ApprovalManager()

    def load_state(self) -> dict[str, Any]:
        if not self.path.exists():
            state = _default_state()
            self.save_state(state)
            return state
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            data = _default_state()
        if not isinstance(data, dict):
            data = _default_state()
        defaults = _default_state()
        for key, value in defaults.items():
            data.setdefault(key, value)
        return data

    def save_state(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state["updated_at"] = _now()
        save_json_atomic(self.path, state)

    def sync_from_latest_mission(self) -> list[dict[str, Any]]:
        mission = self.content_manager.load_state().get("last_phase7_mission", {})
        if not mission:
            return []
        state = self.load_state()
        existing = {item.get("review_id") for item in state.get("review_items", [])}
        items = []
        for content in mission.get("contents", []):
            media = "Website" if content.get("type") == "official_site_article" else str(content.get("type", "")).title()
            review_id = f"rev8-{mission.get('run_id', '')}-{content.get('content_id', '')}"
            if review_id in existing:
                continue
            item = {
                "review_id": review_id,
                "run_id": mission.get("run_id", ""),
                "content_id": content.get("content_id", ""),
                "media": media,
                "topic": mission.get("topic", ""),
                "title": content.get("title", ""),
                "status": "pending_review",
                "reviewer": "",
                "review_notes": "",
                "content": content,
                "related_files": [draft.get("path", "") for draft in mission.get("drafts", []) if draft.get("content_id") == content.get("content_id")],
                "seo": content.get("seo", {}),
                "cta": content.get("cta", ""),
                "created_at": _now(),
                "updated_at": _now(),
            }
            item["risk_review"] = self.approval.review({"content": content})
            items.append(item)
        state.setdefault("review_items", [])
        state["review_items"] = items + state["review_items"]
        state["review_items"] = state["review_items"][:200]
        self.save_state(state)
        return items

    def review_item(self, review_id: str, *, action: str, reviewer: str = "human", notes: str = "") -> dict[str, Any] | None:
        state = self.load_state()
        target = next((item for item in state.get("review_items", []) if item.get("review_id") == review_id), None)
        if not target:
            return None
        target["reviewer"] = reviewer
        target["review_notes"] = notes
        target["updated_at"] = _now()
        if action == "approve":
            target["status"] = "approved"
            target["approved_at"] = _now()
        else:
            target["status"] = "revision_requested"
            target["revision_requested_at"] = _now()
        self.save_state(state)
        return target

    def mark_published(
        self,
        review_id: str,
        *,
        reviewer: str = "human",
        published_url: str = "",
        status: str = "published_manual",
    ) -> dict[str, Any] | None:
        state = self.load_state()
        item = next((row for row in state.get("review_items", []) if row.get("review_id") == review_id), None)
        if not item or item.get("status") != "approved":
            return None
        log = {
            "log_id": f"plog-{uuid4().hex[:10]}",
            "review_id": review_id,
            "run_id": item.get("run_id", ""),
            "published_at": _now(),
            "media": item.get("media", ""),
            "topic": item.get("topic", ""),
            "status": status,
            "reviewer": reviewer,
            "published_url": published_url,
            "related_files": item.get("related_files", []),
            "content_id": item.get("content_id", ""),
            "title": item.get("title", ""),
            "external_api_sent": False,
            "manual_publish": True,
        }
        item["status"] = status
        item["published_at"] = log["published_at"]
        item["published_url"] = published_url
        state.setdefault("publish_logs", []).insert(0, log)
        state["publish_logs"] = state["publish_logs"][:500]
        self.save_state(state)
        return log

    def record_revenue_data(
        self,
        *,
        media: str,
        topic: str,
        pv: int = 0,
        impressions: int = 0,
        ctr: float = 0,
        clicks: int = 0,
        follower_growth: int = 0,
        cv: int = 0,
        revenue: int = 0,
    ) -> dict[str, Any]:
        state = self.load_state()
        row = {
            "record_id": f"revtrack-{uuid4().hex[:10]}",
            "date": date.today().isoformat(),
            "media": media,
            "topic": topic,
            "pv": int(pv or 0),
            "impressions": int(impressions or 0),
            "ctr": float(ctr or 0),
            "clicks": int(clicks or 0),
            "follower_growth": int(follower_growth or 0),
            "cv": int(cv or 0),
            "revenue": int(revenue or 0),
            "created_at": _now(),
        }
        state.setdefault("revenue_tracking", []).insert(0, row)
        state["revenue_tracking"] = state["revenue_tracking"][:500]
        feedback = self.generate_feedback(state["revenue_tracking"])
        state["last_feedback"] = feedback
        state.setdefault("feedback_history", []).insert(0, feedback)
        state["feedback_history"] = state["feedback_history"][:100]
        self.save_state(state)
        return row

    def generate_feedback(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        recent = rows[:30]
        best = max(recent, key=lambda row: (int(row.get("revenue", 0)), int(row.get("clicks", 0)), int(row.get("pv", 0))), default={})
        avg_ctr = sum(float(row.get("ctr", 0) or 0) for row in recent) / max(len(recent), 1)
        total_revenue = sum(int(row.get("revenue", 0) or 0) for row in recent)
        note_title = "AIOS初収益までの実測ログ"
        threads_focus = "ctr" if avg_ctr < 0.03 else "follower"
        cta = "実測データつきのAIOS運用記録を次回も確認する"
        seo = "AIOS 初収益 note Threads 公式サイト 運用記録"
        if best:
            note_title = f"{best.get('topic', 'AIOS')}の勝ちパターン分析"
            cta = f"{best.get('media', 'AIOS')}で反応が出た導線を次の記事で深掘りする"
        return {
            "feedback_id": f"fb-{uuid4().hex[:10]}",
            "source": "phase8_feedback_engine",
            "total_revenue": total_revenue,
            "average_ctr": round(avg_ctr, 4),
            "best_pattern": best,
            "next_note_title": note_title,
            "next_threads_focus": threads_focus,
            "next_cta": cta,
            "next_seo_keywords": seo,
            "created_at": _now(),
        }

    def generate_weekly_report(self) -> dict[str, Any]:
        state = self.load_state()
        today = date.today()
        start = today - timedelta(days=6)
        rows = [
            row for row in state.get("revenue_tracking", [])
            if start.isoformat() <= str(row.get("date", "")) <= today.isoformat()
        ]
        logs = [
            row for row in state.get("publish_logs", [])
            if str(row.get("published_at", ""))[:10] >= start.isoformat()
        ]
        total_revenue = sum(int(row.get("revenue", 0) or 0) for row in rows)
        total_clicks = sum(int(row.get("clicks", 0) or 0) for row in rows)
        best = max(rows, key=lambda row: (int(row.get("revenue", 0)), int(row.get("clicks", 0))), default={})
        report = {
            "report_id": f"wrep-{uuid4().hex[:10]}",
            "week_start": start.isoformat(),
            "week_end": today.isoformat(),
            "results": {
                "publish_count": len(logs),
                "revenue": total_revenue,
                "clicks": total_clicks,
                "pv": sum(int(row.get("pv", 0) or 0) for row in rows),
                "impressions": sum(int(row.get("impressions", 0) or 0) for row in rows),
            },
            "improvements": [
                "CTRが低い媒体はThreads文頭とCTAを短くする",
                "PVが低い日は公式サイトMarkdownの検索意図を強める",
            ],
            "winning_pattern": best,
            "next_week_actions": [
                "勝ち媒体のタイトル構造をnoteへ横展開",
                "Threads 3パターンのうちCTR勝ち案を翌日の基準にする",
                "Website記事にnoteへの内部リンクを追加する",
            ],
            "created_at": _now(),
        }
        state.setdefault("weekly_reports", []).insert(0, report)
        state["weekly_reports"] = state["weekly_reports"][:52]
        self.save_state(state)
        return report
