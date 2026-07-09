from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.business_engine.manager import BusinessEngineStore
from src.content_factory.ab_testing import ABTesting
from src.content_factory.affiliate_writer import AffiliateWriter
from src.content_factory.analytics import ContentAnalytics
from src.content_factory.fortune_engine import FortuneEngine
from src.content_factory.image_prompt_builder import ImagePromptBuilder
from src.content_factory.landing_page_builder import LandingPageBuilder
from src.content_factory.note_builder import NoteBuilder
from src.content_factory.quality_reviewer import QualityReviewer
from src.content_factory.scheduler import ContentScheduler
from src.content_factory.seo_optimizer import SEOOptimizer
from src.content_factory.threads_builder import ThreadsBuilder
from src.content_factory.youtube_summary import YouTubeSummary
from src.core.development_constitution import development_review, evaluate_constitution_compliance, record_improvement
from src.revenue_engine.dashboard import RevenueEngineDashboard
from src.self_builder.knowledge_manager import load_knowledge, save_knowledge
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import save_json_atomic


CONTENT_FACTORY_PATH = PROJECT_ROOT / "config" / "content_factory.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_state() -> dict[str, Any]:
    return {
        "enabled": True,
        "mission": "first_revenue_content_generation",
        "local_first": True,
        "dry_run": True,
        "content_ideas": [],
        "content_queue": [],
        "categories": [
            {"category_id": "cat-note", "name": "note", "priority": "high"},
            {"category_id": "cat-threads", "name": "threads", "priority": "high"},
            {"category_id": "cat-official", "name": "official_site", "priority": "normal"},
        ],
        "drafts": [],
        "history": [],
        "contents": [],
        "schedule": [],
        "analytics": {},
        "ab_tests": [],
        "quality_reviews": [],
        "business_feedback": [],
        "revenue_feedback": [],
        "coding_feedback": [],
        "knowledge_history": [],
        "last_run": {},
        "updated_at": _now(),
    }


class ContentFactoryManager:
    def __init__(self, path: str | Path = CONTENT_FACTORY_PATH) -> None:
        self.path = Path(path)
        self.business_store = BusinessEngineStore()

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

    # Content Engine Phase1 ------------------------------------------

    def add_content_idea(
        self,
        topic: str,
        *,
        category: str = "note",
        tags: list[str] | None = None,
        source: str = "manual",
        priority: str = "normal",
    ) -> dict[str, Any]:
        idea = {
            "idea_id": f"idea-{uuid4().hex[:10]}",
            "topic": topic.strip() or "AIOS収益化コンテンツ",
            "category": category,
            "tags": tags or self.generate_tags(topic),
            "source": source,
            "priority": priority,
            "status": "idea",
            "created_at": _now(),
            "updated_at": _now(),
        }
        state = self.load_state()
        state.setdefault("content_ideas", []).insert(0, idea)
        state["content_ideas"] = state["content_ideas"][:300]
        self.save_state(state)
        return idea

    def queue_content(self, idea_id: str, content_type: str, priority: str | None = None) -> dict[str, Any] | None:
        state = self.load_state()
        idea = next((row for row in state.get("content_ideas", []) if row.get("idea_id") == idea_id), None)
        if idea is None:
            return None
        adjusted = self.adjust_priority_by_business_kpi(priority or idea.get("priority", "normal"), content_type)
        queue_item = {
            "queue_id": f"queue-{uuid4().hex[:10]}",
            "idea_id": idea_id,
            "topic": idea.get("topic", ""),
            "content_type": content_type,
            "category": idea.get("category", content_type),
            "tags": idea.get("tags", []),
            "priority": adjusted["priority"],
            "priority_reason": adjusted["reason"],
            "status": "queued",
            "created_at": _now(),
            "updated_at": _now(),
        }
        idea["status"] = "queued"
        idea["updated_at"] = _now()
        state.setdefault("content_queue", []).insert(0, queue_item)
        state["content_queue"] = sorted(
            state["content_queue"][:300],
            key=lambda row: {"urgent": 0, "high": 1, "normal": 2, "low": 3}.get(row.get("priority", "normal"), 2),
        )
        self.save_state(state)
        return queue_item

    def generate_phase1_content(self, topic: str = "", *, category: str = "revenue", target: str = "AIOS users") -> dict[str, Any]:
        selected_topic = topic.strip() or self._topic_from_business_kpi()
        idea = self.add_content_idea(
            selected_topic,
            category=category,
            tags=self.generate_tags(selected_topic),
            source="content_engine_phase1",
            priority="high",
        )
        queue_items = [
            self.queue_content(idea["idea_id"], "note"),
            self.queue_content(idea["idea_id"], "threads"),
            self.queue_content(idea["idea_id"], "official_site"),
        ]
        contents = [
            self.generate_note_article(selected_topic, target=target),
            self.generate_threads_post(selected_topic),
            self.generate_official_site_article(selected_topic, target=target),
        ]
        drafts = [self.save_draft(content) for content in contents]
        history = self.record_content_history("phase1_generated", contents, drafts)
        business_feedback = self.sync_phase1_to_business_engine(contents)

        state = self.load_state()
        state["contents"] = contents + state.get("contents", [])
        state["contents"] = state["contents"][:300]
        state.setdefault("drafts", [])
        for draft in reversed(drafts):
            state["drafts"].insert(0, draft)
        state["drafts"] = state["drafts"][:300]
        state["last_run"] = {
            "run_id": f"ce1-{uuid4().hex[:10]}",
            "phase": "Content Engine Phase1",
            "topic": selected_topic,
            "idea": idea,
            "queue": [item for item in queue_items if item],
            "contents": contents,
            "drafts": drafts,
            "history": history,
            "business_feedback": business_feedback,
            "dry_run": True,
            "local_first": True,
            "created_at": _now(),
        }
        self.save_state(state)
        return state["last_run"]

    def generate_title(self, topic: str, content_type: str = "note") -> str:
        prefix = {
            "note": "【保存版】",
            "threads": "今日から試す",
            "official_site": "AIOS実践ガイド",
        }.get(content_type, "AIOS")
        return f"{prefix}{topic}で毎日収益化コンテンツを作る方法"

    def generate_tags(self, topic: str) -> list[str]:
        seeds = [topic, "AIOS", "収益化", "note", "Threads", "公式サイト"]
        tags: list[str] = []
        for seed in seeds:
            clean = str(seed).replace("#", "").strip()
            if clean and clean not in tags:
                tags.append(clean)
        return tags[:8]

    def generate_note_article(self, topic: str, *, target: str = "AIOS users") -> dict[str, Any]:
        content = NoteBuilder().build(topic, template="seo", keywords=self.generate_tags(topic)[:4])
        content["title"] = self.generate_title(topic, "note")
        content["target"] = target
        content["category"] = "note"
        content["tags"] = self.generate_tags(topic)
        content["status"] = "draft"
        content["local_first"] = True
        return content

    def generate_threads_post(self, topic: str) -> dict[str, Any]:
        content = ThreadsBuilder().build(topic, genre="work")
        tags = [f"#{tag}" for tag in self.generate_tags(topic)[:5]]
        content["title"] = self.generate_title(topic, "threads")
        content["category"] = "threads"
        content["tags"] = tags
        content["text"] = f"{content['title']}\n\n{topic}は、ネタ管理、下書き、KPI改善までを1日1本で回すのが近道です。\n\n{' '.join(tags)}"[:500]
        content["status"] = "draft"
        content["local_first"] = True
        return content

    def generate_official_site_article(self, topic: str, *, target: str = "AIOS users") -> dict[str, Any]:
        title = self.generate_title(topic, "official_site")
        tags = self.generate_tags(topic)
        body = (
            f"# {title}\n\n"
            f"{target}向けに、{topic}を毎日生成して初収益へ近づける運用手順をまとめます。\n\n"
            "## 収益化導線\n"
            "note記事で深く説明し、Threadsで反応を集め、公式サイトで検索流入を受け止めます。\n\n"
            "## 今日やること\n"
            "記事ネタを1つ選び、下書きを保存し、PVとCTRを見て翌日の優先度を変えます。\n\n"
            "## KPIで改善する\n"
            "PVが低ければ公式サイト記事、CTRが低ければThreads、収益が低ければnoteのCTAを優先します。\n"
        )
        return {
            "content_id": f"site-{uuid4().hex[:10]}",
            "type": "official_site_article",
            "topic": topic,
            "title": title,
            "target": target,
            "category": "official_site",
            "tags": tags,
            "body": body,
            "seo": SEOOptimizer().optimize({"content_id": "official-site-draft", "title": title, "keywords": tags, "description": body[:120]}),
            "estimated_revenue": 15000,
            "status": "draft",
            "local_first": True,
        }

    def save_draft(self, content: dict[str, Any]) -> dict[str, Any]:
        draft_dir = self.path.parent / "content_drafts"
        draft_dir.mkdir(parents=True, exist_ok=True)
        content_id = str(content.get("content_id", f"draft-{uuid4().hex[:10]}"))
        suffix = ".md" if content.get("body") else ".txt"
        draft_path = draft_dir / f"{content_id}{suffix}"
        draft_body = content.get("body") or content.get("text") or json.dumps(content, ensure_ascii=False, indent=2)
        draft_path.write_text(str(draft_body), encoding="utf-8")
        return {
            "draft_id": f"draft-{uuid4().hex[:10]}",
            "content_id": content_id,
            "type": content.get("type", ""),
            "title": content.get("title", content.get("topic", "")),
            "path": str(draft_path),
            "status": "saved",
            "created_at": _now(),
        }

    def record_content_history(self, event: str, contents: list[dict[str, Any]], drafts: list[dict[str, Any]]) -> dict[str, Any]:
        record = {
            "history_id": f"hist-{uuid4().hex[:10]}",
            "event": event,
            "content_ids": [item.get("content_id", "") for item in contents],
            "draft_ids": [item.get("draft_id", "") for item in drafts],
            "created_at": _now(),
        }
        state = self.load_state()
        state.setdefault("history", []).insert(0, record)
        state["history"] = state["history"][:300]
        self.save_state(state)
        return record

    def adjust_priority_by_business_kpi(self, base_priority: str, content_type: str) -> dict[str, str]:
        try:
            dashboard = self.business_store.business_phase1_dashboard()
        except Exception:
            dashboard = {}
        ctr = float(dashboard.get("ctr", 0) or dashboard.get("click_rate", 0) or 0)
        pv = int(dashboard.get("pv", 0) or 0)
        actual_revenue = int(dashboard.get("actual_revenue", 0) or 0)
        priority = base_priority if base_priority in {"low", "normal", "high", "urgent"} else "normal"
        reason = "Business KPI is stable."
        if actual_revenue <= 0 and content_type == "note":
            priority, reason = "urgent", "初収益前のためnote記事とCTAを最優先"
        elif pv < 100 and content_type == "official_site":
            priority, reason = "high", "PV不足のため公式サイト記事を優先"
        elif ctr < 0.03 and content_type == "threads":
            priority, reason = "high", "CTR不足のためThreads導線を優先"
        return {"priority": priority, "reason": reason}

    def sync_phase1_to_business_engine(self, contents: list[dict[str, Any]]) -> dict[str, Any]:
        data = self.business_store.load()
        for content in contents:
            if content.get("type") == "note":
                data.setdefault("article_queue", []).insert(0, content)
            elif content.get("type") == "threads":
                data.setdefault("post_queue", []).insert(0, {"platform": "threads", **content})
            elif content.get("type") == "official_site_article":
                data.setdefault("content_automation_runs", []).insert(0, {
                    "source": "content_engine_phase1",
                    "type": "official_site_article",
                    "content": content,
                    "created_at": _now(),
                })
        feedback = {
            "source": "content_engine_phase1",
            "status": "drafts_saved",
            "content_count": len(contents),
            "dry_run": True,
            "local_first": True,
            "created_at": _now(),
        }
        data.setdefault("mission_planner_feedback", []).insert(0, feedback)
        today = date.today().isoformat()
        current_kpi = next((row for row in data.get("daily_kpis", []) if row.get("date") == today), {})
        self.business_store.save(data)
        self.business_store.record_daily_kpi(
            kpi_date=today,
            revenue=int(current_kpi.get("revenue", 0) or 0),
            articles=int(current_kpi.get("articles", 0) or 0) + sum(1 for item in contents if item.get("type") == "note"),
            sns_posts=int(current_kpi.get("sns_posts", 0) or 0) + sum(1 for item in contents if item.get("type") == "threads"),
            note_articles=int(current_kpi.get("note_articles", current_kpi.get("articles", 0)) or 0) + sum(1 for item in contents if item.get("type") == "note"),
            threads_posts=int(current_kpi.get("threads_posts", current_kpi.get("sns_posts", 0)) or 0) + sum(1 for item in contents if item.get("type") == "threads"),
            affiliate_clicks=int(current_kpi.get("affiliate_clicks", 0) or 0),
            pv=int(current_kpi.get("pv", 0) or 0),
            ctr=float(current_kpi.get("ctr", 0) or 0),
            cv=float(current_kpi.get("cv", 0) or 0),
            seo=int(current_kpi.get("seo", 0) or 0),
            roi=int(current_kpi.get("roi", 0) or 0),
            notes="Content Engine Phase1 drafts generated",
        )
        return feedback

    def _topic_from_business_kpi(self) -> str:
        try:
            dashboard = self.business_store.business_phase1_dashboard()
        except Exception:
            return "AIOS初収益ロードマップ"
        if int(dashboard.get("pv", 0) or 0) < 100:
            return "AIOS公式サイトでPVを増やす方法"
        if float(dashboard.get("ctr", 0) or 0) < 0.03:
            return "Threadsからnoteへクリックを増やす方法"
        return "AIOS毎日収益化コンテンツ運用"

    def generate_daily_pack(
        self,
        *,
        topic: str = "Threads占いで初収益",
        youtube_url: str = "",
        transcript: str = "",
    ) -> dict[str, Any]:
        note = NoteBuilder().build(topic, template="seo", keywords=[topic, "Threads", "占い", "note"])
        threads = ThreadsBuilder().build(topic, genre="fortune")
        fortune = FortuneEngine().daily()
        youtube = YouTubeSummary().summarize(youtube_url or "https://youtube.com/example", transcript or "AI活用で収益化するには、発信と導線設計と改善が重要です。")
        affiliate = AffiliateWriter().build("AIツール紹介")
        landing = LandingPageBuilder().build("AIOS収益コンテンツ生成")
        contents = [note, threads, fortune, youtube, affiliate, landing]

        seo = {item.get("content_id", ""): SEOOptimizer().optimize(item) for item in contents if item.get("type") in {"note", "landing_page", "youtube_summary"}}
        image_prompts = {item.get("content_id", ""): ImagePromptBuilder().build(item) for item in contents}
        reviews = [QualityReviewer().review(item) for item in contents]
        schedule = ContentScheduler().schedule(contents, cadence="daily")
        ab_tests = [ABTesting().create(item) for item in contents if item.get("type") in {"note", "threads", "landing_page", "affiliate"}]
        analytics = ContentAnalytics().summarize(contents)
        knowledge = self.save_knowledge(contents, schedule, analytics, reviews)
        business_feedback = self.send_to_business_engine(contents, analytics)
        revenue_feedback = self.send_to_revenue_engine(contents, analytics)
        coding_feedback = self.send_to_coding_engine(contents, analytics)
        compliance = evaluate_constitution_compliance(
            {
                "instruction": "Content Factory generates revenue content for note Threads affiliate SEO ROI",
                "development_review": development_review({"instruction": "収益最大化 Content Factory note Threads affiliate SEO 初収益 ROI"}),
                "analytics": analytics,
            }
        )
        run = {
            "run_id": f"cf-{uuid4().hex[:10]}",
            "created_at": _now(),
            "contents": contents,
            "seo": seo,
            "image_prompts": image_prompts,
            "schedule": schedule,
            "reviews": reviews,
            "ab_tests": ab_tests,
            "analytics": analytics,
            "knowledge_record": knowledge,
            "business_feedback": business_feedback,
            "revenue_feedback": revenue_feedback,
            "coding_feedback": coding_feedback,
            "constitution_compliance": compliance,
            "next_content": self.next_content(contents, analytics),
        }
        state = self.load_state()
        state["contents"] = contents + state.get("contents", [])
        state["contents"] = state["contents"][:200]
        state["schedule"] = schedule + state.get("schedule", [])
        state["schedule"] = state["schedule"][:200]
        state["analytics"] = analytics
        state["ab_tests"] = ab_tests + state.get("ab_tests", [])
        state["ab_tests"] = state["ab_tests"][:100]
        state["quality_reviews"] = reviews + state.get("quality_reviews", [])
        state["quality_reviews"] = state["quality_reviews"][:200]
        state["business_feedback"] = business_feedback
        state["revenue_feedback"] = revenue_feedback
        state["coding_feedback"] = coding_feedback
        state.setdefault("knowledge_history", []).insert(0, knowledge)
        state["knowledge_history"] = state["knowledge_history"][:100]
        state["last_run"] = run
        self.save_state(state)
        return run

    def next_content(self, contents: list[dict[str, Any]], analytics: dict[str, Any]) -> dict[str, Any]:
        if analytics.get("ctr", 0) < 0.05:
            return {"type": "threads", "topic": "占いCTA改善", "reason": "CTR改善でnote流入を増やす"}
        if analytics.get("cvr", 0) < 0.02:
            return {"type": "landing_page", "topic": "比較表とFAQ強化", "reason": "CVR改善"}
        return {"type": "note", "topic": contents[0].get("topic", "収益化") if contents else "収益化", "reason": "勝ちテーマの横展開"}

    def save_knowledge(
        self,
        contents: list[dict[str, Any]],
        schedule: list[dict[str, Any]],
        analytics: dict[str, Any],
        reviews: list[dict[str, Any]],
    ) -> dict[str, Any]:
        knowledge = load_knowledge()
        record = {
            "id": f"cfk-{uuid4().hex[:10]}",
            "type": "content_factory",
            "content_count": len(contents),
            "content_ids": [item.get("content_id", "") for item in contents],
            "schedule_count": len(schedule),
            "analytics": analytics,
            "quality": {
                "approved": sum(1 for item in reviews if item.get("status") == "approved"),
                "needs_revision": sum(1 for item in reviews if item.get("status") != "approved"),
            },
            "created_at": _now(),
        }
        knowledge.setdefault("improvement_examples", []).insert(0, record)
        knowledge.setdefault("timeline", []).insert(0, record)
        knowledge.setdefault("categories", {}).setdefault("content_factory", 0)
        knowledge["categories"]["content_factory"] += 1
        save_knowledge(knowledge)
        record_improvement(
            {
                "instruction": "Content Factory revenue content generation",
                "estimated_revenue": analytics.get("revenue", 0),
                "estimated_cost": max(len(contents) * 800, 1),
                "risk": "low",
            }
        )
        return record

    def send_to_business_engine(self, contents: list[dict[str, Any]], analytics: dict[str, Any]) -> dict[str, Any]:
        data = self.business_store.load()
        for item in contents:
            if item.get("type") == "note":
                data.setdefault("article_queue", []).insert(0, item)
            if item.get("type") == "threads":
                data.setdefault("post_queue", []).insert(0, {"platform": "threads", **item})
            if item.get("type") == "affiliate":
                data.setdefault("affiliate_queue", []).insert(0, item)
        feedback = {
            "source": "content_factory",
            "status": "ready",
            "content_count": len(contents),
            "analytics": analytics,
            "created_at": _now(),
        }
        data.setdefault("mission_planner_feedback", []).insert(0, feedback)
        data["mission_planner_feedback"] = data["mission_planner_feedback"][:100]
        self.business_store.save(data)
        self.business_store.record_daily_kpi(
            revenue=int(analytics.get("revenue", 0)),
            articles=len([item for item in contents if item.get("type") == "note"]),
            sns_posts=len([item for item in contents if item.get("type") == "threads"]),
            affiliate_clicks=len([item for item in contents if item.get("type") == "affiliate"]),
            pv=int(analytics.get("pv", 0)),
            ctr=float(analytics.get("ctr", 0)),
            cv=float(analytics.get("cvr", 0)),
            roi=int(analytics.get("roi", 0)),
            notes="Content Factory daily pack",
        )
        return feedback

    def send_to_revenue_engine(self, contents: list[dict[str, Any]], analytics: dict[str, Any]) -> dict[str, Any]:
        opportunity = {
            "title": "Content Factory generated revenue pack",
            "channel": "content_factory",
            "expected_revenue": analytics.get("revenue", 0),
            "expected_profit": int(analytics.get("revenue", 0) * 0.82),
            "effort_hours": 1,
            "difficulty": 25,
            "risk": "low",
            "continuity": 85,
            "automation_rate": 90,
            "next_action": "反応が良いコンテンツをnoteとThreadsへ横展開",
        }
        try:
            run = RevenueEngineDashboard().run_cycle(extra_candidates=[opportunity])
            return {"source": "content_factory", "revenue_run_id": run.get("run_id", ""), "top_action": run.get("top_action", {})}
        except Exception as exc:
            return {"source": "content_factory", "error": str(exc)}

    def send_to_coding_engine(self, contents: list[dict[str, Any]], analytics: dict[str, Any]) -> dict[str, Any]:
        queue = [
            {
                "queue_id": f"ccq-{uuid4().hex[:10]}",
                "source": "content_factory",
                "priority": int(analytics.get("roi", 0)),
                "instruction": "Content Factoryの勝ちコンテンツを増やすUI/自動化を改善",
                "target_hint": "src/content_factory/",
                "created_at": _now(),
            }
        ]
        coding_path = PROJECT_ROOT / "config" / "coding_engine.json"
        try:
            data = json.loads(coding_path.read_text(encoding="utf-8")) if coding_path.exists() else {}
        except Exception:
            data = {}
        data.setdefault("content_improvement_queue", [])
        data["content_improvement_queue"] = queue + data["content_improvement_queue"]
        data["content_improvement_queue"] = data["content_improvement_queue"][:100]
        save_json_atomic(coding_path, data)
        return {"source": "content_factory", "queue": queue}
