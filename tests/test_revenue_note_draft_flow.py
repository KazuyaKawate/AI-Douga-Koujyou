from __future__ import annotations

from pathlib import Path

from src.ai.response import AIResponse
from src.revenue_engine.dashboard import RevenueEngineDashboard
from src.revenue_engine.note_draft_flow import RevenueNoteDraftFlow


class FixedRouter:
    def route(self, task):
        return AIResponse(
            ok=True,
            content="# note記事で初収益を狙う方法\n\nテーマから生成した本文です。",
            provider="test-ai",
            model="test-model",
            task_type="writing",
            duration_ms=1,
        )


class SuccessfulPublisher:
    def __init__(self) -> None:
        self.calls = []

    def publish(self, item, *, dry_run=True):
        self.calls.append({"item": item, "dry_run": dry_run})
        return {
            "platform": "note",
            "status": "dry_run" if dry_run else "draft_saved",
            "external_id": "note-test-123",
            "draft_url": "dryrun://note/note-test-123" if dry_run else "https://note.com/notes/note-test-123",
            "dry_run": dry_run,
        }


class FailingPublisher:
    def publish(self, item, *, dry_run=True):
        raise RuntimeError("note save unavailable")


def test_revenue_note_draft_flow_theme_generation_save_and_dashboard_record(tmp_path: Path) -> None:
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    publisher = SuccessfulPublisher()
    flow = RevenueNoteDraftFlow(dashboard=dashboard, router=FixedRouter(), publisher=publisher)

    result = flow.run(dry_run=True)
    state = dashboard.load_state()

    assert result["status"] == "success"
    assert result["theme"] == "note記事"
    assert result["article"]["title"] == "note記事で初収益を狙う方法"
    assert publisher.calls[0]["dry_run"] is True
    assert publisher.calls[0]["item"]["platform"] == "note"
    assert state["note_draft_saves"][0]["save_url"] == "dryrun://note/note-test-123"
    assert state["note_draft_saves"][0]["theme"] == "note記事"
    assert state["note_draft_saves"][0]["ai_provider"] == "test-ai"


def test_revenue_note_draft_flow_does_not_update_dashboard_when_save_fails(tmp_path: Path) -> None:
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    flow = RevenueNoteDraftFlow(dashboard=dashboard, router=FixedRouter(), publisher=FailingPublisher())

    result = flow.run(dry_run=True)
    state = dashboard.load_state()

    assert result["status"] == "failed"
    assert result["stage"] == "draft_save"
    assert state["note_draft_saves"] == []


def test_revenue_note_draft_flow_accepts_theme_input(tmp_path: Path) -> None:
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    publisher = SuccessfulPublisher()
    flow = RevenueNoteDraftFlow(dashboard=dashboard, router=FixedRouter(), publisher=publisher)

    result = flow.run(theme="入力テーマ", dry_run=True)
    state = dashboard.load_state()

    assert result["status"] == "success"
    assert result["theme"] == "入力テーマ"
    assert publisher.calls[0]["item"]["content"]["topic"] == "入力テーマ"
    assert state["note_draft_saves"][0]["theme"] == "入力テーマ"
