from __future__ import annotations

from pathlib import Path

from src.business_engine.manager import BusinessEngineStore
from src.creator_factory.factory_manager import CreatorFactoryManager, PIPELINES, creator_factory_summary
from src.knowledge.knowledge_base import KnowledgeBase


def test_project_creation(tmp_path: Path) -> None:
    manager = CreatorFactoryManager(tmp_path / "data")

    project = manager.create_project(
        "Phase 9 Project",
        description="Local production project",
        category="note",
        target_platform="note",
        priority="high",
    )

    assert project["id"].startswith("proj_")
    assert project["status"] == "planning"
    assert manager.get_project(project["id"])["title"] == "Phase 9 Project"
    assert (tmp_path / "data" / "projects" / f"{project['id']}.json").exists()


def test_template_management(tmp_path: Path) -> None:
    manager = CreatorFactoryManager(tmp_path / "data")

    template = manager.create_template("SEO Template", "seo_article", "Original")
    updated = manager.update_template(template["id"], body="Updated", description="v2")
    duplicate = manager.duplicate_template(template["id"])

    assert updated is not None
    assert updated["version"] == 2
    assert updated["history"][0]["body"] == "Original"
    assert duplicate is not None
    assert duplicate["name"].endswith("Copy")
    assert len(manager.list_templates("seo_article")) == 2


def test_production_queue_and_pipeline_summary(tmp_path: Path) -> None:
    manager = CreatorFactoryManager(tmp_path / "data")
    project = manager.create_project("SNS Campaign")

    item = manager.enqueue_production("sns", "Launch thread", project_id=project["id"], priority="high")
    summary = manager.pipeline_summary()

    assert item["pipeline_label"] == PIPELINES["sns"]["label"]
    assert manager.get_project(project["id"])["status"] == "queued"
    assert summary["sns"]["queue"] == 1
    assert summary["sns"]["estimated_token_usage"] == PIPELINES["sns"]["estimated_token_usage"]


def test_knowledge_base(tmp_path: Path) -> None:
    kb = KnowledgeBase(tmp_path / "data")

    item = kb.add("Brand tone", "tone_preset", "Calm, direct, practical.", tags=["voice"])

    assert item["knowledge_type"] == "tone_preset"
    assert kb.list("tone_preset")[0]["title"] == "Brand tone"
    assert "prompt_snippet" in kb.types()


def test_revenue_estimator_is_production_only(tmp_path: Path) -> None:
    manager = CreatorFactoryManager(tmp_path / "data")
    item = manager.enqueue_production("note", "Article")
    manager.update_production_status(
        item["id"],
        "exported",
        approval_status="approved",
        export_status="exported",
    )

    estimate = manager.revenue_estimator()

    assert estimate["articles_produced"] == 1
    assert estimate["exports_completed"] == 1
    assert estimate["approval_rate"] == 100.0
    assert estimate["income_prediction_enabled"] is False


def test_dashboard_metrics(tmp_path: Path) -> None:
    manager = CreatorFactoryManager(tmp_path / "data")
    manager.create_project("Active")
    queued = manager.enqueue_production("affiliate", "Affiliate draft")
    manager.update_production_status(queued["id"], "reviewing", approval_status="pending_review")

    metrics = manager.dashboard_metrics()

    assert metrics["active_projects"] == 1
    assert metrics["review_queue"] == 1
    assert metrics["local_first"] is True
    assert metrics["external_apis_enabled"] is False


def test_business_engine_integration(tmp_path: Path, monkeypatch) -> None:
    data_root = tmp_path / "data"
    manager = CreatorFactoryManager(data_root)
    manager.create_project("Business Engine Surface")
    manager.enqueue_production("business_report", "Weekly report")

    monkeypatch.setattr("src.business_engine.manager.creator_factory_summary", lambda: creator_factory_summary(data_root))
    store = BusinessEngineStore(tmp_path / "business_engine.json")

    metrics = store.beta_metrics()

    assert metrics["active_projects"] == 1
    assert metrics["creator_production_queue"] == 1
    assert metrics["creator_export_queue"] == 0


def test_local_storage_layout(tmp_path: Path) -> None:
    manager = CreatorFactoryManager(tmp_path / "data")

    assert manager.projects_dir.exists()
    assert manager.templates_dir.exists()
    assert manager.knowledge_dir.exists()
    assert manager.production_dir.exists()
    assert manager.history_dir.exists()


def test_no_external_api_path(tmp_path: Path, monkeypatch) -> None:
    def fail_network(*args, **kwargs):
        raise AssertionError("External APIs must not be called by Creator Factory.")

    monkeypatch.setattr("urllib.request.urlopen", fail_network)
    manager = CreatorFactoryManager(tmp_path / "data")
    manager.create_project("Local Only")
    manager.create_template("Note", "note_article")
    manager.add_knowledge_item("Prompt", "reusable_prompt", "Use local context only.")
    manager.enqueue_production("note", "Local article")

    metrics = manager.dashboard_metrics()

    assert metrics["local_first"] is True
    assert metrics["external_apis_enabled"] is False
