from __future__ import annotations

from src.utils.json_store import save_json_atomic
from src.business_engine.manager import BusinessEngineStore
from src.official_site.site_manager import formal_release
from src.official_site.website_engine import WebsiteEngine


def _seed_business_data(store: BusinessEngineStore) -> None:
    data = store.load()
    data["article_queue"].insert(
        0,
        {
            "article_id": "article-phase8",
            "title": "AIOS Phase8 Official Website",
            "topic": "Official Website",
            "keyword": "AIOS Website",
            "body": "# AIOS Phase8 Official Website\n\n## Business Hub\nAIOS integrates revenue, analytics, and knowledge.",
            "status": "published",
            "pv": 1200,
            "ctr": 0.08,
            "actual_revenue": 18000,
        },
    )
    data["post_queue"].insert(
        0,
        {
            "thread_id": "thread-phase8",
            "platform": "threads",
            "title": "AIOS Phase8 Official Website",
            "text": "AIOS Official Website is now a Business Hub.",
            "pv": 600,
            "ctr": 0.06,
        },
    )
    data["affiliate_queue"].insert(0, {"offer_id": "offer-1", "title": "AIOS Template Pack"})
    data["execution_history"].insert(0, {"message": "Phase8 release generated", "created_at": "2026-07-08T00:00:00"})
    data["revenue_pipeline"].insert(0, {"item_id": "rev-1", "title": "Website Hub", "stage": "published", "expected_revenue": 10000, "probability": 50})
    store.save(data)


def test_phase8_builds_core_routes_seo_artifacts_and_article_sync(tmp_path, monkeypatch):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    _seed_business_data(store)
    monkeypatch.setattr(
        "src.official_site.website_engine.load_knowledge",
        lambda: {"improvement_examples": [{"title": "Knowledge public insight"}]},
    )
    engine = WebsiteEngine(store, state_path=tmp_path / "website.json", output_dir=tmp_path / "site")

    result = engine.build_site("https://aios.example.com")
    written = result["written"]

    for key in ["home", "about", "features", "pricing", "blog", "docs", "contact", "dashboard", "admin"]:
        assert key in written
        assert (tmp_path / "site" / f"{'index' if key == 'home' else key}.html").exists()

    article_path = tmp_path / "site" / "blog" / "aios-phase8-official-website.html"
    assert article_path.exists()
    article_html = article_path.read_text(encoding="utf-8")
    assert "<title>AIOS Phase8 Official Website | AIOS</title>" in article_html
    assert 'rel="canonical"' in article_html
    assert 'property="og:image"' in article_html

    assert (tmp_path / "site" / "sitemap.xml").exists()
    assert (tmp_path / "site" / "rss.xml").exists()
    assert (tmp_path / "site" / "robots.txt").exists()
    assert (tmp_path / "site" / "search.json").exists()
    assert "Knowledge public insight" in (tmp_path / "site" / "docs" / "knowledge.html").read_text(encoding="utf-8")
    assert result["state"]["mission_feedback"][0]["source"] == "website_engine"


def test_phase8_dashboard_analytics_business_and_threads_embed(tmp_path, monkeypatch):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    _seed_business_data(store)
    monkeypatch.setattr("src.official_site.website_engine.load_knowledge", lambda: {"improvement_examples": []})
    engine = WebsiteEngine(store, state_path=tmp_path / "website.json", output_dir=tmp_path / "site")

    result = engine.build_site("https://aios.example.com")
    dashboard = (tmp_path / "site" / "dashboard.html").read_text(encoding="utf-8")
    home = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")

    assert "AIOS Dashboard" in dashboard
    assert "Affiliate管理" in dashboard
    assert "AIOS Template Pack" in dashboard
    assert "AIOS Official Website is now a Business Hub." in home
    assert result["context"]["analytics"]["pv"] == 1800
    assert result["context"]["analytics"]["ctr"] == 0.07
    assert result["context"]["analytics"]["revenue"] >= 18000
    assert result["context"]["business"]["pipeline"]["weighted_forecast"] == 5000


def test_phase5_dashboard_centralizes_note_threads_revenue_and_history(tmp_path, monkeypatch):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    _seed_business_data(store)
    revenue_path = tmp_path / "revenue_engine.json"
    save_json_atomic(
        revenue_path,
        {
            "note_draft_saves": [
                {
                    "title": "Phase5 note下書き",
                    "theme": "収益ハブ",
                    "save_url": "dryrun://note/phase5",
                    "dry_run": True,
                }
            ],
            "threads_waiting_posts": [
                {
                    "text": "Phase5 Threads待機投稿",
                    "note_save_url": "dryrun://note/phase5",
                    "dry_run": True,
                    "status": "waiting",
                }
            ],
            "publish_history": [{"title": "Phase5 公開履歴", "status": "dry_run"}],
            "publish_approval_candidates": [
                {
                    "candidate_id": "cand-phase8",
                    "title": "Phase8 承認待ち",
                    "platform": "note",
                    "status": "approval_waiting",
                    "dry_run": True,
                }
            ],
            "publish_approval_history": [
                {
                    "candidate_id": "cand-done",
                    "title": "Phase8 Queue移動済み",
                    "platform": "threads",
                    "status": "approved",
                    "dry_run": True,
                }
            ],
            "forecasts": {"weighted_profit": 12000},
            "roi_ranking": [{"title": "note収益", "revenue_score": 90}],
        },
    )
    monkeypatch.setattr("src.official_site.website_engine.load_knowledge", lambda: {"improvement_examples": []})
    engine = WebsiteEngine(
        store,
        state_path=tmp_path / "website.json",
        output_dir=tmp_path / "site",
        revenue_state_path=revenue_path,
    )

    result = engine.build_site("https://aios.example.com")
    dashboard = (tmp_path / "site" / "dashboard.html").read_text(encoding="utf-8")

    assert "公開待ち一覧" in dashboard
    assert "note下書き一覧" in dashboard
    assert "Phase5 note下書き" in dashboard
    assert "Threads待機一覧" in dashboard
    assert "Phase5 Threads待機投稿" in dashboard
    assert "公開履歴" in dashboard
    assert "Phase5 公開履歴" in dashboard
    assert "承認待ち" in dashboard
    assert "Phase8 承認待ち" in dashboard
    assert "data-action=\"approve-publish\"" in dashboard
    assert "Publish Queue" in dashboard
    assert "Phase8 Queue移動済み" in dashboard
    assert "Revenue統計" in dashboard
    assert "DryRun: True" in dashboard
    assert result["context"]["publishing_hub"]["revenue_stats"]["roi_count"] == 1


def test_phase8_contact_user_registration_and_admin_state(tmp_path, monkeypatch):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    monkeypatch.setattr("src.official_site.website_engine.load_knowledge", lambda: {"improvement_examples": []})
    engine = WebsiteEngine(store, state_path=tmp_path / "website.json", output_dir=tmp_path / "site")

    contact = engine.register_contact("AIOS User", "user@example.com", "Interested")
    user = engine.register_user("member@example.com", "Pro")
    state = engine.load_state()

    assert contact["contact_id"]
    assert user["user_id"]
    assert state["contacts"][0]["email"] == "user@example.com"
    assert state["users"][0]["plan"] == "Pro"

    result = engine.build_site("https://aios.example.com")
    assert result["state"]["analytics"]["contact_count"] == 1
    assert result["state"]["analytics"]["registered_users"] == 1
    assert "管理者Dashboard" in (tmp_path / "site" / "admin.html").read_text(encoding="utf-8")


def test_phase4_official_site_builds_revenue_home_and_content_factory_routes(tmp_path, monkeypatch):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    _seed_business_data(store)
    content_state_path = tmp_path / "content_factory.json"
    save_json_atomic(
        content_state_path,
        {
            "contents": [
                {
                    "content_id": "site-content-1",
                    "type": "official_site_article",
                    "title": "Content Factory公式サイト記事",
                    "topic": "AIOS公式サイト",
                    "body": "# Content Factory公式サイト記事\n\n## 収益導線\n公式サイトへ自動反映します。",
                    "category": "official_site",
                    "tags": ["AIOS", "公式サイト"],
                    "status": "draft",
                    "pv": 900,
                    "ctr": 0.09,
                },
                {
                    "content_id": "note-content-1",
                    "type": "note",
                    "title": "Content Factory note記事",
                    "topic": "note収益化",
                    "body": "# Content Factory note記事\n\nnoteから収益導線を作ります。",
                    "category": "note",
                    "status": "draft",
                },
                {
                    "content_id": "threads-content-1",
                    "type": "threads",
                    "title": "Content Factory Threads投稿",
                    "text": "Threadsから公式サイトへ流入を作ります。",
                    "status": "draft",
                },
            ],
            "drafts": [{"content_id": "site-content-1", "path": "dryrun://draft"}],
            "history": [{"event": "phase1_generated"}],
        },
    )
    monkeypatch.setattr("src.official_site.website_engine.load_knowledge", lambda: {"improvement_examples": []})
    engine = WebsiteEngine(
        store,
        state_path=tmp_path / "website.json",
        output_dir=tmp_path / "site",
        content_state_path=content_state_path,
    )

    result = engine.build_site("https://aios.example.com")

    expected_keys = ["home", "about", "features", "start", "pricing", "blog", "notes", "threads", "contact", "updates"]
    for page in expected_keys:
        assert page in result["written"]
    for page in ["index", "about", "features", "start", "pricing", "blog", "notes", "threads", "contact", "updates"]:
        assert (tmp_path / "site" / f"{page}.html").exists()

    home = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    notes = (tmp_path / "site" / "notes.html").read_text(encoding="utf-8")
    threads = (tmp_path / "site" / "threads.html").read_text(encoding="utf-8")
    sitemap = (tmp_path / "site" / "sitemap.xml").read_text(encoding="utf-8")

    assert "最新記事" in home
    assert "人気記事" in home
    assert "収益KPI" in home
    assert "初収益までの進捗" in home
    assert "Content Factory公式サイト記事" in home
    assert "Content Factory note記事" in notes
    assert "Content Factory Threads投稿" in threads
    assert "start.html" in sitemap
    assert "notes.html" in sitemap
    assert "threads.html" in sitemap
    assert result["context"]["content_factory"]["drafts"][0]["content_id"] == "site-content-1"
    assert any(row.get("type") == "official_site_article" for row in result["context"]["official_articles"])


def test_phase5_dryrun_release_generates_vps_https_gsc_ga_and_requires_review(tmp_path, monkeypatch):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    _seed_business_data(store)
    monkeypatch.setattr("src.official_site.website_engine.load_knowledge", lambda: {"improvement_examples": []})
    engine = WebsiteEngine(store, state_path=tmp_path / "website.json", output_dir=tmp_path / "site")
    settings = {
        "release": {
            "domain_url": "https://aios.example.com",
            "public_dir": str(tmp_path / "public"),
            "vps_host": "vps.example.com",
            "vps_user": "deploy",
            "vps_web_root": "/var/www/aios",
            "google_analytics_id": "G-TEST123",
            "search_console_verification": "gsc-token",
            "search_console_file": "google-test.html",
            "search_console_file_content": "google-site-verification: google-test.html",
            "pre_publication_review_approved": False,
        }
    }

    result = engine.build_phase5_release(settings)
    home = (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    commands = (tmp_path / "site" / "deploy" / "dryrun_deploy_commands.txt").read_text(encoding="utf-8")

    assert result["deploy_plan"]["mode"] == "dry_run"
    assert result["review"]["status"] == "review_required"
    assert "manual_review" in result["review"]["missing"]
    assert "G-TEST123" in home
    assert "google-site-verification" in home
    assert (tmp_path / "site" / "google-test.html").exists()
    assert "rsync -avz --dry-run" in commands
    assert "certbot --nginx -d aios.example.com --dry-run" in commands
    assert result["state"]["phase5_release"]["auto_update"]["enabled"] is True

    settings["release"]["pre_publication_review_approved"] = True
    approved = engine.build_phase5_release(settings)
    assert approved["review"]["ok"] is True


def test_phase5_formal_release_blocks_without_pre_publication_review(tmp_path):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    _seed_business_data(store)
    settings = {
        "release": {
            "domain_url": "https://aios.example.com",
            "public_dir": str(tmp_path / "public"),
            "pre_publication_review_approved": False,
        }
    }

    try:
        formal_release(store.load(), settings)
    except RuntimeError as exc:
        assert "公開前レビュー" in str(exc)
    else:
        raise AssertionError("formal_release should require pre-publication review")


def test_phase5_review_gate_reports_required_checks_article_counts_and_errors(tmp_path, monkeypatch):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    _seed_business_data(store)
    monkeypatch.setattr("src.official_site.website_engine.load_knowledge", lambda: {"improvement_examples": []})
    engine = WebsiteEngine(store, state_path=tmp_path / "website.json", output_dir=tmp_path / "site")
    incomplete = {
        "release": {
            "domain_url": "http://example.com",
            "vps_host": "",
            "google_analytics_id": "",
            "search_console_verification": "",
            "pre_publication_review_approved": False,
        }
    }

    blocked = engine.build_phase5_release(incomplete)
    review = blocked["review"]

    assert review["publish_ready"] is False
    assert review["status"] == "review_required"
    assert review["target_article_count"] >= 1
    assert review["unpublished_article_count"] >= 0
    assert any(error["code"] == "https" for error in review["errors"])
    assert any(error["code"] == "google_analytics" for error in review["errors"])
    assert any(check["label"] == "robots.txt" and check["ok"] is True for check in review["checks"])

    complete = {
        "release": {
            "domain_url": "https://aios.example.com",
            "vps_host": "vps.example.com",
            "google_analytics_id": "G-TEST123",
            "search_console_verification": "gsc-token",
            "pre_publication_review_approved": True,
        }
    }
    approved = engine.build_phase5_release(complete)["review"]

    assert approved["publish_ready"] is True
    assert approved["errors"] == []
    assert approved["required"]["manual_review"] is True
