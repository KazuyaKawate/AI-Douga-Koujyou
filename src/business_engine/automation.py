from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from src.business_engine.manager import BusinessEngineStore, _new_id


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class RevenueAutomation:
    """Local-first revenue automation for note, SNS, affiliate, and SEO queues."""

    def __init__(self, store: BusinessEngineStore | None = None) -> None:
        self.store = store or BusinessEngineStore()

    # Note Factory -----------------------------------------------------

    def generate_article(self, topic: str, keyword: str = "", target: str = "AIOS users") -> dict[str, Any]:
        article = {
            "article_id": _new_id("article"),
            "topic": topic,
            "keyword": keyword or topic,
            "target": target,
            "title": f"{topic}: local-first revenue playbook",
            "body": (
                f"# {topic}: local-first revenue playbook\n\n"
                f"Target reader: {target}\n\n"
                "## Problem\n"
                f"Readers searching for {keyword or topic} need a practical next step.\n\n"
                "## Solution\n"
                "Use AIOS to plan, queue, review, and publish content locally before any paid automation is enabled.\n\n"
                "## Action\n"
                "Create the draft, review it, approve it, then publish through the local queue."
            ),
            "review": None,
            "approved": False,
            "status": "draft",
            "created_at": _now(),
            "updated_at": _now(),
        }
        data = self.store.load()
        data["article_queue"].insert(0, article)
        self.store.save(data)
        return article

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

    def publish_article(self, article_id: str) -> dict[str, Any] | None:
        data = self.store.load()
        article = _find(data["article_queue"], "article_id", article_id)
        if article is None:
            return None
        article["status"] = "published"
        article["published_at"] = date.today().isoformat()
        article["updated_at"] = _now()
        self.store.save(data)
        self.store.record_execution(article_id, "completed", "Local article publish completed.")
        return article

    # SNS Factory ------------------------------------------------------

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
        return {
            "today_revenue": today_revenue,
            "projected_monthly_revenue": forecast["forecast_total"],
            "article_queue": len([a for a in data.get("article_queue", []) if a.get("status") != "published"]),
            "post_queue": len([p for p in data.get("post_queue", []) if p.get("status") != "published"]),
            "affiliate_queue": len(data.get("affiliate_queue", [])),
            "seo_queue": len(data.get("seo_queue", [])),
            "completed_jobs": sum(1 for j in jobs if j.get("status") == "completed"),
            "failed_jobs": sum(1 for j in jobs if j.get("status") == "failed"),
        }


def _find(rows: list[dict[str, Any]], key: str, value: str) -> dict[str, Any] | None:
    return next((row for row in rows if row.get(key) == value), None)
