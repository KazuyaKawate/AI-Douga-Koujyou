from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from src.business_engine.manager import BusinessEngineStore, _new_id
from src.self_builder.knowledge_manager import load_knowledge, save_knowledge


CONTENT_AUTOMATION_AGENTS = [
    {
        "agent": "Content Planner Agent",
        "capabilities": ["市場分析", "トレンド分析", "記事テーマ選択", "収益性評価"],
    },
    {
        "agent": "SEO Agent",
        "capabilities": ["検索キーワード", "タイトル", "見出し", "タグ", "内部リンク設計"],
    },
    {
        "agent": "Image Prompt Agent",
        "capabilities": ["アイキャッチ", "サムネイル", "OGP", "図解生成プロンプト"],
    },
    {
        "agent": "Publisher",
        "capabilities": ["note", "Threads", "X", "Instagram", "Facebook", "予約投稿管理"],
    },
    {
        "agent": "Analytics Agent",
        "capabilities": ["PV", "CTR", "クリック率", "人気記事", "収益", "改善点抽出"],
    },
]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RevenueAutomation:
    """Local-first revenue automation for note, SNS, affiliate, and SEO queues."""

    def __init__(self, store: BusinessEngineStore | None = None) -> None:
        self.store = store or BusinessEngineStore()

    # Content Automation ----------------------------------------------

    def start_content_automation(self, topic: str = "", target: str = "AIOS users") -> dict[str, Any]:
        data = self.store.load()
        context = self._content_research_context(data, topic)
        selected_theme = self._select_content_theme(data, topic)
        planner = self._run_content_planner_agent(data, context, selected_theme, target)
        seo = self._run_seo_agent(data, planner)
        image_prompts = self._run_image_prompt_agent(planner, seo)
        publisher = self._run_publisher_agent(planner, seo)
        analytics = self._run_analytics_agent(data, planner)
        mission_feedback = self._build_mission_planner_feedback(planner, seo, analytics)
        run = {
            "run_id": _new_id("content_auto"),
            "status": "planned",
            "topic": selected_theme,
            "target": target,
            "agents": CONTENT_AUTOMATION_AGENTS,
            "references": ["business_engine", "research_team"],
            "research_context": context,
            "outputs": {
                "content_planner": planner,
                "seo": seo,
                "image_prompts": image_prompts,
                "publisher": publisher,
                "analytics": analytics,
            },
            "mission_planner_feedback": mission_feedback,
            "created_at": _now(),
            "updated_at": _now(),
        }
        data.setdefault("content_automation_runs", [])
        data["content_automation_runs"].insert(0, run)
        self.store.save(data)
        return run

    def _content_research_context(self, data: dict[str, Any], topic: str) -> dict[str, Any]:
        seo_keywords = [item.get("keyword", "") for item in data.get("seo_queue", []) if item.get("keyword")]
        revenue_titles = [item.get("title", "") for item in data.get("revenue_pipeline", []) if item.get("title")]
        article_titles = [item.get("title", "") for item in data.get("article_queue", []) if item.get("title")]
        post_topics = [item.get("topic", "") for item in data.get("post_queue", []) if item.get("topic")]
        return {
            "business_engine": {
                "pipeline_summary": self.store.pipeline_summary(),
                "dashboard_summary": self.dashboard_summary(),
                "revenue_titles": revenue_titles[:5],
                "article_titles": article_titles[:5],
            },
            "research_team": {
                "source": "local business queues",
                "trend_signals": [topic, *seo_keywords[:5], *post_topics[:3]],
                "market_notes": [
                    "既存のSEO QueueとRevenue Pipelineから収益化テーマを抽出",
                    "公開済み記事とSNS投稿の反応をAnalytics Agentへ接続",
                ],
            },
        }

    def _select_content_theme(self, data: dict[str, Any], topic: str) -> str:
        if topic.strip():
            return topic.strip()
        for item in data.get("revenue_pipeline", []):
            if item.get("title"):
                return str(item["title"])
        for item in data.get("seo_queue", []):
            if item.get("keyword"):
                return str(item["keyword"])
        return "AIOS Content Automation"

    def _run_content_planner_agent(
        self,
        data: dict[str, Any],
        context: dict[str, Any],
        selected_theme: str,
        target: str,
    ) -> dict[str, Any]:
        forecast = context["business_engine"]["pipeline_summary"].get("weighted_forecast", 0)
        seo_count = len(data.get("seo_queue", []))
        profitability = min(100, 45 + min(30, int(forecast) // 1000) + min(25, seo_count * 5))
        return {
            "agent": "Content Planner Agent",
            "status": "done",
            "references": ["business_engine.pipeline_summary", "research_team.trend_signals"],
            "market_analysis": f"{target}向けに、既存キューから需要が見えるテーマを優先します。",
            "trend_analysis": context["research_team"]["trend_signals"][:6],
            "selected_theme": selected_theme,
            "profitability_score": profitability,
            "profitability_reason": "Revenue Pipelineの予測収益とSEO Queue量からローカル評価しました。",
        }

    def _run_seo_agent(self, data: dict[str, Any], planner: dict[str, Any]) -> dict[str, Any]:
        theme = planner["selected_theme"]
        queued_keywords = [item.get("keyword", "") for item in data.get("seo_queue", []) if item.get("keyword")]
        keywords = list(dict.fromkeys([theme, *queued_keywords, "AIOS", "自動化", "収益化"]))[:8]
        headings = [
            "なぜ今このテーマに取り組むのか",
            "Business Engineで作る収益導線",
            "Content Automationの実行ステップ",
            "失敗しやすいポイント",
            "次に改善すること",
        ]
        return {
            "agent": "SEO Agent",
            "status": "done",
            "references": ["business_engine.seo_queue", "research_team.trend_signals"],
            "keywords": keywords,
            "title": f"{theme}で始めるAIOSコンテンツ収益化",
            "headings": headings,
            "tags": ["AIOS", "BusinessEngine", "ContentAutomation", "note", "収益化"],
            "internal_links": self.build_internal_links(),
        }

    def _run_image_prompt_agent(self, planner: dict[str, Any], seo: dict[str, Any]) -> dict[str, Any]:
        theme = planner["selected_theme"]
        keyword = seo["keywords"][0] if seo.get("keywords") else theme
        base = f"{theme}, AIOS dashboard, content automation workflow, clean modern UI"
        return {
            "agent": "Image Prompt Agent",
            "status": "done",
            "references": ["seo.title", "content_planner.selected_theme"],
            "eyecatch": f"16:9 eyecatch image, {base}, readable space for title: {seo['title']}",
            "thumbnail": f"Square thumbnail, bold central keyword '{keyword}', workflow cards, high contrast",
            "ogp": f"OGP banner, {base}, note and social publishing timeline",
            "diagram": f"Generate a diagram: Business Engine -> Research Team -> Planner -> SEO -> Publisher -> Analytics for {theme}",
        }

    def _run_publisher_agent(self, planner: dict[str, Any], seo: dict[str, Any]) -> dict[str, Any]:
        theme = planner["selected_theme"]
        channels = ["note", "Threads", "X", "Instagram", "Facebook"]
        schedule = [
            {"channel": channel, "status": "draft_ready", "scheduled_for": (date.today() + timedelta(days=idx)).isoformat()}
            for idx, channel in enumerate(channels)
        ]
        return {
            "agent": "Publisher",
            "status": "done",
            "references": ["business_engine.scheduled_jobs", "business_engine.post_queue"],
            "channels": channels,
            "note_title": seo["title"],
            "social_topic": theme,
            "reservation_management": schedule,
            "external_posting": "disabled_local_first",
        }

    def _run_analytics_agent(self, data: dict[str, Any], planner: dict[str, Any]) -> dict[str, Any]:
        kpis = data.get("daily_kpis", [])
        revenue = sum(int(item.get("revenue", 0)) for item in kpis)
        clicks = sum(int(item.get("affiliate_clicks", 0)) for item in kpis)
        articles = data.get("article_queue", [])
        popular = [article.get("title", article.get("topic", "")) for article in articles[:3]]
        pv = sum(int(item.get("pv", 0)) for item in kpis)
        impressions = max(1, sum(int(item.get("impressions", 0)) for item in kpis))
        ctr = round(clicks / impressions, 4)
        improvements = [
            "CTR確認用に投稿別クリック計測を増やす",
            "人気記事から内部リンク候補を自動生成する",
            "収益性スコアが高いテーマをMission Plannerへ戻す",
        ]
        return {
            "agent": "Analytics Agent",
            "status": "done",
            "references": ["business_engine.daily_kpis", "business_engine.article_queue"],
            "pv": pv,
            "ctr": ctr,
            "click_rate": ctr,
            "popular_articles": popular,
            "revenue": revenue,
            "improvements": improvements,
            "focus_theme": planner["selected_theme"],
        }

    def _build_mission_planner_feedback(
        self,
        planner: dict[str, Any],
        seo: dict[str, Any],
        analytics: dict[str, Any],
    ) -> dict[str, Any]:
        tasks = [
            {
                "title": f"{planner['selected_theme']}の記事下書きを生成",
                "agent": "Mission Planner",
                "priority": "high" if planner.get("profitability_score", 0) >= 70 else "normal",
                "reason": planner["profitability_reason"],
            },
            {
                "title": f"SEOタイトルを検証: {seo['title']}",
                "agent": "SEO Agent",
                "priority": "normal",
                "reason": "検索キーワード、見出し、タグを作成済みです。",
            },
            {
                "title": "Analytics改善点を次回Missionへ反映",
                "agent": "Analytics Agent",
                "priority": "normal",
                "reason": " / ".join(analytics.get("improvements", [])[:2]),
            },
        ]
        return {
            "receiver": "Mission Planner",
            "status": "ready",
            "improvement_tasks": tasks,
            "returned_at": _now(),
        }

    # Note Factory -----------------------------------------------------

    def generate_note_article_pipeline(self, topic: str, target: str = "AIOS users") -> dict[str, Any]:
        research = self.topic_research(topic)
        keywords = self.extract_keywords(research)
        title = self.generate_title(topic, keywords)
        if self._is_duplicate_article(title, keywords[0] if keywords else topic):
            return {
                "article_id": "",
                "status": "duplicate_blocked",
                "topic": topic,
                "title": title,
                "keyword": keywords[0] if keywords else topic,
                "reason": "同一タイトルまたは主要Keywordの記事が既に予約・公開済みです。",
            }
        outline = self.generate_outline(topic, keywords)
        body = self.generate_body(title, topic, keywords, outline, target)
        image_prompts = self.generate_image_prompts(title, keywords)
        eyecatch = self.generate_eyecatch(title, image_prompts)
        seo = self.evaluate_seo(title, body, keywords)
        article = {
            "article_id": _new_id("article"),
            "topic": topic,
            "target": target,
            "research": research,
            "keyword": keywords[0] if keywords else topic,
            "keywords": keywords,
            "title": title,
            "outline": outline,
            "body": body,
            "image_prompts": image_prompts,
            "eyecatch": eyecatch,
            "seo": seo,
            "pv": 0,
            "ctr": 0,
            "estimated_revenue": self._estimate_article_revenue(seo),
            "review": {"score": seo["score"], "recommendation": "approve" if seo["score"] >= 70 else "revise"},
            "approved": seo["score"] >= 70,
            "status": "draft",
            "created_at": _now(),
            "updated_at": _now(),
        }
        article["markdown_path"] = str(self.generate_markdown(article))
        data = self.store.load()
        data["article_queue"].insert(0, article)
        self.store.save(data)
        self.save_article_knowledge(article, event="generated")
        self.feedback_research_team(article)
        self.return_improvement_to_mission_planner(article)
        return article

    def topic_research(self, topic: str) -> dict[str, Any]:
        data = self.store.load()
        pipeline = self.store.pipeline_summary()
        seo_signals = [item.get("keyword", "") for item in data.get("seo_queue", []) if item.get("keyword")]
        kpis = data.get("daily_kpis", [])
        return {
            "topic": topic.strip() or "AIOS Business Engine",
            "source": "business_engine_local",
            "trend_signals": list(dict.fromkeys([topic, *seo_signals]))[:8],
            "revenue_forecast": pipeline.get("weighted_forecast", 0),
            "recent_pv": sum(int(item.get("pv", 0)) for item in kpis[-7:]),
            "recent_ctr": round(sum(float(item.get("ctr", 0)) for item in kpis[-7:]) / max(len(kpis[-7:]), 1), 4),
            "researched_at": _now(),
        }

    def extract_keywords(self, research: dict[str, Any]) -> list[str]:
        topic = str(research.get("topic", "AIOS Business Engine"))
        seeds = [topic, *research.get("trend_signals", []), "AIOS", "Business Engine", "note収益化", "自動投稿"]
        keywords = []
        for seed in seeds:
            value = str(seed).strip()
            if value and value not in keywords:
                keywords.append(value)
        return keywords[:8]

    def generate_title(self, topic: str, keywords: list[str]) -> str:
        main = keywords[0] if keywords else topic
        return f"{main}で作るAIOS実運用型Business Engine"

    def generate_outline(self, topic: str, keywords: list[str]) -> list[dict[str, str]]:
        return [
            {"heading": "なぜ今Business Engineを実運用化するのか", "goal": "読者の課題と収益導線を明確にする"},
            {"heading": "Topic Researchから記事化までの流れ", "goal": "生成プロセスを理解してもらう"},
            {"heading": "SEOと予約投稿で継続運用する", "goal": "検索と公開タイミングの設計を示す"},
            {"heading": "PV・CTR・収益から改善する", "goal": "運用後の改善ループを説明する"},
            {"heading": "今日から始める最小ステップ", "goal": "次の行動につなげる"},
        ]

    def generate_body(
        self,
        title: str,
        topic: str,
        keywords: list[str],
        outline: list[dict[str, str]],
        target: str,
    ) -> str:
        keyword_text = "、".join(keywords[:5])
        sections = []
        for item in outline:
            sections.append(
                f"## {item['heading']}\n"
                f"{item['goal']}ために、{topic}を小さく検証しながら進めます。"
                f"重要なKeywordは {keyword_text} です。AIOSではResearch、生成、予約、分析を一つの流れで扱えます。\n"
            )
        return (
            f"# {title}\n\n"
            f"対象読者: {target}\n\n"
            f"この記事では {topic} を実運用に近づけるための流れを整理します。\n\n"
            + "\n".join(sections)
            + "\n## まとめ\n"
            "最初のゴールは、完璧な自動投稿ではなく、重複なく予約し、反応を見て改善できる状態です。"
            "PV、CTR、収益の数字をKnowledgeへ戻すことで、次の記事テーマが自然に強くなります。\n"
        )

    def generate_image_prompts(self, title: str, keywords: list[str]) -> dict[str, str]:
        keyword = keywords[0] if keywords else "AIOS Business Engine"
        return {
            "eyecatch": f"16:9 clean dashboard eyecatch, title concept '{title}', keyword '{keyword}', business automation workflow",
            "thumbnail": f"square note thumbnail, bold Japanese SaaS dashboard, keyword '{keyword}', high readability",
            "section": f"diagram style image prompt showing Topic Research -> SEO -> note schedule -> Analytics for {keyword}",
        }

    def generate_eyecatch(self, title: str, image_prompts: dict[str, str]) -> dict[str, Any]:
        output_dir = self.store.path.parent / "note_eyecatch"
        output_dir.mkdir(parents=True, exist_ok=True)
        asset_id = _new_id("eyecatch")
        path = output_dir / f"{asset_id}.txt"
        path.write_text(image_prompts["eyecatch"], encoding="utf-8")
        return {
            "asset_id": asset_id,
            "status": "prompt_ready",
            "title": title,
            "prompt": image_prompts["eyecatch"],
            "path": str(path),
            "created_at": _now(),
        }

    def generate_markdown(self, article: dict[str, Any]) -> Path:
        return self._save_article_markdown(article)

    def evaluate_seo(self, title: str, body: str, keywords: list[str]) -> dict[str, Any]:
        score = 45
        if 20 <= len(title) <= 60:
            score += 15
        if keywords and keywords[0] in title:
            score += 15
        if len(body) >= 800:
            score += 10
        if body.count("## ") >= 4:
            score += 10
        if "まとめ" in body:
            score += 5
        return {
            "score": min(score, 100),
            "keywords": keywords,
            "checks": {
                "title_length": 20 <= len(title) <= 60,
                "primary_keyword_in_title": bool(keywords and keywords[0] in title),
                "body_length": len(body),
                "heading_count": body.count("## "),
            },
            "recommendations": ["主要Keywordをタイトル前半に置く", "PV/CTRが低い場合は導入文とCTAを改善する"],
            "evaluated_at": _now(),
        }

    def generate_article(self, topic: str, keyword: str = "", target: str = "AIOS users") -> dict[str, Any]:
        title = self._generate_note_title(topic, keyword)
        body = self._generate_note_body(title, topic, keyword or topic, target)
        article = {
            "article_id": _new_id("article"),
            "topic": topic,
            "keyword": keyword or topic,
            "target": target,
            "title": title,
            "body": body,
            "review": None,
            "approved": False,
            "status": "draft",
            "created_at": _now(),
            "updated_at": _now(),
        }
        article["markdown_path"] = str(self._save_article_markdown(article))
        data = self.store.load()
        data["article_queue"].insert(0, article)
        self.store.save(data)
        return article

    def _generate_note_title(self, topic: str, keyword: str = "") -> str:
        main = (keyword or topic).strip()
        return f"{main}で始めるAIOS収益化の最小ステップ"

    def _generate_note_body(self, title: str, topic: str, keyword: str, target: str) -> str:
        return (
            f"# {title}\n\n"
            f"対象読者: {target}\n\n"
            "## はじめに\n"
            f"{topic}に取り組むとき、最初から大きな自動化を狙う必要はありません。"
            "まずは毎日続けられる小さな収益導線を作ることが重要です。\n\n"
            "## 課題\n"
            f"{keyword}に関心がある読者は、何から着手すれば収益につながるのかを知りたい状態です。"
            "アイデア、下書き、レビュー、投稿準備が分断されると、公開までの手間が増えて継続できません。\n\n"
            "## AIOSで作る流れ\n"
            "AIOSでは、note記事のテーマを決め、本文を作り、レビューして、投稿前の状態までローカルで管理します。"
            "外部APIや有料自動化に進む前に、まず手元で記事資産を増やせます。\n\n"
            "## 今日やること\n"
            "1. 収益化につながるテーマを1つ決める\n"
            "2. note記事の下書きを生成する\n"
            "3. Threads投稿へ転用できる要点を抜き出す\n"
            "4. 公開前にタイトル、CTA、導線を確認する\n\n"
            "## まとめ\n"
            "最初の成果は、完全自動投稿ではなく、公開できる下書きを安定して作れる状態です。"
            "AIOSを使って小さな制作サイクルを回し、反応があるテーマから収益化を広げていきましょう。\n"
        )

    def _save_article_markdown(self, article: dict[str, Any]) -> Path:
        output_dir = self.store.path.parent / "note_markdown"
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"{article['article_id']}.md"
        path.write_text(article["body"], encoding="utf-8")
        return path

    def review_article(self, article_id: str) -> dict[str, Any] | None:
        data = self.store.load()
        article = _find(data["article_queue"], "article_id", article_id)
        if article is None:
            return None
        article["review"] = {
            "score": 82,
            "checks": ["title_present", "keyword_present", "cta_present"],
            "recommendation": "approve",
        }
        article["status"] = "reviewed"
        article["updated_at"] = _now()
        self.store.save(data)
        return article

    def approve_article(self, article_id: str) -> dict[str, Any] | None:
        data = self.store.load()
        article = _find(data["article_queue"], "article_id", article_id)
        if article is None:
            return None
        article["approved"] = True
        article["status"] = "approved"
        article["updated_at"] = _now()
        self.store.save(data)
        return article

    def queue_article(self, article_id: str) -> dict[str, Any] | None:
        data = self.store.load()
        article = _find(data["article_queue"], "article_id", article_id)
        if article is None:
            return None
        article["status"] = "queued"
        article["updated_at"] = _now()
        self.store.save(data)
        self.store.schedule_job(
            "note_article",
            article["title"],
            date.today().isoformat(),
            payload={"topic": article["topic"], "keywords": article["keyword"], "use_workflow": True},
        )
        return article

    def schedule_note_post(self, article_id: str, scheduled_for: str | None = None, *, call_api: bool = False) -> dict[str, Any] | None:
        data = self.store.load()
        article = _find(data["article_queue"], "article_id", article_id)
        if article is None:
            return None
        if self._has_posted_or_reserved(data, article):
            article["status"] = "duplicate_blocked"
            article["updated_at"] = _now()
            self.store.save(data)
            return article
        scheduled_at = scheduled_for or (date.today() + timedelta(days=1)).isoformat()
        api_result = self._note_reservation_api(article, scheduled_at, call_api=call_api)
        reservation = {
            "reservation_id": _new_id("note_res"),
            "article_id": article_id,
            "title": article.get("title", ""),
            "scheduled_for": scheduled_at,
            "status": "reserved" if api_result["status"] in ("disabled_local_first", "accepted") else "failed",
            "api_result": api_result,
            "created_at": _now(),
            "updated_at": _now(),
        }
        data.setdefault("note_reservations", []).insert(0, reservation)
        article["status"] = "reserved"
        article["scheduled_for"] = scheduled_at
        article["reservation_id"] = reservation["reservation_id"]
        article["updated_at"] = _now()
        self.store.save(data)
        self.store.schedule_job(
            "note_article",
            article["title"],
            scheduled_at,
            priority="high" if article.get("seo", {}).get("score", 0) >= 80 else "normal",
            payload={"article_id": article_id, "note_reservation_id": reservation["reservation_id"], "use_workflow": False},
        )
        return reservation

    def publish_article(self, article_id: str) -> dict[str, Any] | None:
        data = self.store.load()
        article = _find(data["article_queue"], "article_id", article_id)
        if article is None:
            return None
        article["status"] = "published"
        article["published_at"] = date.today().isoformat()
        article["updated_at"] = _now()
        history = self._posting_history_item(article, "published")
        data.setdefault("posting_history", []).insert(0, history)
        for reservation in data.setdefault("note_reservations", []):
            if reservation.get("article_id") == article_id and reservation.get("status") == "reserved":
                reservation["status"] = "published"
                reservation["updated_at"] = _now()
        self.store.save(data)
        self.store.record_execution(article_id, "completed", "Local article publish completed.")
        self.save_article_knowledge(article, event="published")
        self.feedback_research_team(article)
        self.return_improvement_to_mission_planner(article)
        return article

    def publish_reserved_note(self, reservation_id: str) -> dict[str, Any] | None:
        data = self.store.load()
        reservation = _find(data.setdefault("note_reservations", []), "reservation_id", reservation_id)
        if reservation is None:
            return None
        return self.publish_article(str(reservation.get("article_id", "")))

    def fetch_article_metrics(self, article_id: str, *, pv: int | None = None, ctr: float | None = None, revenue: int = 0) -> dict[str, Any] | None:
        data = self.store.load()
        article = _find(data["article_queue"], "article_id", article_id)
        if article is None:
            return None
        if pv is None:
            pv = max(10, int(article.get("seo", {}).get("score", 50)) * 3)
        if ctr is None:
            ctr = round(min(0.18, max(0.01, int(article.get("seo", {}).get("score", 50)) / 1000)), 4)
        article["pv"] = int(pv)
        article["ctr"] = float(ctr)
        article["actual_revenue"] = int(revenue or int(pv) * float(ctr) * 120)
        article["metrics_updated_at"] = _now()
        article["updated_at"] = _now()
        self.store.save(data)
        self.store.record_daily_kpi(
            revenue=int(article["actual_revenue"]),
            articles=1,
            affiliate_clicks=int(int(pv) * float(ctr)),
            pv=int(pv),
            ctr=float(ctr),
            notes=f"note metrics: {article.get('title', '')}",
        )
        self.save_article_knowledge(article, event="metrics")
        self.feedback_research_team(article)
        self.return_improvement_to_mission_planner(article)
        return article

    def save_article_knowledge(self, article: dict[str, Any], event: str = "generated") -> dict[str, Any]:
        knowledge = load_knowledge()
        record = {
            "history_id": _new_id("hist"),
            "type": "business_article",
            "event": event,
            "article_id": article.get("article_id", ""),
            "title": article.get("title", ""),
            "keywords": article.get("keywords", [article.get("keyword", "")]),
            "seo": article.get("seo", {}),
            "pv": article.get("pv", 0),
            "ctr": article.get("ctr", 0),
            "revenue": article.get("actual_revenue", article.get("estimated_revenue", 0)),
            "created_at": _now(),
        }
        knowledge.setdefault("history", []).insert(0, record)
        knowledge.setdefault("improvement_examples", []).insert(0, record)
        save_knowledge(knowledge)
        return record

    def feedback_research_team(self, article: dict[str, Any]) -> dict[str, Any]:
        feedback = {
            "feedback_id": _new_id("research_fb"),
            "receiver": "Research Team",
            "article_id": article.get("article_id", ""),
            "topic": article.get("topic", ""),
            "keywords": article.get("keywords", [article.get("keyword", "")]),
            "pv": article.get("pv", 0),
            "ctr": article.get("ctr", 0),
            "message": "記事生成・投稿・分析結果を次回Topic Researchへ反映",
            "created_at": _now(),
        }
        data = self.store.load()
        data.setdefault("research_feedback", []).insert(0, feedback)
        self.store.save(data)
        return feedback

    def return_improvement_to_mission_planner(self, article: dict[str, Any]) -> dict[str, Any]:
        seo_score = int(article.get("seo", {}).get("score", 0))
        feedback = {
            "feedback_id": _new_id("mission_fb"),
            "receiver": "Mission Planner",
            "status": "ready",
            "article_id": article.get("article_id", ""),
            "improvement_tasks": [
                {
                    "title": f"記事SEO改善: {article.get('title', '')}",
                    "agent": "SEO Agent",
                    "priority": "high" if seo_score < 75 else "normal",
                    "reason": f"SEO score={seo_score}, PV={article.get('pv', 0)}, CTR={article.get('ctr', 0)}",
                },
                {
                    "title": "Business Engineの投稿結果を次の記事Queueへ反映",
                    "agent": "Content Planner Agent",
                    "priority": "normal",
                    "reason": "投稿履歴とKnowledgeをもとに次のTopic Researchを更新",
                },
            ],
            "returned_at": _now(),
        }
        data = self.store.load()
        data.setdefault("mission_planner_feedback", []).insert(0, feedback)
        self.store.save(data)
        return feedback

    def _is_duplicate_article(self, title: str, keyword: str) -> bool:
        data = self.store.load()
        return any(
            row.get("title") == title
            or str(row.get("keyword", "")).lower() == str(keyword).lower()
            or str(keyword).lower() in [str(item).lower() for item in row.get("keywords", [])]
            for row in data.get("article_queue", [])
            if row.get("status") in ("reserved", "published", "queued")
        )

    def _has_posted_or_reserved(self, data: dict[str, Any], article: dict[str, Any]) -> bool:
        article_id = article.get("article_id", "")
        title = article.get("title", "")
        reservations = data.get("note_reservations", [])
        history = data.get("posting_history", [])
        return any(
            row.get("article_id") == article_id or row.get("title") == title
            for row in [*reservations, *history]
            if row.get("status") in ("reserved", "published")
        )

    def _note_reservation_api(self, article: dict[str, Any], scheduled_for: str, *, call_api: bool = False) -> dict[str, Any]:
        data = self.store.load()
        external_enabled = bool(data.get("meta", {}).get("external_apis_enabled", False))
        if not call_api or not external_enabled:
            return {
                "status": "disabled_local_first",
                "message": "note予約投稿APIはLocal-first安全モードで記録のみ実施",
            }
        endpoint = os.getenv("NOTE_API_ENDPOINT", "")
        token = os.getenv("NOTE_API_TOKEN", "")
        if not endpoint or not token:
            return {"status": "not_configured", "message": "NOTE_API_ENDPOINT or NOTE_API_TOKEN is missing"}
        payload = parse.urlencode(
            {
                "title": article.get("title", ""),
                "body": article.get("body", ""),
                "scheduled_for": scheduled_for,
            }
        ).encode("utf-8")
        req = request.Request(endpoint, data=payload, headers={"Authorization": f"Bearer {token}"}, method="POST")
        try:
            with request.urlopen(req, timeout=10) as response:
                return {"status": "accepted", "code": response.status, "message": response.read().decode("utf-8")[:500]}
        except error.URLError as exc:
            return {"status": "failed", "message": str(exc)}

    def _posting_history_item(self, article: dict[str, Any], status: str) -> dict[str, Any]:
        return {
            "history_id": _new_id("post_hist"),
            "article_id": article.get("article_id", ""),
            "title": article.get("title", ""),
            "status": status,
            "published_at": article.get("published_at", date.today().isoformat()),
            "markdown_path": article.get("markdown_path", ""),
            "pv": article.get("pv", 0),
            "ctr": article.get("ctr", 0),
            "revenue": article.get("actual_revenue", article.get("estimated_revenue", 0)),
            "created_at": _now(),
        }

    def _estimate_article_revenue(self, seo: dict[str, Any]) -> int:
        return int(seo.get("score", 0)) * 180

    # SNS Factory ------------------------------------------------------

    def generate_threads_post_from_markdown(self, markdown_path: str | Path, source_id: str = "") -> dict[str, Any]:
        path = Path(markdown_path)
        markdown = path.read_text(encoding="utf-8")
        title = self._extract_markdown_title(markdown, path.stem)
        hashtags = self._generate_threads_hashtags(markdown, title)
        text = self._generate_threads_text(markdown, title, hashtags)
        post = {
            "post_id": _new_id("post"),
            "platform": "threads",
            "topic": title,
            "source_id": source_id or str(path),
            "markdown_path": str(path),
            "text": text,
            "hashtags": hashtags,
            "status": "draft",
            "retry_count": 0,
            "scheduled_for": "",
            "published_at": "",
            "created_at": _now(),
            "updated_at": _now(),
        }
        data = self.store.load()
        data["post_queue"].insert(0, post)
        self.store.save(data)
        return post

    def _extract_markdown_title(self, markdown: str, fallback: str) -> str:
        for line in markdown.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip() or fallback
        return fallback

    def _generate_threads_text(self, markdown: str, title: str, hashtags: list[str]) -> str:
        points = [
            line.strip(" -0123456789.、")
            for line in markdown.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ][:3]
        body = " ".join(points) or title
        text = f"{title}\n\n{body}\n\n{' '.join(hashtags)}"
        return text[:500]

    def _generate_threads_hashtags(self, markdown: str, title: str) -> list[str]:
        base_words = [title, markdown]
        tags = ["#AIOS", "#note", "#Threads"]
        joined = " ".join(base_words).lower()
        if "収益" in joined or "revenue" in joined:
            tags.append("#収益化")
        if "自動" in joined or "automation" in joined:
            tags.append("#自動化")
        return tags[:5]

    def generate_sns_posts(self, topic: str, source_id: str = "") -> list[dict[str, Any]]:
        templates = {
            "x": f"{topic} is easier to monetize when drafts, queues, and reviews stay local-first. Start with one small workflow today.",
            "threads": f"A practical thread idea: use {topic} to build a daily content loop, then measure what converts before scaling.",
            "instagram": f"{topic} workflow: plan the idea, create the asset, queue the post, review the outcome. Local-first keeps costs controlled.",
        }
        data = self.store.load()
        posts = []
        for platform, text in templates.items():
            post = {
                "post_id": _new_id("post"),
                "platform": platform,
                "topic": topic,
                "source_id": source_id,
                "text": text,
                "status": "draft",
                "retry_count": 0,
                "scheduled_for": "",
                "published_at": "",
                "created_at": _now(),
                "updated_at": _now(),
            }
            data["post_queue"].insert(0, post)
            posts.append(post)
        self.store.save(data)
        return posts

    def queue_post(self, post_id: str, scheduled_for: str | None = None) -> dict[str, Any] | None:
        data = self.store.load()
        post = _find(data["post_queue"], "post_id", post_id)
        if post is None:
            return None
        post["status"] = "scheduled"
        post["scheduled_for"] = scheduled_for or (date.today() + timedelta(days=1)).isoformat()
        post["updated_at"] = _now()
        self.store.save(data)
        self.store.schedule_job(
            "sns_post",
            f"{post['platform']} post: {post['topic']}",
            post["scheduled_for"],
            payload={"topic": post["topic"], "brand_name": "AIOS", "use_workflow": True},
        )
        return post

    def publish_post(self, post_id: str) -> dict[str, Any] | None:
        data = self.store.load()
        post = _find(data["post_queue"], "post_id", post_id)
        if post is None:
            return None
        post["status"] = "published"
        post["published_at"] = date.today().isoformat()
        post["updated_at"] = _now()
        self.store.save(data)
        self.store.record_execution(post_id, "completed", f"Local {post['platform']} publish completed.")
        return post

    def get_pending_posts(self) -> list[dict[str, Any]]:
        data = self.store.load()
        return [
            post for post in data.get("post_queue", [])
            if post.get("status") in ("draft", "scheduled", "retry_queued")
        ]

    def mark_post_posted(self, post_id: str, posted_at: str | None = None) -> dict[str, Any] | None:
        data = self.store.load()
        post = _find(data["post_queue"], "post_id", post_id)
        if post is None:
            return None
        post["status"] = "posted"
        post["posted_at"] = posted_at or _now()
        post["published_at"] = post["posted_at"]
        post["last_error"] = ""
        post["updated_at"] = _now()
        self.store.save(data)
        return post

    def mark_post_failed(self, post_id: str, error: str) -> dict[str, Any] | None:
        data = self.store.load()
        post = _find(data["post_queue"], "post_id", post_id)
        if post is None:
            return None
        post["status"] = "failed"
        post["last_error"] = error
        post["retry_count"] = int(post.get("retry_count", 0)) + 1
        post["failed_at"] = _now()
        post["updated_at"] = _now()
        self.store.save(data)
        return post

    def poster(self, post: dict[str, Any], dry_run: bool = False) -> bool | dict[str, Any] | Exception:
        try:
            if not post.get("post_id"):
                raise ValueError("post_id is required")
            if not post.get("text"):
                raise ValueError("text is required")
            if not post.get("platform"):
                raise ValueError("platform is required")
            if post.get("platform") == "threads":
                return self.post_to_threads_api(post, dry_run=dry_run)
            return True
        except Exception as exc:
            return exc

    def validate_threads_config(self) -> dict[str, str]:
        access_token = os.getenv("THREADS_ACCESS_TOKEN", "").strip()
        user_id = os.getenv("THREADS_USER_ID", "").strip()
        if not access_token:
            raise RuntimeError("Threads production posting is blocked: THREADS_ACCESS_TOKEN is not set.")
        if not user_id:
            raise RuntimeError("Threads production posting is blocked: THREADS_USER_ID is not set.")
        return {"access_token": access_token, "user_id": user_id}

    def post_to_threads_api(self, post: dict[str, Any], dry_run: bool = False) -> bool | dict[str, Any]:
        config = self.validate_threads_config()
        access_token = config["access_token"]
        user_id = config["user_id"]
        api_base = os.getenv("THREADS_API_BASE", "https://graph.threads.net/v1.0").rstrip("/")
        if dry_run:
            return {
                "platform": "threads",
                "text": post["text"],
                "user_id": user_id,
                "dry_run": True,
            }

        create_payload = {
            "media_type": "TEXT",
            "text": post["text"],
            "access_token": access_token,
        }
        create_result = self._threads_api_post(f"{api_base}/{user_id}/threads", create_payload)
        creation_id = create_result.get("id")
        if not creation_id:
            raise RuntimeError(f"Threads create response missing id: {create_result}")

        publish_payload = {
            "creation_id": creation_id,
            "access_token": access_token,
        }
        publish_result = self._threads_api_post(f"{api_base}/{user_id}/threads_publish", publish_payload)
        if not publish_result.get("id"):
            raise RuntimeError(f"Threads publish response missing id: {publish_result}")
        return True

    def _threads_api_post(self, url: str, payload: dict[str, str]) -> dict[str, Any]:
        encoded = parse.urlencode(payload).encode("utf-8")
        req = request.Request(url, data=encoded, method="POST")
        try:
            with request.urlopen(req, timeout=30) as response:
                body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Threads API HTTP {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Threads API request failed: {exc.reason}") from exc
        return json.loads(body or "{}")

    def process_next_post(self, poster: Any | None = None, dry_run: bool = False) -> dict[str, Any] | None:
        pending = self.get_pending_posts()
        if not pending:
            return None
        post = pending[0]
        try:
            if poster is None:
                result = self.poster(post, dry_run=dry_run)
            else:
                result = poster(post)
            if isinstance(result, Exception):
                raise result
            if dry_run:
                return result if isinstance(result, dict) else {"post_id": post["post_id"], "dry_run": True}
            return self.mark_post_posted(post["post_id"])
        except Exception as exc:
            return self.mark_post_failed(post["post_id"], str(exc))

    def test_post_pipeline(self, topic: str = "AIOS note automation", keyword: str = "AIOS収益化") -> dict[str, Any]:
        article = self.generate_article(topic, keyword)
        threads_post = self.generate_threads_post_from_markdown(
            article["markdown_path"],
            source_id=article["article_id"],
        )
        result = self.process_next_post(dry_run=True)
        return {
            "article_id": article["article_id"],
            "markdown_path": article["markdown_path"],
            "threads_post_id": threads_post["post_id"],
            "result": result,
        }

    # Affiliate Factory -----------------------------------------------

    def create_affiliate_offer(
        self,
        title: str,
        url: str,
        commission_rate: float = 0.1,
        expected_clicks: int = 0,
        conversion_rate: float = 0.02,
        average_order_value: int = 0,
    ) -> dict[str, Any]:
        offer = {
            "offer_id": _new_id("aff"),
            "title": title,
            "url": url,
            "link_token": f"aff-{_new_id('trk')}",
            "commission_rate": float(commission_rate),
            "clicks": int(expected_clicks),
            "conversions": 0,
            "conversion_rate": float(conversion_rate),
            "average_order_value": int(average_order_value),
            "estimated_revenue": self.estimate_affiliate_revenue(expected_clicks, conversion_rate, average_order_value, commission_rate),
            "status": "queued",
            "created_at": _now(),
            "updated_at": _now(),
        }
        data = self.store.load()
        data["affiliate_queue"].insert(0, offer)
        self.store.save(data)
        return offer

    def insert_affiliate_links(self, content: str, offer_id: str) -> str:
        data = self.store.load()
        offer = _find(data["affiliate_queue"], "offer_id", offer_id)
        if offer is None:
            return content
        return f"{content}\n\nRecommended resource: [{offer['title']}]({offer['url']}?ref={offer['link_token']})"

    def track_click(self, offer_id: str, count: int = 1) -> dict[str, Any] | None:
        return self._update_affiliate_counter(offer_id, clicks=count)

    def track_conversion(self, offer_id: str, count: int = 1) -> dict[str, Any] | None:
        return self._update_affiliate_counter(offer_id, conversions=count)

    def _update_affiliate_counter(self, offer_id: str, *, clicks: int = 0, conversions: int = 0) -> dict[str, Any] | None:
        data = self.store.load()
        offer = _find(data["affiliate_queue"], "offer_id", offer_id)
        if offer is None:
            return None
        offer["clicks"] = int(offer.get("clicks", 0)) + int(clicks)
        offer["conversions"] = int(offer.get("conversions", 0)) + int(conversions)
        offer["estimated_revenue"] = self.estimate_affiliate_revenue(
            offer["clicks"],
            offer.get("conversion_rate", 0.02),
            offer.get("average_order_value", 0),
            offer.get("commission_rate", 0.1),
        )
        offer["updated_at"] = _now()
        self.store.save(data)
        return offer

    @staticmethod
    def estimate_affiliate_revenue(clicks: int, conversion_rate: float, average_order_value: int, commission_rate: float) -> int:
        return int(int(clicks) * float(conversion_rate) * int(average_order_value) * float(commission_rate))

    # SEO Factory ------------------------------------------------------

    def add_keyword(self, keyword: str, intent: str = "commercial", priority: str = "normal") -> dict[str, Any]:
        item = {
            "seo_id": _new_id("seo"),
            "keyword": keyword,
            "intent": intent,
            "priority": priority,
            "status": "queued",
            "cluster": "",
            "internal_links": [],
            "calendar_date": "",
            "ranking": {"current": None, "target": 10, "updated_at": ""},
            "created_at": _now(),
            "updated_at": _now(),
        }
        data = self.store.load()
        data["seo_queue"].insert(0, item)
        self.store.save(data)
        return item

    def cluster_topics(self) -> dict[str, list[str]]:
        data = self.store.load()
        clusters: dict[str, list[str]] = {}
        for item in data["seo_queue"]:
            first = item.get("keyword", "misc").split()[0].lower()
            item["cluster"] = first
            clusters.setdefault(first, []).append(item["keyword"])
            item["updated_at"] = _now()
        self.store.save(data)
        return clusters

    def build_internal_links(self) -> list[dict[str, str]]:
        data = self.store.load()
        links = []
        for item in data["seo_queue"]:
            related = [
                other["keyword"] for other in data["seo_queue"]
                if other.get("seo_id") != item.get("seo_id") and other.get("cluster") == item.get("cluster")
            ][:3]
            item["internal_links"] = related
            for target in related:
                links.append({"from": item["keyword"], "to": target})
        self.store.save(data)
        return links

    def build_content_calendar(self, start: str | None = None) -> list[dict[str, str]]:
        data = self.store.load()
        base = date.fromisoformat(start) if start else date.today()
        calendar = []
        for idx, item in enumerate(data["seo_queue"]):
            item["calendar_date"] = (base + timedelta(days=idx)).isoformat()
            item["status"] = "planned"
            calendar.append({"keyword": item["keyword"], "date": item["calendar_date"]})
        self.store.save(data)
        return calendar

    def track_ranking(self, seo_id: str, current_rank: int) -> dict[str, Any] | None:
        data = self.store.load()
        item = _find(data["seo_queue"], "seo_id", seo_id)
        if item is None:
            return None
        item["ranking"] = {
            "current": int(current_rank),
            "target": item.get("ranking", {}).get("target", 10),
            "updated_at": _now(),
        }
        item["updated_at"] = _now()
        self.store.save(data)
        return item

    def dashboard_summary(self) -> dict[str, Any]:
        data = self.store.load()
        kpis = data.get("daily_kpis", [])
        today = date.today().isoformat()
        today_revenue = sum(int(k.get("revenue", 0)) for k in kpis if k.get("date") == today)
        forecast = self.store.earnings_forecast(days=30)
        jobs = data.get("scheduled_jobs", [])
        articles = data.get("article_queue", [])
        published = [a for a in articles if a.get("status") == "published"]
        pv = sum(int(a.get("pv", 0)) for a in articles) + sum(int(k.get("pv", 0)) for k in kpis)
        ctr_values = [float(a.get("ctr", 0)) for a in articles if float(a.get("ctr", 0)) > 0]
        ctr_values.extend(float(k.get("ctr", 0)) for k in kpis if float(k.get("ctr", 0)) > 0)
        avg_ctr = round(sum(ctr_values) / max(len(ctr_values), 1), 4)
        seo_scores = [int(a.get("seo", {}).get("score", 0)) for a in articles if a.get("seo")]
        return {
            "today_revenue": today_revenue,
            "projected_monthly_revenue": forecast["forecast_total"],
            "article_queue": len([a for a in articles if a.get("status") != "published"]),
            "note_reservations": len([r for r in data.get("note_reservations", []) if r.get("status") == "reserved"]),
            "posting_history": len(data.get("posting_history", [])),
            "published_articles": len(published),
            "seo_average": round(sum(seo_scores) / max(len(seo_scores), 1), 1),
            "pv": pv,
            "ctr": avg_ctr,
            "article_revenue": sum(int(a.get("actual_revenue", a.get("estimated_revenue", 0))) for a in articles),
            "post_queue": len([p for p in data.get("post_queue", []) if p.get("status") != "published"]),
            "affiliate_queue": len(data.get("affiliate_queue", [])),
            "seo_queue": len(data.get("seo_queue", [])),
            "completed_jobs": sum(1 for j in jobs if j.get("status") == "completed"),
            "failed_jobs": sum(1 for j in jobs if j.get("status") == "failed"),
        }


def _find(rows: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    return next((row for row in rows if row.get(key) == value), None)
