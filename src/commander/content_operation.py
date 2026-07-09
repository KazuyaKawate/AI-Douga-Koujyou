from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


CONTENT_QUEUE_STATUSES = {"draft", "review_required", "approved", "scheduled", "published", "failed", "rejected"}
CHANNELS = {"note", "threads", "official_line", "website"}
FORBIDDEN_CONTENT = (
    "live publish",
    "live send",
    "api key",
    "secret",
    "必ず儲かる",
    "絶対に稼げる",
    "断定します",
    "治ります",
    "法律上問題ない",
    "的中保証",
    "個人情報",
)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ContentSafetyGuard:
    def evaluate(self, item: dict[str, Any], *, publish: bool = False, send: bool = False) -> dict[str, Any]:
        text = " ".join(str(item.get(key, "")) for key in ("title", "body", "cta", "target", "review_notes")).lower()
        findings = []
        for token in FORBIDDEN_CONTENT:
            if token.lower() in text:
                findings.append({"type": "forbidden_content", "message": token, "risk": "high"})
        if (publish or send) and item.get("status") != "approved":
            findings.append({"type": "approval_required", "message": "未承認投稿は禁止", "risk": "high"})
        if publish and item.get("channel") in {"note", "threads", "website"}:
            findings.append({"type": "publish_blocked", "message": "本番公開はReview→Approve後のpublish_ready生成まで", "risk": "medium"})
        if send and item.get("channel") == "official_line":
            findings.append({"type": "send_blocked", "message": "公式LINE自動送信は未実装。Draft/Reviewのみ", "risk": "medium"})
        return {"ok": not any(item["risk"] == "high" for item in findings), "findings": findings}


class ContentOperationEngine:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root)
        self.path = self.root / "config" / "commander_content_queue.json"
        self.guard = ContentSafetyGuard()

    def load(self) -> dict[str, Any]:
        data = load_json(self.path, default={}) or {}
        data.setdefault("queue", [])
        data.setdefault("updated_at", _now())
        return data

    def save(self, data: dict[str, Any]) -> None:
        data["updated_at"] = _now()
        save_json_atomic(self.path, data)

    def create_draft(self, *, channel: str, instruction: str, expected_revenue: int = 0, target: str = "初収益") -> dict[str, Any]:
        if channel not in CHANNELS:
            raise ValueError(f"Unsupported content channel: {channel}")
        item = self._draft(channel, instruction, expected_revenue, target)
        guard = self.guard.evaluate(item)
        item["safety"] = guard
        item["status"] = "review_required" if guard["ok"] else "rejected"
        data = self.load()
        data["queue"].insert(0, item)
        data["queue"] = data["queue"][:300]
        self.save(data)
        return item

    def approve(self, content_id: str, *, review_notes: str = "") -> dict[str, Any] | None:
        data = self.load()
        for item in data["queue"]:
            if item.get("content_id") == content_id and item.get("status") == "review_required":
                item["status"] = "approved"
                item["review_notes"] = review_notes
                item["approved_at"] = _now()
                item["publish_ready"] = item.get("channel") in {"note", "threads", "website"}
                item["send_ready"] = item.get("channel") == "official_line"
                self.save(data)
                return item
        return None

    def reject(self, content_id: str, *, review_notes: str = "") -> dict[str, Any] | None:
        data = self.load()
        for item in data["queue"]:
            if item.get("content_id") == content_id:
                item["status"] = "rejected"
                item["review_notes"] = review_notes
                item["updated_at"] = _now()
                self.save(data)
                return item
        return None

    def summary(self) -> dict[str, Any]:
        queue = self.load().get("queue", [])
        by_channel = {channel: [item for item in queue if item.get("channel") == channel] for channel in CHANNELS}
        pending = [item for item in queue if item.get("status") == "review_required"]
        approved = [item for item in queue if item.get("status") == "approved"]
        next_item = sorted(queue, key=lambda item: (-float(item.get("priority_score", 0)), item.get("created_at", "")))[0] if queue else None
        return {
            "queue": queue,
            "today_content_mission": next_item,
            "note_drafts": len([item for item in by_channel["note"] if item.get("status") in {"draft", "review_required"}]),
            "threads_drafts": len([item for item in by_channel["threads"] if item.get("status") in {"draft", "review_required"}]),
            "line_drafts": len([item for item in by_channel["official_line"] if item.get("status") in {"draft", "review_required"}]),
            "pending_review": pending,
            "approved_queue": approved,
            "revenue_cta": [item for item in queue if item.get("cta")],
            "next_best_action": next_item,
        }

    def _draft(self, channel: str, instruction: str, expected_revenue: int, target: str) -> dict[str, Any]:
        title = self._title(channel, instruction)
        body = self._body(channel, instruction)
        cta = self._cta(channel)
        priority_score = round((expected_revenue or self._default_revenue(channel)) / self._effort(channel), 2)
        return {
            "content_id": f"cnt-{uuid4().hex[:10]}",
            "channel": channel,
            "title": title,
            "body": body,
            "cta": cta,
            "target": target,
            "expected_revenue": expected_revenue or self._default_revenue(channel),
            "priority_score": priority_score,
            "publish_time": "",
            "review_notes": "",
            "result_url": "",
            "status": "draft",
            "publish_ready": False,
            "send_ready": False,
            "created_at": _now(),
            "updated_at": _now(),
        }

    @staticmethod
    def _title(channel: str, instruction: str) -> str:
        if channel == "note":
            return f"note案: {instruction[:40]}"
        if channel == "threads":
            return f"Threads連投案: {instruction[:36]}"
        if channel == "official_line":
            return f"LINE配信案: {instruction[:38]}"
        return f"Website改善案: {instruction[:36]}"

    @staticmethod
    def _body(channel: str, instruction: str) -> str:
        if channel == "note":
            return f"導入文: {instruction}\n有料導線: 実践手順とテンプレートを有料部分へ配置。"
        if channel == "threads":
            return f"1/ 問題提起: {instruction}\n2/ 解決策\n3/ note/LINE/公式サイトへの誘導"
        if channel == "official_line":
            return f"配信用メッセージ: {instruction}\nステップ配信: 友だち追加→価値提供→note販売導線"
        return f"公式サイト改善: {instruction}\nCTAと収益導線を明確化。"

    @staticmethod
    def _cta(channel: str) -> str:
        if channel == "note":
            return "続きを読む / 有料noteで実践手順を見る"
        if channel == "threads":
            return "詳しくはnote・公式LINE・公式サイトへ"
        if channel == "official_line":
            return "友だち追加後にnote特典を受け取る"
        return "無料相談 / note / LINEへ進む"

    @staticmethod
    def _default_revenue(channel: str) -> int:
        return {"note": 12000, "threads": 6000, "official_line": 10000, "website": 15000}.get(channel, 3000)

    @staticmethod
    def _effort(channel: str) -> float:
        return {"note": 3, "threads": 1, "official_line": 2, "website": 3}.get(channel, 2)
