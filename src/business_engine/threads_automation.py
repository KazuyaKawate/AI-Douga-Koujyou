from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from typing import Any
from urllib import error, parse, request

from src.business_engine.manager import BusinessEngineStore, _new_id
from src.self_builder.knowledge_manager import load_knowledge, save_knowledge


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ThreadsAutomation:
    """Local-first Threads automation connected to Phase6 note operations."""

    def __init__(self, store: BusinessEngineStore | None = None) -> None:
        self.store = store or BusinessEngineStore()

    def generate_from_note(self, article_id: str) -> dict[str, Any] | None:
        data = self.store.load()
        article = self._find_article(data, article_id)
        if article is None:
            return None
        summary = self.summarize_note(article)
        cta = self.generate_cta(article)
        hashtags = self.generate_hashtags(article)
        text = self.generate_threads_text(article, summary, cta, hashtags)
        if self._is_duplicate(data, article_id, text):
            return {
                "thread_id": "",
                "article_id": article_id,
                "status": "duplicate_blocked",
                "reason": "同一note記事または同一本文のThreads投稿が既に存在します。",
            }
        thread = {
            "thread_id": _new_id("thread"),
            "platform": "threads",
            "article_id": article_id,
            "source_id": article_id,
            "topic": article.get("topic", ""),
            "title": article.get("title", ""),
            "summary": summary,
            "cta": cta,
            "hashtags": hashtags,
            "text": text,
            "image_prompt": self.image_prompt_for_article(article),
            "asset_ref": self.asset_ref_for_article(article),
            "status": "draft",
            "dry_run": True,
            "reaction_rate": 0,
            "ctr": 0,
            "click_rate": 0,
            "pv": 0,
            "created_at": _now(),
            "updated_at": _now(),
        }
        data.setdefault("post_queue", []).insert(0, thread)
        self.store.save(data)
        self.save_threads_knowledge(thread, event="generated")
        self.feedback_research_team(thread)
        self.return_improvement_to_mission_planner(thread)
        return thread

    def summarize_note(self, article: dict[str, Any]) -> str:
        body = str(article.get("body", ""))
        lines = [
            line.strip(" -0123456789.、")
            for line in body.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        summary = " ".join(lines[:3]) or article.get("title", "")
        return summary[:240]

    def generate_threads_text(
        self,
        article: dict[str, Any],
        summary: str,
        cta: str,
        hashtags: list[str],
    ) -> str:
        title = article.get("title", "")
        return f"{title}\n\n{summary}\n\n{cta}\n\n{' '.join(hashtags)}"[:500]

    def generate_cta(self, article: dict[str, Any]) -> str:
        keyword = article.get("keyword") or (article.get("keywords") or ["AIOS"])[0]
        return f"{keyword}の運用を小さく始めたい人は、まずnote本文の流れを1つだけ試してください。"

    def generate_hashtags(self, article: dict[str, Any]) -> list[str]:
        source = " ".join([article.get("title", ""), article.get("topic", ""), " ".join(article.get("keywords", []))]).lower()
        tags = ["#AIOS", "#Threads", "#note"]
        if "business" in source or "収益" in source:
            tags.append("#収益化")
        if "automation" in source or "自動" in source:
            tags.append("#自動化")
        return tags[:5]

    def image_prompt_for_article(self, article: dict[str, Any]) -> str:
        prompts = article.get("image_prompts", {})
        return prompts.get("thumbnail") or prompts.get("eyecatch") or f"Threads visual for {article.get('title', '')}"

    def asset_ref_for_article(self, article: dict[str, Any]) -> dict[str, Any]:
        eyecatch = article.get("eyecatch", {})
        return {
            "source": "phase6_note",
            "asset_id": eyecatch.get("asset_id", ""),
            "path": eyecatch.get("path", ""),
            "prompt": eyecatch.get("prompt", self.image_prompt_for_article(article)),
        }

    def reserve_thread(self, thread_id: str, scheduled_for: str | None = None) -> dict[str, Any] | None:
        data = self.store.load()
        thread = self._find_thread(data, thread_id)
        if thread is None:
            return None
        if self._is_duplicate(data, thread.get("article_id", ""), thread.get("text", ""), exclude_thread_id=thread_id):
            thread["status"] = "duplicate_blocked"
            thread["updated_at"] = _now()
            self.store.save(data)
            return thread
        scheduled_at = scheduled_for or (date.today() + timedelta(days=1)).isoformat()
        reservation = {
            "reservation_id": _new_id("thread_res"),
            "thread_id": thread_id,
            "article_id": thread.get("article_id", ""),
            "title": thread.get("title", ""),
            "scheduled_for": scheduled_at,
            "status": "reserved",
            "dry_run": True,
            "created_at": _now(),
            "updated_at": _now(),
        }
        data.setdefault("threads_reservations", []).insert(0, reservation)
        thread["status"] = "reserved"
        thread["scheduled_for"] = scheduled_at
        thread["reservation_id"] = reservation["reservation_id"]
        thread["updated_at"] = _now()
        self.store.save(data)
        self.store.schedule_job(
            "sns_post",
            f"Threads post: {thread.get('title', '')}",
            scheduled_at,
            payload={"thread_id": thread_id, "article_id": thread.get("article_id", ""), "platform": "threads", "use_workflow": False},
        )
        return reservation

    def publish_thread(self, thread_id: str, *, dry_run: bool | None = None) -> dict[str, Any] | None:
        data = self.store.load()
        thread = self._find_thread(data, thread_id)
        if thread is None:
            return None
        api_result = self._threads_api(thread, dry_run=dry_run)
        status = "dry_run" if api_result.get("dry_run") else "published"
        thread["status"] = status
        thread["dry_run"] = bool(api_result.get("dry_run"))
        thread["published_at"] = _now()
        thread["api_result"] = api_result
        thread["updated_at"] = _now()
        history = self._history_item(thread, status)
        data.setdefault("threads_history", []).insert(0, history)
        for reservation in data.setdefault("threads_reservations", []):
            if reservation.get("thread_id") == thread_id and reservation.get("status") == "reserved":
                reservation["status"] = status
                reservation["updated_at"] = _now()
        self.store.save(data)
        self.store.record_execution(thread_id, "completed", f"Threads {status} completed.")
        self.save_threads_knowledge(thread, event=status)
        self.feedback_research_team(thread)
        self.return_improvement_to_mission_planner(thread)
        return thread

    def fetch_thread_metrics(
        self,
        thread_id: str,
        *,
        pv: int | None = None,
        ctr: float | None = None,
        reaction_rate: float | None = None,
        click_rate: float | None = None,
    ) -> dict[str, Any] | None:
        data = self.store.load()
        thread = self._find_thread(data, thread_id)
        if thread is None:
            return None
        if pv is None:
            pv = max(20, len(thread.get("text", "")) * 2)
        if ctr is None:
            ctr = 0.04
        if reaction_rate is None:
            reaction_rate = 0.06
        if click_rate is None:
            click_rate = ctr
        thread["pv"] = int(pv)
        thread["ctr"] = float(ctr)
        thread["reaction_rate"] = float(reaction_rate)
        thread["click_rate"] = float(click_rate)
        thread["metrics_updated_at"] = _now()
        thread["updated_at"] = _now()
        improvement = self._improvement(thread)
        data.setdefault("threads_improvements", []).insert(0, improvement)
        self.store.save(data)
        self.save_threads_knowledge(thread, event="metrics")
        self.feedback_research_team(thread)
        self.return_improvement_to_mission_planner(thread)
        return thread

    def dashboard_summary(self) -> dict[str, Any]:
        data = self.store.load()
        threads = [post for post in data.get("post_queue", []) if post.get("platform") == "threads"]
        ctr_values = [float(post.get("ctr", 0)) for post in threads if float(post.get("ctr", 0)) > 0]
        reaction_values = [float(post.get("reaction_rate", 0)) for post in threads if float(post.get("reaction_rate", 0)) > 0]
        config = self.production_status()
        return {
            "queue": len([post for post in threads if post.get("status") in ("draft", "reserved", "scheduled")]),
            "reservations": len([row for row in data.get("threads_reservations", []) if row.get("status") == "reserved"]),
            "history": len(data.get("threads_history", [])),
            "dry_run": config["dry_run"],
            "production_ready": config["production_ready"],
            "reaction_rate": round(sum(reaction_values) / max(len(reaction_values), 1), 4),
            "ctr": round(sum(ctr_values) / max(len(ctr_values), 1), 4),
            "improvements": len(data.get("threads_improvements", [])),
        }

    def production_status(self) -> dict[str, Any]:
        data = self.store.load()
        enabled = bool(data.get("meta", {}).get("external_apis_enabled", False))
        configured = bool(os.getenv("THREADS_ACCESS_TOKEN", "").strip() and os.getenv("THREADS_USER_ID", "").strip())
        return {
            "production_ready": enabled and configured,
            "dry_run": not (enabled and configured),
            "external_apis_enabled": enabled,
            "configured": configured,
        }

    def save_threads_knowledge(self, thread: dict[str, Any], event: str = "generated") -> dict[str, Any]:
        knowledge = load_knowledge()
        record = {
            "history_id": _new_id("hist"),
            "type": "threads_automation",
            "event": event,
            "thread_id": thread.get("thread_id", ""),
            "article_id": thread.get("article_id", ""),
            "title": thread.get("title", ""),
            "ctr": thread.get("ctr", 0),
            "reaction_rate": thread.get("reaction_rate", 0),
            "click_rate": thread.get("click_rate", 0),
            "created_at": _now(),
        }
        knowledge.setdefault("history", []).insert(0, record)
        knowledge.setdefault("improvement_examples", []).insert(0, record)
        save_knowledge(knowledge)
        return record

    def feedback_research_team(self, thread: dict[str, Any]) -> dict[str, Any]:
        feedback = {
            "feedback_id": _new_id("research_fb"),
            "receiver": "Research Team",
            "source": "threads_automation",
            "thread_id": thread.get("thread_id", ""),
            "article_id": thread.get("article_id", ""),
            "reaction_rate": thread.get("reaction_rate", 0),
            "ctr": thread.get("ctr", 0),
            "message": "Threads反応を次回Topic Researchと投稿仮説へ反映",
            "created_at": _now(),
        }
        data = self.store.load()
        data.setdefault("research_feedback", []).insert(0, feedback)
        self.store.save(data)
        return feedback

    def return_improvement_to_mission_planner(self, thread: dict[str, Any]) -> dict[str, Any]:
        ctr = float(thread.get("ctr", 0))
        reaction = float(thread.get("reaction_rate", 0))
        feedback = {
            "feedback_id": _new_id("mission_fb"),
            "receiver": "Mission Planner",
            "source": "threads_automation",
            "status": "ready",
            "thread_id": thread.get("thread_id", ""),
            "improvement_tasks": [
                {
                    "title": f"Threads CTA改善: {thread.get('title', '')}",
                    "agent": "SNS Agent",
                    "priority": "high" if ctr < 0.03 else "normal",
                    "reason": f"CTR={ctr}, reaction_rate={reaction}",
                },
                {
                    "title": "note本文からThreads要約テンプレートを更新",
                    "agent": "Content Planner Agent",
                    "priority": "normal",
                    "reason": "投稿履歴と反応率をBusiness Engineへ戻す",
                },
            ],
            "returned_at": _now(),
        }
        data = self.store.load()
        data.setdefault("mission_planner_feedback", []).insert(0, feedback)
        self.store.save(data)
        return feedback

    def _threads_api(self, thread: dict[str, Any], *, dry_run: bool | None = None) -> dict[str, Any]:
        status = self.production_status()
        should_dry_run = status["dry_run"] if dry_run is None else bool(dry_run)
        if should_dry_run:
            return {"status": "dry_run", "dry_run": True, "text": thread.get("text", ""), "message": "Threads本番API未設定のためDryRun"}
        api_base = os.getenv("THREADS_API_BASE", "https://graph.threads.net/v1.0").rstrip("/")
        user_id = os.getenv("THREADS_USER_ID", "").strip()
        token = os.getenv("THREADS_ACCESS_TOKEN", "").strip()
        payload = parse.urlencode({"media_type": "TEXT", "text": thread.get("text", ""), "access_token": token}).encode("utf-8")
        try:
            create_req = request.Request(f"{api_base}/{user_id}/threads", data=payload, method="POST")
            with request.urlopen(create_req, timeout=30) as response:
                create_result = json.loads(response.read().decode("utf-8") or "{}")
            creation_id = create_result.get("id", "")
            publish_payload = parse.urlencode({"creation_id": creation_id, "access_token": token}).encode("utf-8")
            publish_req = request.Request(f"{api_base}/{user_id}/threads_publish", data=publish_payload, method="POST")
            with request.urlopen(publish_req, timeout=30) as response:
                publish_result = json.loads(response.read().decode("utf-8") or "{}")
            return {"status": "published", "dry_run": False, "create": create_result, "publish": publish_result}
        except (error.URLError, json.JSONDecodeError) as exc:
            return {"status": "failed", "dry_run": False, "message": str(exc)}

    def _is_duplicate(self, data: dict[str, Any], article_id: str, text: str, *, exclude_thread_id: str = "") -> bool:
        for post in data.get("post_queue", []):
            if post.get("platform") != "threads" or post.get("thread_id") == exclude_thread_id:
                continue
            if post.get("article_id") == article_id or post.get("text") == text:
                return True
        for row in data.get("threads_history", []):
            if row.get("article_id") == article_id or row.get("text") == text:
                return True
        return False

    def _find_article(self, data: dict[str, Any], article_id: str) -> dict[str, Any] | None:
        return next((row for row in data.get("article_queue", []) if row.get("article_id") == article_id), None)

    def _find_thread(self, data: dict[str, Any], thread_id: str) -> dict[str, Any] | None:
        return next((row for row in data.get("post_queue", []) if row.get("thread_id") == thread_id), None)

    def _history_item(self, thread: dict[str, Any], status: str) -> dict[str, Any]:
        return {
            "history_id": _new_id("thread_hist"),
            "thread_id": thread.get("thread_id", ""),
            "article_id": thread.get("article_id", ""),
            "title": thread.get("title", ""),
            "text": thread.get("text", ""),
            "status": status,
            "dry_run": thread.get("dry_run", True),
            "published_at": thread.get("published_at", _now()),
            "ctr": thread.get("ctr", 0),
            "reaction_rate": thread.get("reaction_rate", 0),
            "click_rate": thread.get("click_rate", 0),
            "created_at": _now(),
        }

    def _improvement(self, thread: dict[str, Any]) -> dict[str, Any]:
        ctr = float(thread.get("ctr", 0))
        reaction = float(thread.get("reaction_rate", 0))
        suggestions = []
        if ctr < 0.03:
            suggestions.append("CTAを短くし、noteへの導線を先頭側へ移動する")
        if reaction < 0.05:
            suggestions.append("冒頭に読者の痛みを入れて返信しやすくする")
        if not suggestions:
            suggestions.append("反応が良いため同テーマで次投稿を予約する")
        return {
            "improvement_id": _new_id("thread_imp"),
            "thread_id": thread.get("thread_id", ""),
            "ctr": ctr,
            "reaction_rate": reaction,
            "click_rate": thread.get("click_rate", 0),
            "suggestions": suggestions,
            "created_at": _now(),
        }
