from __future__ import annotations

import html
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.business_engine.manager import BusinessEngineStore
from src.core.development_constitution import load_development_constitution
from src.official_site import site_manager
from src.self_builder.knowledge_manager import load_knowledge
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


WEBSITE_STATE_PATH = PROJECT_ROOT / "config" / "official_website.json"
WEBSITE_OUTPUT_DIR = PROJECT_ROOT / "output" / "official_website"
REVENUE_DASHBOARD_PATH = PROJECT_ROOT / "config" / "revenue_engine.json"
CONTENT_FACTORY_PATH = PROJECT_ROOT / "config" / "content_factory.json"
DEFAULT_SITE_URL = site_manager.DEFAULT_SITE_URL


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _slug(value: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    return "-".join(part for part in normalized.split("-") if part) or "page"


def _default_state() -> dict[str, Any]:
    return {
        "brand": {
            "name": "AIOS",
            "tagline": "Autonomous Business OS",
            "site_url": DEFAULT_SITE_URL,
            "dark_mode": True,
        },
        "analytics": {
            "pv": 0,
            "ctr": 0,
            "revenue": 0,
            "contact_count": 0,
            "registered_users": 0,
        },
        "contacts": [],
        "users": [],
        "admin_events": [],
        "release_notes": [],
        "mission_feedback": [],
        "last_build": {},
        "updated_at": _now(),
    }


def load_website_state(path: str | Path = WEBSITE_STATE_PATH) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return _default_state()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return _default_state()
    if not isinstance(data, dict):
        return _default_state()
    defaults = _default_state()
    for key, value in defaults.items():
        data.setdefault(key, value)
    data.setdefault("brand", {})
    for key, value in defaults["brand"].items():
        data["brand"].setdefault(key, value)
    data.setdefault("analytics", {})
    for key, value in defaults["analytics"].items():
        data["analytics"].setdefault(key, value)
    return data


def save_website_state(state: dict[str, Any], path: str | Path = WEBSITE_STATE_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now()
    save_json_atomic(p, state)


class WebsiteEngine:
    """Static official website builder that turns AIOS business state into a hub."""

    def __init__(
        self,
        store: BusinessEngineStore | None = None,
        *,
        state_path: str | Path = WEBSITE_STATE_PATH,
        output_dir: str | Path = WEBSITE_OUTPUT_DIR,
        revenue_state_path: str | Path = REVENUE_DASHBOARD_PATH,
        content_state_path: str | Path = CONTENT_FACTORY_PATH,
    ) -> None:
        self.store = store or BusinessEngineStore()
        self.state_path = Path(state_path)
        self.output_dir = Path(output_dir)
        self.revenue_state_path = Path(revenue_state_path)
        self.content_state_path = Path(content_state_path)

    def load_state(self) -> dict[str, Any]:
        return load_website_state(self.state_path)

    def save_state(self, state: dict[str, Any]) -> None:
        save_website_state(state, self.state_path)

    def build_site(self, site_url: str = DEFAULT_SITE_URL) -> dict[str, Any]:
        return self.build_site_with_release(site_url)

    def build_site_with_release(
        self,
        site_url: str = DEFAULT_SITE_URL,
        release_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = self.store.load()
        knowledge = load_knowledge()
        state = self.load_state()
        site_url = site_url or state.get("brand", {}).get("site_url", DEFAULT_SITE_URL)
        context = self.build_context(data, knowledge, state, site_url, release_settings or {})

        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "blog").mkdir(exist_ok=True)
        (self.output_dir / "docs").mkdir(exist_ok=True)
        (self.output_dir / "assets").mkdir(exist_ok=True)

        written: dict[str, str] = {}
        self.write_assets(context)
        for page in self.core_pages(context):
            path = self.output_dir / page["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self.render_page(page["title"], page["body"], page["description"], context, page["path"]), encoding="utf-8")
            written[page["name"]] = str(path)

        for article in context["articles"]:
            path = self.output_dir / "blog" / f"{_slug(article.get('title', article.get('article_id', 'article')))}.html"
            path.write_text(self.render_article(article, context), encoding="utf-8")
            written[f"blog_{article.get('article_id', _slug(article.get('title', 'article')))}"] = str(path)

        release_note = self.generate_release_note(context)
        release_path = self.output_dir / "release-notes.html"
        release_path.write_text(
            self.render_page("Release Notes", release_note, "AIOS release notes and update history", context, "release-notes.html"),
            encoding="utf-8",
        )
        written["release_notes"] = str(release_path)

        knowledge_article = self.generate_knowledge_public_article(knowledge)
        knowledge_path = self.output_dir / "docs" / "knowledge.html"
        knowledge_path.write_text(
            self.render_page("Knowledge Base", knowledge_article, "Public AIOS knowledge article", context, "docs/knowledge.html"),
            encoding="utf-8",
        )
        written["knowledge"] = str(knowledge_path)

        written.update(self.write_artifacts(context))
        state["last_build"] = {
            "build_id": f"web-{uuid4().hex[:10]}",
            "site_url": site_url,
            "written": written,
            "created_at": _now(),
        }
        state["analytics"] = context["analytics"]
        state.setdefault("release_notes", []).insert(0, {"title": "AIOS Website build", "created_at": _now()})
        state.setdefault("mission_feedback", []).insert(0, self.mission_planner_feedback(context))
        self.save_state(state)
        return {"written": written, "context": context, "state": state}

    def build_phase5_release(self, settings: dict[str, Any]) -> dict[str, Any]:
        release = settings.get("release", {})
        site_url = str(release.get("domain_url") or DEFAULT_SITE_URL)
        build = self.build_site_with_release(site_url, release)
        deploy_plan = self.write_deploy_plan(release, build["written"])
        review = self.pre_publication_review(release, build["written"], build["context"])
        state = self.load_state()
        state["phase5_release"] = {
            "status": "review_required",
            "dry_run": True,
            "local_first": True,
            "site_url": site_url,
            "deploy_plan": deploy_plan,
            "review": review,
            "auto_update": {
                "source": "Business Engine + Content Factory",
                "trigger": "run WebsiteEngine.build_phase5_release after article additions",
                "enabled": True,
            },
            "created_at": _now(),
        }
        self.save_state(state)
        return {"build": build, "deploy_plan": deploy_plan, "review": review, "state": state}

    def build_context(
        self,
        data: dict[str, Any],
        knowledge: dict[str, Any],
        state: dict[str, Any],
        site_url: str,
        release_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        release_settings = release_settings or {}
        articles = list(data.get("article_queue", []))
        content_state = self.load_content_factory_state()
        content_articles = self.content_factory_articles(content_state)
        articles = content_articles + articles
        threads = [row for row in data.get("post_queue", []) if row.get("platform") == "threads"]
        threads = self.content_factory_threads(content_state) + threads
        revenue_state = self.load_revenue_dashboard_state()
        pipeline = self.store.pipeline_summary()
        phase1 = self.store.business_phase1_dashboard()
        analytics = self.analytics_summary(data, state)
        constitution = load_development_constitution()
        return {
            "site_url": site_url.rstrip("/"),
            "brand": state.get("brand", {}),
            "release": release_settings,
            "articles": articles,
            "threads": threads,
            "latest_articles": self.latest_articles(articles),
            "popular_articles": self.popular_articles(articles, threads),
            "note_articles": [row for row in articles if row.get("type") == "note" or row.get("category") == "note"],
            "official_articles": [row for row in articles if row.get("type") == "official_site_article" or row.get("category") == "official_site"],
            "content_factory": {
                "contents": content_state.get("contents", []),
                "drafts": content_state.get("drafts", []),
                "history": content_state.get("history", []),
            },
            "releases": [*state.get("release_notes", [])[:10], *data.get("execution_history", [])[:10]],
            "knowledge": knowledge,
            "business": {
                "pipeline": pipeline,
                "phase1": phase1,
                "revenue_pipeline": data.get("revenue_pipeline", []),
                "affiliate_queue": data.get("affiliate_queue", []),
                "scheduled_jobs": data.get("scheduled_jobs", []),
            },
            "publishing_hub": self.publishing_hub(data, revenue_state, analytics, pipeline),
            "continuous": self.continuous_summary(),
            "analytics": analytics,
            "development_constitution": constitution,
            "search_index": self.search_index(articles, knowledge),
        }

    def load_revenue_dashboard_state(self) -> dict[str, Any]:
        data = load_json(self.revenue_state_path, default={})
        return data if isinstance(data, dict) else {}

    def load_content_factory_state(self) -> dict[str, Any]:
        data = load_json(self.content_state_path, default={})
        return data if isinstance(data, dict) else {}

    def content_factory_articles(self, content_state: dict[str, Any]) -> list[dict[str, Any]]:
        articles: list[dict[str, Any]] = []
        for item in content_state.get("contents", []):
            content_type = item.get("type")
            if content_type not in {"note", "official_site_article", "landing_page"}:
                continue
            article = dict(item)
            article.setdefault("article_id", article.get("content_id", _slug(str(article.get("title", "content")))))
            article.setdefault("title", article.get("topic") or article.get("offer") or "AIOS Content")
            article.setdefault("category", "official_site" if content_type == "official_site_article" else content_type)
            article.setdefault("status", "draft")
            articles.append(article)
        return articles

    def content_factory_threads(self, content_state: dict[str, Any]) -> list[dict[str, Any]]:
        threads: list[dict[str, Any]] = []
        for item in content_state.get("contents", []):
            if item.get("type") != "threads":
                continue
            thread = dict(item)
            thread.setdefault("thread_id", thread.get("content_id", _slug(str(thread.get("title", "thread")))))
            thread.setdefault("platform", "threads")
            thread.setdefault("status", "draft")
            threads.append(thread)
        return threads

    def latest_articles(self, articles: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
        return sorted(
            articles,
            key=lambda row: str(row.get("updated_at") or row.get("created_at") or ""),
            reverse=True,
        )[:limit]

    def popular_articles(self, articles: list[dict[str, Any]], threads: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
        rows = [*articles, *threads]
        return sorted(
            rows,
            key=lambda row: int(row.get("pv", 0) or 0) + int(float(row.get("ctr", 0) or 0) * 10000),
            reverse=True,
        )[:limit]

    def publishing_hub(
        self,
        data: dict[str, Any],
        revenue_state: dict[str, Any],
        analytics: dict[str, Any],
        pipeline: dict[str, Any],
    ) -> dict[str, Any]:
        note_drafts = list(revenue_state.get("note_draft_saves", []))
        threads_waiting = list(revenue_state.get("threads_waiting_posts", []))
        public_history = [
            *data.get("posting_history", []),
            *data.get("threads_history", []),
            *revenue_state.get("publish_history", []),
        ]
        return {
            "dry_run": any(bool(row.get("dry_run")) for row in [*note_drafts, *threads_waiting]) or not public_history,
            "note_drafts": note_drafts,
            "threads_waiting": threads_waiting,
            "approval_candidates": list(revenue_state.get("publish_approval_candidates", [])),
            "approval_history": list(revenue_state.get("publish_approval_history", [])),
            "public_history": public_history[:20],
            "revenue_stats": {
                "revenue": analytics.get("revenue", 0),
                "weighted_forecast": pipeline.get("weighted_forecast", 0),
                "forecast": revenue_state.get("forecasts", {}),
                "roi_count": len(revenue_state.get("roi_ranking", [])),
            },
        }

    def analytics_summary(self, data: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        articles = data.get("article_queue", [])
        threads = [row for row in data.get("post_queue", []) if row.get("platform") == "threads"]
        pv = sum(int(row.get("pv", 0)) for row in articles) + sum(int(row.get("pv", 0)) for row in threads)
        ctr_values = [float(row.get("ctr", 0)) for row in [*articles, *threads] if float(row.get("ctr", 0)) > 0]
        revenue = sum(int(row.get("actual_revenue", row.get("estimated_revenue", 0))) for row in articles)
        return {
            "pv": pv,
            "ctr": round(sum(ctr_values) / max(len(ctr_values), 1), 4),
            "revenue": revenue + int(self.store.pipeline_summary().get("weighted_forecast", 0)),
            "contact_count": len(state.get("contacts", [])),
            "registered_users": len(state.get("users", [])),
        }

    def continuous_summary(self) -> dict[str, Any]:
        path = PROJECT_ROOT / "config" / "self_builder_continuous.json"
        if not path.exists():
            return {"enabled": False, "version": "", "roi": 0}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"enabled": False, "version": "", "roi": 0}
        return {
            "enabled": bool(data.get("enabled")),
            "version": data.get("version", {}).get("current", ""),
            "roi": sum(int(row.get("roi", 0)) for row in data.get("roi_trend", [])),
        }

    def core_pages(self, context: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {"name": "home", "path": "index.html", "title": "AIOS Official Website", "description": "AIOS official business hub", "body": self.home_body(context)},
            {"name": "about", "path": "about.html", "title": "About AIOS", "description": "About AIOS", "body": self.about_body(context)},
            {"name": "features", "path": "features.html", "title": "Features", "description": "AIOS features", "body": self.features_body(context)},
            {"name": "start", "path": "start.html", "title": "Get Started", "description": "Start using AIOS", "body": self.start_body()},
            {"name": "pricing", "path": "pricing.html", "title": "Pricing", "description": "AIOS pricing", "body": self.pricing_body()},
            {"name": "blog", "path": "blog.html", "title": "Blog", "description": "AIOS blog", "body": self.blog_body(context)},
            {"name": "notes", "path": "notes.html", "title": "note Articles", "description": "AIOS note articles", "body": self.note_articles_body(context)},
            {"name": "threads", "path": "threads.html", "title": "Threads Posts", "description": "AIOS Threads posts", "body": self.threads_list_body(context)},
            {"name": "docs", "path": "docs.html", "title": "Docs", "description": "AIOS docs", "body": self.docs_body(context)},
            {"name": "contact", "path": "contact.html", "title": "Contact", "description": "Contact AIOS", "body": self.contact_body()},
            {"name": "updates", "path": "updates.html", "title": "Update History", "description": "AIOS update history", "body": self.updates_body(context)},
            {"name": "dashboard", "path": "dashboard.html", "title": "AIOS Dashboard", "description": "AIOS Business dashboard", "body": self.dashboard_body(context)},
            {"name": "admin", "path": "admin.html", "title": "Admin Dashboard", "description": "AIOS admin dashboard", "body": self.admin_body(context)},
        ]

    def render_page(self, title: str, body: str, description: str, context: dict[str, Any], path: str) -> str:
        brand = context["brand"]
        release = context.get("release", {})
        escaped_title = html.escape(title)
        desc = html.escape(self.optimize_description(description))
        canonical = f"{context['site_url']}/{path}"
        ga_id = str(release.get("google_analytics_id") or "").strip()
        gsc_token = str(release.get("search_console_verification") or "").strip()
        return (
            "<!doctype html>\n<html lang=\"ja\" data-theme=\"dark\">\n<head>\n"
            "  <meta charset=\"utf-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            f"  <title>{escaped_title} | {html.escape(brand.get('name', 'AIOS'))}</title>\n"
            f"  <meta name=\"description\" content=\"{desc}\">\n"
            f"  <link rel=\"canonical\" href=\"{html.escape(canonical)}\">\n"
            f"{self.gsc_meta(gsc_token)}"
            f"  <meta property=\"og:title\" content=\"{escaped_title}\">\n"
            f"  <meta property=\"og:description\" content=\"{desc}\">\n"
            "  <meta property=\"og:type\" content=\"website\">\n"
            f"  <meta property=\"og:image\" content=\"{context['site_url']}/assets/ogp.svg\">\n"
            "  <meta name=\"twitter:card\" content=\"summary_large_image\">\n"
            "  <link rel=\"stylesheet\" href=\"/assets/website.css\">\n"
            "  <script defer src=\"/assets/search.js\"></script>\n"
            f"{self.ga_script(ga_id)}"
            "</head>\n<body>\n"
            f"{self.nav(brand)}\n<main>{body}</main>\n<footer>AIOS Business Hub / Generated by Website Engine</footer>\n"
            "</body>\n</html>\n"
        )

    def render_article(self, article: dict[str, Any], context: dict[str, Any]) -> str:
        body = (
            f"<article class=\"panel\"><h1>{html.escape(str(article.get('title', 'Untitled')))}</h1>"
            f"<p class=\"muted\">{html.escape(str(article.get('keyword') or article.get('topic') or 'AIOS'))}</p>"
            f"{self.markdown_to_html(str(article.get('body') or article.get('text') or ''))}</article>"
        )
        return self.render_page(str(article.get("title", "Untitled")), body, str(article.get("topic") or ""), context, f"blog/{_slug(str(article.get('title', 'article')))}.html")

    def nav(self, brand: dict[str, Any]) -> str:
        links = ["Home", "About", "Features", "Start", "Pricing", "Blog", "note", "Threads", "Contact", "Updates"]
        hrefs = ["index", "about", "features", "start", "pricing", "blog", "notes", "threads", "contact", "updates"]
        return (
            "<header><strong>" + html.escape(brand.get("name", "AIOS")) + "</strong><nav>"
            + "".join(f'<a href="/{href}.html">{label}</a>' for label, href in zip(links, hrefs))
            + "</nav></header>"
        )

    def home_body(self, context: dict[str, Any]) -> str:
        return (
            "<section class=\"hero\"><h1>AIOS Business Hub</h1><p>全サービス、収益、分析、自己進化を統合する公式サイト。</p>"
            "<a class=\"button\" href=\"/start.html\">利用開始</a> <a class=\"button ghost\" href=\"/pricing.html\">料金を見る</a></section>"
            + self.top_revenue_panel(context)
            + "<section><h2>最新記事</h2><div class=\"grid\">"
            + "".join(self.article_card(article) for article in context["latest_articles"])
            + "</div></section>"
            + "<section><h2>人気記事</h2><div class=\"grid\">"
            + "".join(self.article_card(article) for article in context["popular_articles"])
            + "</div></section>"
            + self.threads_embed(context)
        )

    def about_body(self, context: dict[str, Any]) -> str:
        return "<section class=\"panel\"><h1>About AIOS</h1><p>AIOSは制作、収益化、分析、改善をつなぐ自律型Business OSです。</p></section>"

    def features_body(self, context: dict[str, Any]) -> str:
        features = ["Business Engine", "Content Factory", "公式サイト自動反映", "Threads Automation", "Revenue KPI"]
        return "<section class=\"grid\">" + "".join(f"<div class=\"panel\"><h2>{html.escape(item)}</h2><p>AIOS Hubに統合済み。</p></div>" for item in features) + "</section>"

    def start_body(self) -> str:
        steps = ["記事ネタを登録", "Content Factoryで下書きを生成", "Business EngineでKPIを確認", "公式サイトへDryRun反映"]
        return "<section class=\"panel\"><h1>利用開始</h1><p>Local FirstでAIOSの収益導線を小さく開始します。</p>" + "".join(f"<h2>{idx}. {html.escape(step)}</h2>" for idx, step in enumerate(steps, 1)) + "</section>"

    def pricing_body(self) -> str:
        plans = [("Free", "Local-first operations / 将来用"), ("Pro", "Automation and analytics / 将来用"), ("Business", "Hub and release operations / 将来用")]
        return "<section class=\"grid\">" + "".join(f"<div class=\"panel\"><h2>{name}</h2><p>{desc}</p></div>" for name, desc in plans) + "</section>"

    def blog_body(self, context: dict[str, Any]) -> str:
        return '<section class="panel"><h1>Blog</h1><input placeholder="検索" oninput="filterCards(this.value)"></section><section class="grid">' + "".join(self.article_card(article) for article in context["articles"]) + "</section>"

    def note_articles_body(self, context: dict[str, Any]) -> str:
        return '<section class="panel"><h1>note記事一覧</h1><p>Content FactoryとBusiness Engineから同期されたnote下書き・記事です。</p></section><section class="grid">' + "".join(self.article_card(article) for article in context["note_articles"]) + "</section>"

    def threads_list_body(self, context: dict[str, Any]) -> str:
        return "<section class=\"panel\"><h1>Threads記事一覧</h1><p>Threads投稿下書きと反応確認用の一覧です。</p></section><section class=\"grid\">" + "".join(f"<div class=\"panel card\"><h2>{html.escape(str(row.get('title') or row.get('topic') or 'Threads'))}</h2><p>{html.escape(str(row.get('text', ''))[:300])}</p><p class=\"muted\">PV {int(row.get('pv', 0) or 0)} / CTR {float(row.get('ctr', 0) or 0)}</p></div>" for row in context["threads"]) + "</section>"

    def docs_body(self, context: dict[str, Any]) -> str:
        return "<section class=\"panel\"><h1>Docs</h1><p>AIOSの運用ドキュメント、Knowledge公開記事、Release Noteを掲載します。</p><a href=\"/docs/knowledge.html\">Knowledge公開記事</a></section>"

    def contact_body(self) -> str:
        return "<section class=\"panel\"><h1>Contact</h1><form><input name=\"name\" placeholder=\"Name\"><input name=\"email\" placeholder=\"Email\"><textarea name=\"message\" placeholder=\"Message\"></textarea><button>問い合わせ</button></form></section>"

    def updates_body(self, context: dict[str, Any]) -> str:
        return self.generate_release_note(context)

    def dashboard_body(self, context: dict[str, Any]) -> str:
        return (
            "<section class=\"hero\"><h1>AIOS Dashboard</h1></section>"
            + self.metric_grid(context)
            + self.publish_waiting_body(context)
            + self.revenue_hub_body(context)
            + self.affiliate_body(context)
        )

    def admin_body(self, context: dict[str, Any]) -> str:
        return (
            "<section class=\"panel\"><h1>管理者Dashboard</h1>"
            f"<p>記事: {len(context['articles'])} / Threads: {len(context['threads'])} / Jobs: {len(context['business']['scheduled_jobs'])}</p>"
            f"<pre>{html.escape(json.dumps(context['continuous'], ensure_ascii=False, indent=2))}</pre></section>"
        )

    def metric_grid(self, context: dict[str, Any]) -> str:
        analytics = context["analytics"]
        pipeline = context["business"]["pipeline"]
        rows = [
            ("PV", analytics["pv"]),
            ("CTR", analytics["ctr"]),
            ("Revenue", f"¥{analytics['revenue']:,}"),
            ("Pipeline", f"¥{int(pipeline.get('weighted_forecast', 0)):,}"),
            ("Continuous ROI", context["continuous"].get("roi", 0)),
        ]
        return "<section class=\"grid\">" + "".join(f"<div class=\"metric\"><span>{name}</span><strong>{value}</strong></div>" for name, value in rows) + "</section>"

    def top_revenue_panel(self, context: dict[str, Any]) -> str:
        phase1 = context["business"].get("phase1", {})
        analytics = context["analytics"]
        rows = [
            ("収益KPI", f"¥{int(analytics.get('revenue', 0)):,}"),
            ("初収益までの進捗", f"{int(phase1.get('first_revenue_progress_rate', 0))}%"),
            ("PV", int(phase1.get("pv", analytics.get("pv", 0)) or 0)),
            ("クリック率", phase1.get("click_rate", analytics.get("ctr", 0))),
        ]
        return "<section><h2>Business Engine KPI</h2><div class=\"grid\">" + "".join(f"<div class=\"metric\"><span>{html.escape(name)}</span><strong>{html.escape(str(value))}</strong></div>" for name, value in rows) + "</div></section>"

    def affiliate_body(self, context: dict[str, Any]) -> str:
        return "<section class=\"panel\"><h2>Affiliate管理</h2>" + "".join(f"<p>{html.escape(str(item.get('title', item.get('offer_title', 'Affiliate'))))}</p>" for item in context["business"]["affiliate_queue"][:5]) + "</section>"

    def publish_waiting_body(self, context: dict[str, Any]) -> str:
        hub = context["publishing_hub"]
        note_rows = hub["note_drafts"][:10]
        threads_rows = hub["threads_waiting"][:10]
        return (
            "<section class=\"panel\"><h2>公開待ち一覧</h2>"
            f"<p>DryRun: {html.escape(str(hub['dry_run']))}</p>"
            "<h3>note下書き一覧</h3>"
            + (self.publish_rows(note_rows, "title", "save_url") or "<p>note下書きはありません。</p>")
            + "<h3>Threads待機一覧</h3>"
            + (self.publish_rows(threads_rows, "text", "note_save_url") or "<p>Threads待機はありません。</p>")
            + "<h3>承認待ち</h3>"
            + (self.approval_rows(hub["approval_candidates"][:10]) or "<p>承認待ちはありません。</p>")
            + "<h3>Publish Queue</h3>"
            + (self.approval_rows(hub["approval_history"][:10]) or "<p>Publish Queue移動済みはありません。</p>")
            + "</section>"
        )

    def revenue_hub_body(self, context: dict[str, Any]) -> str:
        hub = context["publishing_hub"]
        stats = hub["revenue_stats"]
        history = hub["public_history"][:10]
        return (
            "<section class=\"panel\"><h2>Revenue統計</h2>"
            f"<p>Revenue: ¥{int(stats.get('revenue', 0)):,}</p>"
            f"<p>Weighted Forecast: ¥{int(stats.get('weighted_forecast', 0)):,}</p>"
            f"<p>ROI候補: {int(stats.get('roi_count', 0))}</p>"
            "<h3>公開履歴</h3>"
            + (self.publish_rows(history, "title", "status") or "<p>公開履歴はありません。</p>")
            + "</section>"
        )

    def publish_rows(self, rows: list[dict[str, Any]], title_key: str, meta_key: str) -> str:
        return "".join(
            "<div class=\"publish-row\">"
            f"<strong>{html.escape(str(row.get(title_key) or row.get('note_title') or row.get('thread_id') or row.get('article_id') or 'Untitled')[:180])}</strong>"
            f"<span>{html.escape(str(row.get(meta_key) or row.get('created_at') or row.get('recorded_at') or '')[:220])}</span>"
            "</div>"
            for row in rows
        )

    def approval_rows(self, rows: list[dict[str, Any]]) -> str:
        return "".join(
            "<div class=\"publish-row\">"
            f"<strong>{html.escape(str(row.get('title') or row.get('platform') or '公開候補')[:180])}</strong>"
            f"<span>{html.escape(str(row.get('status', 'approval_waiting')))} / {html.escape(str(row.get('platform', '')))} / DryRun: {html.escape(str(row.get('dry_run', True)))}</span>"
            f"<button data-action=\"approve-publish\" data-candidate-id=\"{html.escape(str(row.get('candidate_id', '')))}\">公開承認</button>"
            "</div>"
            for row in rows
        )

    def threads_embed(self, context: dict[str, Any]) -> str:
        return "<section><h2>Threads</h2><div class=\"grid\">" + "".join(f"<div class=\"panel\"><p>{html.escape(str(row.get('text', ''))[:240])}</p></div>" for row in context["threads"][:6]) + "</div></section>"

    def article_card(self, article: dict[str, Any]) -> str:
        title = str(article.get("title", "Untitled"))
        return f'<div class="panel card"><h2><a href="/blog/{_slug(title)}.html">{html.escape(title)}</a></h2><p>{html.escape(str(article.get("topic") or article.get("keyword") or ""))}</p><p class="muted">PV {int(article.get("pv", 0) or 0)} / CTR {float(article.get("ctr", 0) or 0)}</p></div>'

    def generate_release_note(self, context: dict[str, Any]) -> str:
        rows = context["releases"][:20]
        return "<section class=\"panel\"><h1>Release Notes</h1>" + "".join(f"<p>{html.escape(str(row.get('created_at', '')))} - {html.escape(str(row.get('message', row.get('title', 'Update'))))}</p>" for row in rows) + "</section>"

    def generate_knowledge_public_article(self, knowledge: dict[str, Any]) -> str:
        items = knowledge.get("improvement_examples", [])[:10]
        return "<section class=\"panel\"><h1>Knowledge公開記事</h1>" + "".join(f"<p>{html.escape(str(item.get('title', item.get('type', 'Knowledge'))))}</p>" for item in items) + "</section>"

    def search_index(self, articles: list[dict[str, Any]], knowledge: dict[str, Any]) -> list[dict[str, str]]:
        rows = [{"title": str(article.get("title", "")), "url": f"/blog/{_slug(str(article.get('title', 'article')))}.html", "type": "article"} for article in articles]
        rows.extend({"title": str(item.get("title", item.get("type", "Knowledge"))), "url": "/docs/knowledge.html", "type": "knowledge"} for item in knowledge.get("improvement_examples", [])[:20])
        return rows

    def optimize_description(self, description: str) -> str:
        base = description.strip() or "AIOS Business Hub"
        return (base + " | AIOS official website").strip()[:155]

    def markdown_to_html(self, markdown: str) -> str:
        html_lines = []
        for line in markdown.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                html_lines.append(f"<h1>{html.escape(stripped[2:])}</h1>")
            elif stripped.startswith("## "):
                html_lines.append(f"<h2>{html.escape(stripped[3:])}</h2>")
            elif stripped:
                html_lines.append(f"<p>{html.escape(stripped)}</p>")
        return "\n".join(html_lines)

    def write_assets(self, context: dict[str, Any]) -> None:
        assets = self.output_dir / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        (assets / "website.css").write_text(
            "body{margin:0;background:#0b1020;color:#eef4ff;font-family:system-ui,sans-serif;line-height:1.7;}"
            "header,main,footer{max-width:1180px;margin:auto;padding:22px;}header{display:flex;justify-content:space-between;gap:16px;align-items:center;}"
            "nav a{color:#b8ddff;margin-left:12px;text-decoration:none}.hero{padding:54px 22px}.panel,.metric{background:#141b34;border:1px solid #263454;border-radius:8px;padding:18px;margin:12px 0;}"
            ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.metric span{display:block;color:#93a4c7}.metric strong{font-size:28px}.button,button{background:#5eead4;color:#07111f;padding:12px 16px;border-radius:8px;text-decoration:none;border:0;font-weight:700}"
            ".publish-row{border-top:1px solid #263454;padding:10px 0}.publish-row strong,.publish-row span{display:block}.publish-row span{color:#93a4c7;font-size:14px}"
            "input,textarea{width:100%;box-sizing:border-box;background:#0b1020;color:#eef4ff;border:1px solid #263454;border-radius:8px;padding:12px;margin:8px 0}@media(max-width:720px){header{display:block}nav a{display:inline-block;margin:6px 8px 0 0}}",
            encoding="utf-8",
        )
        (assets / "search.js").write_text(
            "function filterCards(q){q=(q||'').toLowerCase();document.querySelectorAll('.card').forEach(c=>c.style.display=c.innerText.toLowerCase().includes(q)?'':'none')}",
            encoding="utf-8",
        )
        (assets / "ogp.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630"><rect width="1200" height="630" fill="#0b1020"/><text x="80" y="300" fill="#5eead4" font-size="90" font-family="Arial" font-weight="700">AIOS</text><text x="84" y="380" fill="#eef4ff" font-size="38" font-family="Arial">Autonomous Business OS</text></svg>',
            encoding="utf-8",
        )

    def write_artifacts(self, context: dict[str, Any]) -> dict[str, str]:
        search_path = self.output_dir / "search.json"
        search_path.write_text(json.dumps(context["search_index"], ensure_ascii=False, indent=2), encoding="utf-8")
        sitemap_path = self.output_dir / "sitemap.xml"
        urls = [
            "index.html",
            "about.html",
            "features.html",
            "start.html",
            "pricing.html",
            "blog.html",
            "notes.html",
            "threads.html",
            "docs.html",
            "contact.html",
            "updates.html",
            "dashboard.html",
            "admin.html",
            "release-notes.html",
            "docs/knowledge.html",
        ]
        urls.extend(f"blog/{_slug(str(article.get('title', 'article')))}.html" for article in context["articles"])
        sitemap_path.write_text(
            '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(f"<url><loc>{html.escape(context['site_url'] + '/' + url)}</loc><lastmod>{date.today().isoformat()}</lastmod></url>" for url in urls)
            + "</urlset>",
            encoding="utf-8",
        )
        rss_path = self.output_dir / "rss.xml"
        rss_path.write_text(
            '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>AIOS</title>'
            + "".join(f"<item><title>{html.escape(str(article.get('title', 'Untitled')))}</title><link>{context['site_url']}/blog/{_slug(str(article.get('title', 'article')))}.html</link></item>" for article in context["articles"])
            + "</channel></rss>",
            encoding="utf-8",
        )
        robots_path = self.output_dir / "robots.txt"
        robots_path.write_text(f"User-agent: *\nAllow: /\nSitemap: {context['site_url']}/sitemap.xml\n", encoding="utf-8")
        written = {"search": str(search_path), "sitemap": str(sitemap_path), "rss": str(rss_path), "robots": str(robots_path)}
        gsc_file = self.write_search_console_file(context.get("release", {}))
        if gsc_file:
            written["google_search_console"] = gsc_file
        return written

    def write_search_console_file(self, release: dict[str, Any]) -> str:
        filename = str(release.get("search_console_file") or "").strip()
        content = str(release.get("search_console_file_content") or "").strip()
        if not filename:
            token = str(release.get("search_console_verification") or "").strip()
            if not token:
                return ""
            filename = "google-site-verification.html"
            content = f"google-site-verification: {token}"
        safe_name = Path(filename).name
        if not safe_name.endswith(".html"):
            safe_name += ".html"
        path = self.output_dir / safe_name
        path.write_text(content or f"google-site-verification: {safe_name}", encoding="utf-8")
        return str(path)

    def write_deploy_plan(self, release: dict[str, Any], written: dict[str, str]) -> dict[str, str]:
        deploy_dir = self.output_dir / "deploy"
        deploy_dir.mkdir(parents=True, exist_ok=True)
        domain = str(release.get("domain_url") or DEFAULT_SITE_URL).replace("https://", "").replace("http://", "").strip("/")
        vps_host = str(release.get("vps_host") or "your-vps-host").strip()
        vps_user = str(release.get("vps_user") or "deploy").strip()
        web_root = str(release.get("vps_web_root") or "/var/www/aios").strip()
        nginx = (
            "server {\n"
            "    listen 80;\n"
            f"    server_name {domain};\n"
            f"    root {web_root};\n"
            "    index index.html;\n"
            "    location / { try_files $uri $uri/ /index.html; }\n"
            "}\n"
        )
        commands = (
            "# DryRun only. Review before running on VPS.\n"
            f"rsync -avz --dry-run {self.output_dir}/ {vps_user}@{vps_host}:{web_root}/\n"
            f"ssh {vps_user}@{vps_host} 'sudo nginx -t'\n"
            f"ssh {vps_user}@{vps_host} 'sudo certbot --nginx -d {domain} --dry-run'\n"
        )
        checklist = {
            "vps_publication": bool(vps_host and vps_host != "your-vps-host"),
            "domain": domain != "example.com",
            "https": str(release.get("domain_url", "")).startswith("https://"),
            "top_page": "home" in written,
            "article_list": "blog" in written,
            "sitemap": "sitemap" in written,
            "robots": "robots" in written,
            "rss": "rss" in written,
            "gsc_file": bool(written.get("google_search_console")),
            "ga": bool(release.get("google_analytics_id")),
            "auto_update_source": True,
        }
        nginx_path = deploy_dir / "nginx_aios.conf"
        commands_path = deploy_dir / "dryrun_deploy_commands.txt"
        checklist_path = deploy_dir / "phase5_release_checklist.json"
        nginx_path.write_text(nginx, encoding="utf-8")
        commands_path.write_text(commands, encoding="utf-8")
        checklist_path.write_text(json.dumps(checklist, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"nginx": str(nginx_path), "commands": str(commands_path), "checklist": str(checklist_path), "mode": "dry_run"}

    def pre_publication_review(
        self,
        release: dict[str, Any],
        written: dict[str, str],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        context = context or {}
        site_url = str(release.get("domain_url") or context.get("site_url") or DEFAULT_SITE_URL)
        articles = list(context.get("articles", []))
        published_articles = [
            row for row in articles
            if str(row.get("status", "")).lower() in {"published", "posted", "public"}
        ]
        unpublished_articles = [row for row in articles if row not in published_articles]
        domain = site_url.replace("https://", "").replace("http://", "").strip("/")
        required = {
            "site_url": bool(site_url.strip()),
            "custom_domain": site_url.startswith("https://") and domain != "example.com",
            "https": site_url.startswith("https://"),
            "vps_publication": bool(str(release.get("vps_host") or "").strip()),
            "seo": self.html_contains("home", written, ['name="description"', 'rel="canonical"']),
            "ogp": self.html_contains("home", written, ['property="og:image"', 'twitter:card']),
            "robots_txt": "robots" in written and Path(written["robots"]).exists(),
            "sitemap_xml": "sitemap" in written and Path(written["sitemap"]).exists(),
            "rss": "rss" in written and Path(written["rss"]).exists(),
            "google_search_console": bool(written.get("google_search_console")),
            "google_analytics": bool(str(release.get("google_analytics_id") or "").strip()),
            "top_page": "home" in written and Path(written["home"]).exists(),
            "article_list": "blog" in written and Path(written["blog"]).exists(),
            "manual_review": bool(release.get("pre_publication_review_approved", False)),
        }
        labels = {
            "site_url": "サイトURL",
            "custom_domain": "独自ドメイン",
            "https": "HTTPS設定",
            "vps_publication": "VPS公開設定",
            "seo": "SEO設定",
            "ogp": "OGP設定",
            "robots_txt": "robots.txt",
            "sitemap_xml": "sitemap.xml",
            "rss": "RSS",
            "google_search_console": "Google Search Console",
            "google_analytics": "Google Analytics",
            "top_page": "トップページ公開",
            "article_list": "記事一覧公開",
            "manual_review": "公開前レビュー承認",
        }
        errors = [
            {
                "code": key,
                "label": labels.get(key, key),
                "message": f"{labels.get(key, key)}が未設定または未生成です。",
            }
            for key, ok in required.items()
            if not ok
        ]
        publish_ready = not errors
        return {
            "ok": publish_ready,
            "publish_ready": publish_ready,
            "status": "approved" if publish_ready else "review_required",
            "site_url": site_url,
            "domain": domain,
            "https_enabled": site_url.startswith("https://"),
            "published_article_count": len(published_articles),
            "unpublished_article_count": len(unpublished_articles),
            "target_article_count": len(articles),
            "required": required,
            "checks": [
                {"key": key, "label": labels.get(key, key), "ok": ok}
                for key, ok in required.items()
            ],
            "missing": [row["code"] for row in errors],
            "errors": errors,
            "dry_run": True,
            "message": "公開前レビュー承認後にのみ本番公開へ進めます。",
            "created_at": _now(),
        }

    def html_contains(self, key: str, written: dict[str, str], needles: list[str]) -> bool:
        path = Path(written.get(key, ""))
        if not path.exists():
            return False
        content = path.read_text(encoding="utf-8")
        return all(needle in content for needle in needles)

    @staticmethod
    def ga_script(ga_id: str) -> str:
        if not ga_id:
            return ""
        escaped = html.escape(ga_id)
        return (
            f"  <script async src=\"https://www.googletagmanager.com/gtag/js?id={escaped}\"></script>\n"
            "  <script>\n"
            "    window.dataLayer = window.dataLayer || [];\n"
            "    function gtag(){dataLayer.push(arguments);}\n"
            "    gtag('js', new Date());\n"
            f"    gtag('config', '{escaped}');\n"
            "  </script>\n"
        )

    @staticmethod
    def gsc_meta(token: str) -> str:
        if not token:
            return ""
        return f"  <meta name=\"google-site-verification\" content=\"{html.escape(token)}\">\n"

    def mission_planner_feedback(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "feedback_id": f"webfb-{uuid4().hex[:10]}",
            "receiver": "Mission Planner",
            "source": "website_engine",
            "status": "ready",
            "improvement_tasks": [
                {"title": "公式サイトSEOを記事実績から改善", "agent": "SEO Agent", "priority": "normal"},
                {"title": "Business HubのDashboard指標を次回Releaseへ反映", "agent": "Business Agent", "priority": "normal"},
            ],
            "constitution_reference": {
                "version": context.get("development_constitution", {}).get("version", "1.0"),
                "primary_goal": "収益最大化",
            },
            "created_at": _now(),
        }

    def register_contact(self, name: str, email: str, message: str) -> dict[str, Any]:
        state = self.load_state()
        contact = {"contact_id": f"contact-{uuid4().hex[:10]}", "name": name, "email": email, "message": message, "created_at": _now()}
        state.setdefault("contacts", []).insert(0, contact)
        self.save_state(state)
        return contact

    def register_user(self, email: str, plan: str = "Free") -> dict[str, Any]:
        state = self.load_state()
        user = {"user_id": f"user-{uuid4().hex[:10]}", "email": email, "plan": plan, "created_at": _now()}
        state.setdefault("users", []).insert(0, user)
        self.save_state(state)
        return user
