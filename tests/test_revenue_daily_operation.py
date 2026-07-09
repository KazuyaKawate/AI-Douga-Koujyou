from __future__ import annotations

from pathlib import Path

from src.ai.response import AIResponse
from src.revenue_engine.daily_operation import RevenueDailyOperationMode
from src.revenue_engine.dashboard import RevenueEngineDashboard
from src.revenue_engine.threads_draft_flow import RevenueThreadsDraftFlow, ThreadsCredentials


class FixedRouter:
    def route(self, task):
        if "Threads投稿文" in task.prompt:
            content = "今日のnote下書きからThreads投稿文を生成しました。DryRunで公開待ちに登録します。"
        else:
            content = "# 今日のAIOS収益テーマ\n\n日次運用で生成したnote本文です。"
        return AIResponse(
            ok=True,
            content=content,
            provider="daily-test-ai",
            model="daily-test-model",
            task_type="writing",
            duration_ms=1,
        )


class SuccessfulNotePublisher:
    def publish(self, item, *, dry_run=True):
        return {
            "platform": "note",
            "status": "dry_run",
            "external_id": "note-daily",
            "draft_url": "dryrun://note/note-daily",
            "dry_run": dry_run,
        }


def _daily_mode(tmp_path: Path) -> tuple[RevenueDailyOperationMode, RevenueEngineDashboard]:
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    credentials = ThreadsCredentials(input_func=lambda prompt: "daily@example.com", password_func=lambda prompt: "daily-secret")
    threads_flow = RevenueThreadsDraftFlow(dashboard=dashboard, router=FixedRouter(), credentials=credentials)
    threads_flow.note_flow.publisher = SuccessfulNotePublisher()
    return RevenueDailyOperationMode(dashboard=dashboard, threads_flow=threads_flow, report_dir=tmp_path / "reports"), dashboard


def test_phase6_daily_operation_completes_content_pack_and_report(tmp_path: Path) -> None:
    mode, dashboard = _daily_mode(tmp_path)

    result = mode.run_once(dry_run=True)
    state = dashboard.load_state()
    report = Path(result["report_path"]).read_text(encoding="utf-8")

    assert result["status"] == "success"
    assert result["dry_run"] is True
    assert result["theme"] == "note記事"
    assert state["note_draft_saves"][0]["save_url"] == "dryrun://note/note-daily"
    assert state["threads_waiting_posts"][0]["status"] == "waiting"
    assert state["daily_operation_runs"][0]["operation_id"] == result["operation_id"]
    assert "AIOS Revenue Daily Report" in report
    assert "Threads Waiting: True" in report
    assert "daily-secret" not in str(state)


def test_phase6_daily_operation_rejects_live_mode(tmp_path: Path) -> None:
    mode, dashboard = _daily_mode(tmp_path)

    result = mode.run_once(theme="Liveは禁止", dry_run=False)
    state = dashboard.load_state()

    assert result["status"] == "failed"
    assert result["stage"] == "dry_run_guard"
    assert state["note_draft_saves"] == []
    assert state["threads_waiting_posts"] == []
    assert state.get("daily_operation_runs", []) == []
