from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from src.ai.router import AIRouter, get_router
from src.ai.task import AITask, TaskType
from src.publish_engine.note_publisher import NotePublisher
from src.revenue_engine.dashboard import RevenueEngineDashboard


logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RevenueNoteDraftFlow:
    def __init__(
        self,
        *,
        dashboard: RevenueEngineDashboard | None = None,
        router: AIRouter | None = None,
        publisher: NotePublisher | None = None,
    ) -> None:
        self.dashboard = dashboard or RevenueEngineDashboard()
        self.router = router or get_router()
        self.publisher = publisher or NotePublisher()

    def run(self, *, theme: str | None = None, dry_run: bool = True) -> dict[str, Any]:
        theme = (theme or self.get_theme_from_revenue_engine()).strip()
        if not theme:
            message = "Revenue Engine note theme was not found."
            logger.error(message)
            return {"status": "failed", "stage": "theme", "error": message, "dry_run": dry_run}

        article = self.generate_article(theme)
        if not article.get("body"):
            message = str(article.get("error") or "AI article generation returned empty body.")
            logger.error("note draft flow generation failed: %s", message)
            return {"status": "failed", "stage": "article_generation", "error": message, "theme": theme, "dry_run": dry_run}

        item = self._publish_item(theme, article)
        try:
            save_result = self.publisher.publish(item, dry_run=dry_run)
        except Exception as exc:
            logger.exception("note draft save failed without retry: %s", exc)
            return {
                "status": "failed",
                "stage": "draft_save",
                "error": str(exc),
                "theme": theme,
                "content_id": item.get("content_id", ""),
                "dry_run": dry_run,
            }

        if not self._save_succeeded(save_result):
            logger.error("note draft save failed without retry: %s", save_result)
            return {
                "status": "failed",
                "stage": "draft_save",
                "error": str(save_result.get("error") or save_result.get("status") or "unknown"),
                "theme": theme,
                "content_id": item.get("content_id", ""),
                "save_result": save_result,
                "dry_run": dry_run,
            }

        save_url = self._save_url(save_result, dry_run=dry_run)
        dashboard_record = self.dashboard.record_note_draft_save(
            {
                "flow_id": f"rnd-{uuid4().hex[:10]}",
                "theme": theme,
                "title": article.get("title", ""),
                "content_id": item.get("content_id", ""),
                "publish_id": item.get("publish_id", ""),
                "save_url": save_url,
                "save_result": save_result,
                "ai_provider": article.get("ai_provider", ""),
                "ai_model": article.get("ai_model", ""),
                "dry_run": dry_run,
                "created_at": _now(),
            }
        )
        return {
            "status": "success",
            "theme": theme,
            "article": article,
            "save_result": save_result,
            "save_url": save_url,
            "dashboard_record": dashboard_record,
            "dry_run": dry_run,
        }

    def get_theme_from_revenue_engine(self) -> str:
        ranked = self.dashboard.opportunities.generate()
        note_queue = self.dashboard.channel_queues(ranked).get("note", [])
        if not note_queue:
            return ""
        selected = note_queue[0]
        return str(selected.get("title") or selected.get("article_angle") or "").strip()

    def generate_article(self, theme: str) -> dict[str, Any]:
        prompt = (
            "note下書き用の記事をMarkdownで生成してください。\n"
            f"トピック: {theme}\n"
            "条件:\n"
            "- 読者が今日から実行できる具体策を入れる\n"
            "- 収益化導線を自然に入れる\n"
            "- 最初の行は # から始まるタイトルにする\n"
            "- 公開ではなく下書き保存用の完成記事にする\n"
        )
        response = self.router.route(
            AITask(
                task_type=TaskType.WRITING,
                prompt=prompt,
                system_prompt="あなたはnote向けの収益化記事を書く編集者です。",
                options={"channel": "note", "theme": theme},
            )
        )
        if not response.ok:
            return {"title": "", "body": "", "error": response.error or "AI generation failed"}
        body = response.content.strip()
        return {
            "content_id": f"note-ai-{uuid4().hex[:10]}",
            "type": "note",
            "topic": theme,
            "title": self._title_from_markdown(body, theme),
            "body": body,
            "tags": [theme, "AIOS", "収益化"],
            "estimated_revenue": 20000,
            "status": "draft",
            "ai_provider": response.provider,
            "ai_model": response.model,
        }

    @staticmethod
    def _publish_item(theme: str, article: dict[str, Any]) -> dict[str, Any]:
        now = _now()
        return {
            "publish_id": f"pub-{uuid4().hex[:10]}",
            "content_id": article.get("content_id", ""),
            "platform": "note",
            "status": "draft",
            "priority": 90,
            "content": article,
            "attempts": 0,
            "max_attempts": 1,
            "scheduled_for": "",
            "review": {"status": "approved", "source": "revenue_note_draft_flow"},
            "approval": {},
            "publish_result": {},
            "analytics": {},
            "theme": theme,
            "created_at": now,
            "updated_at": now,
        }

    @staticmethod
    def _title_from_markdown(body: str, fallback: str) -> str:
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return f"{fallback}で初収益を狙う方法"

    @staticmethod
    def _save_succeeded(result: dict[str, Any]) -> bool:
        return result.get("status") in {"dry_run", "published", "draft_saved", "success"}

    @staticmethod
    def _save_url(result: dict[str, Any], *, dry_run: bool) -> str:
        for key in ("save_url", "draft_url", "edit_url", "url"):
            value = result.get(key)
            if value:
                return str(value)
        external_id = str(result.get("external_id") or "")
        if dry_run:
            return f"dryrun://note/{external_id or uuid4().hex[:10]}"
        if external_id:
            return f"https://note.com/notes/{external_id}"
        return ""
