from __future__ import annotations

import getpass
import logging
import os
from datetime import datetime
from typing import Any, Callable
from uuid import uuid4

from src.ai.router import AIRouter, get_router
from src.ai.task import AITask, TaskType
from src.revenue_engine.dashboard import RevenueEngineDashboard
from src.revenue_engine.note_draft_flow import RevenueNoteDraftFlow


logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ThreadsCredentials:
    def __init__(
        self,
        *,
        input_func: Callable[[str], str] = input,
        password_func: Callable[[str], str] = getpass.getpass,
    ) -> None:
        self.input_func = input_func
        self.password_func = password_func

    def read(self) -> dict[str, str]:
        email = os.getenv("THREADS_EMAIL", "").strip()
        password = os.getenv("THREADS_PASSWORD", "")
        if not email:
            email = self.input_func("THREADS_EMAIL: ").strip()
        if not password:
            password = self.password_func("THREADS_PASSWORD: ")
        return {"email": email, "password": password}


class RevenueThreadsDraftFlow:
    def __init__(
        self,
        *,
        dashboard: RevenueEngineDashboard | None = None,
        router: AIRouter | None = None,
        note_flow: RevenueNoteDraftFlow | None = None,
        credentials: ThreadsCredentials | None = None,
    ) -> None:
        self.dashboard = dashboard or RevenueEngineDashboard()
        self.router = router or get_router()
        self.note_flow = note_flow or RevenueNoteDraftFlow(dashboard=self.dashboard, router=self.router)
        self.credentials = credentials or ThreadsCredentials()

    def run(self, *, theme: str | None = None, dry_run: bool = True) -> dict[str, Any]:
        if not dry_run:
            logger.error("Threads live posting is prohibited; dry_run must be true.")
            return {"status": "failed", "stage": "dry_run_guard", "error": "Threads live posting is prohibited.", "dry_run": False}

        try:
            credentials = self.credentials.read()
        except Exception as exc:
            logger.exception("Threads credential input failed.")
            return {"status": "failed", "stage": "credentials", "error": str(exc), "dry_run": True}

        credentials_configured = bool(credentials.get("email") and credentials.get("password"))
        if not credentials_configured:
            logger.error("Threads credentials are not configured.")
            return {"status": "failed", "stage": "credentials", "error": "Threads credentials are not configured.", "dry_run": True}

        note_result = self.note_flow.run(theme=theme, dry_run=True)
        if note_result.get("status") != "success":
            logger.error("note draft step failed before Threads waiting registration: %s", note_result.get("stage", "unknown"))
            return {"status": "failed", "stage": "note_draft", "note_result": note_result, "dry_run": True}

        threads_post = self.generate_threads_post(note_result)
        if not threads_post.get("text"):
            message = str(threads_post.get("error") or "Threads post generation returned empty text.")
            logger.error("Threads post generation failed: %s", message)
            return {"status": "failed", "stage": "threads_generation", "error": message, "dry_run": True}

        waiting = self.dashboard.record_threads_waiting_post(
            {
                "waiting_id": f"thrwait-{uuid4().hex[:10]}",
                "source": "note_draft",
                "note_theme": note_result.get("theme", ""),
                "note_title": note_result.get("article", {}).get("title", ""),
                "note_save_url": note_result.get("save_url", ""),
                "text": threads_post.get("text", ""),
                "credentials_configured": credentials_configured,
                "created_at": _now(),
            }
        )
        return {
            "status": "success",
            "note_result": note_result,
            "threads_post": threads_post,
            "dashboard_record": waiting,
            "dry_run": True,
            "credentials_configured": credentials_configured,
        }

    def generate_threads_post(self, note_result: dict[str, Any]) -> dict[str, Any]:
        article = note_result.get("article", {})
        prompt = (
            "note下書きからThreads投稿文を1本生成してください。\n"
            f"タイトル: {article.get('title', '')}\n"
            f"保存URL: {note_result.get('save_url', '')}\n"
            f"本文:\n{article.get('body', '')[:1800]}\n\n"
            "条件:\n"
            "- 300〜500文字\n"
            "- note下書きへの導線を自然に入れる\n"
            "- 投稿文のみ出力\n"
        )
        response = self.router.route(
            AITask(
                task_type=TaskType.WRITING,
                prompt=prompt,
                system_prompt="あなたはThreads向けにnote導線を作るSNS編集者です。",
                options={"channel": "threads", "source": "note_draft"},
            )
        )
        if not response.ok:
            return {"text": "", "error": response.error or "Threads generation failed"}
        return {
            "text": response.content.strip()[:500],
            "ai_provider": response.provider,
            "ai_model": response.model,
        }
