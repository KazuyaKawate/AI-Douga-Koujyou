from __future__ import annotations

from src.revenue_engine.dashboard import RevenueEngineDashboard
from src.revenue_engine.publish_approval import RevenuePublishApprovalFlow


def _seed_dashboard(dashboard: RevenueEngineDashboard) -> None:
    state = dashboard.load_state()
    state["note_draft_saves"] = [
        {
            "flow_id": "note-flow-1",
            "content_id": "note-content-1",
            "title": "承認待ちnote",
            "save_url": "dryrun://note/approval",
            "dry_run": True,
        }
    ]
    state["threads_waiting_posts"] = [
        {
            "waiting_id": "threads-wait-1",
            "note_title": "承認待ちThreads",
            "text": "Threads投稿候補です。",
            "note_save_url": "dryrun://note/approval",
            "dry_run": True,
            "status": "waiting",
        }
    ]
    dashboard.save_state(state)


def test_phase8_syncs_note_and_threads_publish_approval_candidates(tmp_path) -> None:
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    _seed_dashboard(dashboard)
    flow = RevenuePublishApprovalFlow(dashboard=dashboard, publish_path=tmp_path / "publish_engine.json")

    candidates = flow.sync_candidates()

    assert len(candidates) == 2
    assert {row["platform"] for row in candidates} == {"note", "threads"}
    assert all(row["status"] == "approval_waiting" for row in candidates)
    assert all(row["dry_run"] is True for row in candidates)


def test_phase8_approved_candidate_moves_to_publish_queue_dry_run_only(tmp_path) -> None:
    dashboard = RevenueEngineDashboard(path=tmp_path / "revenue_engine.json")
    _seed_dashboard(dashboard)
    publish_path = tmp_path / "publish_engine.json"
    flow = RevenuePublishApprovalFlow(dashboard=dashboard, publish_path=publish_path)
    candidate = flow.sync_candidates()[0]

    approved = flow.approve(candidate["candidate_id"], reviewer="tester")
    state = dashboard.load_state()
    publish_state = __import__("json").loads(publish_path.read_text(encoding="utf-8"))

    assert approved is not None
    assert approved["status"] == "approved"
    assert approved["publish_queue_item"]["status"] == "approved"
    assert state["publish_approval_history"][0]["candidate_id"] == candidate["candidate_id"]
    assert publish_state["dry_run_default"] is True
    assert publish_state["queue"][0]["status"] == "approved"
    assert publish_state["queue"][0]["dry_run"] is True
    assert publish_state["queue"][0]["approval"]["dry_run_only"] is True
