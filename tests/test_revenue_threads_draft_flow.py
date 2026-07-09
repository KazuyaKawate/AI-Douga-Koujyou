from __future__ import annotations

from pathlib import Path

from src.ai.response import AIResponse
from src.revenue_engine.dashboard import RevenueEngineDashboard
from src.revenue_engine.threads_draft_flow import RevenueThreadsDraftFlow, ThreadsCredentials


class FixedRouter:
    def route(self, task):
        prompt = task.prompt
        if "Threads投稿文" in prompt:
            content = "note下書きからThreads用の投稿文を生成しました。詳しくは保存済みnoteで確認できます。"
        else:
            content = "# Phase4 note下書き\n\nThreadsへ展開するためのnote本文です。"
        return AIResponse(
            ok=True,
            content=content,
            provider="test-ai",
            model="test-model",
            task_type="writing",
            duration_ms=1,
        )


class SuccessfulNotePublisher:
    def publish(self, item, *, dry_run=True):
        return {
            "platform": "note",
            "status": "dry_run",
            "external_id": "note-phase4",
            "draft_url": "dryrun://note/note-phase4",
            "dry_run": dry_run,
        }


def test_phase4_note_draft_to_threads_waiting_dashboard_without_storing_credentials(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("THREADS_EMAIL", "user@example.com")
    monkeypatch.setenv("THREADS_PASSWORD", "super-secret")
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    flow = RevenueThreadsDraftFlow(dashboard=dashboard, router=FixedRouter())
    flow.note_flow.publisher = SuccessfulNotePublisher()

    result = flow.run(theme="Phase4 Threads", dry_run=True)
    state = dashboard.load_state()
    serialized = str(state) + str(result)

    assert result["status"] == "success"
    assert result["dry_run"] is True
    assert state["note_draft_saves"][0]["save_url"] == "dryrun://note/note-phase4"
    assert state["threads_waiting_posts"][0]["status"] == "waiting"
    assert state["threads_waiting_posts"][0]["dry_run"] is True
    assert state["threads_waiting_posts"][0]["note_save_url"] == "dryrun://note/note-phase4"
    assert "super-secret" not in serialized
    assert "user@example.com" not in serialized


def test_phase4_reads_threads_credentials_from_runtime_input_when_env_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("THREADS_EMAIL", raising=False)
    monkeypatch.delenv("THREADS_PASSWORD", raising=False)
    credentials = ThreadsCredentials(input_func=lambda prompt: "runtime@example.com", password_func=lambda prompt: "runtime-secret")
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    flow = RevenueThreadsDraftFlow(dashboard=dashboard, router=FixedRouter(), credentials=credentials)
    flow.note_flow.publisher = SuccessfulNotePublisher()

    result = flow.run(theme="Runtime Input", dry_run=True)
    state = dashboard.load_state()
    serialized = str(state) + str(result)

    assert result["status"] == "success"
    assert state["threads_waiting_posts"][0]["credentials_configured"] is True
    assert "runtime-secret" not in serialized
    assert "runtime@example.com" not in serialized


def test_phase4_rejects_threads_live_posting(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("THREADS_EMAIL", "user@example.com")
    monkeypatch.setenv("THREADS_PASSWORD", "super-secret")
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    flow = RevenueThreadsDraftFlow(dashboard=dashboard, router=FixedRouter())

    result = flow.run(theme="No Live", dry_run=False)
    state = dashboard.load_state()

    assert result["status"] == "failed"
    assert result["stage"] == "dry_run_guard"
    assert state["threads_waiting_posts"] == []
    assert state["note_draft_saves"] == []
