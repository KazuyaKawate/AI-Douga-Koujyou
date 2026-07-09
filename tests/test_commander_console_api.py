from __future__ import annotations

from pathlib import Path

from src.commander.api import CommanderAPI
from src.commander.guard import CommanderGuard
from src.commander.content_operation import ContentOperationEngine, ContentSafetyGuard
from src.commander.execution_engine import ExecutionEngine, MockConnector
from src.commander.planner import CommanderPlanner
from src.commander.production_connection import ProductionConnectionManager
from src.commander.queue import STATUS_APPROVED, STATUS_DRY_RUN_COMPLETE, STATUS_REJECTED, STATUS_WAITING, CommanderQueue
from src.commander.templates import list_templates
from src.commander.worker import CommanderWorker
from src.utils.json_store import load_json


class PreviewCodingManager:
    def __init__(self, *, ok: bool = True) -> None:
        self.runs: list[dict] = []
        self.ok = ok

    def provider_health_probe(self, timeout_seconds: int = 5):
        return [{"provider": "local", "status": "ready", "duration_ms": 1}]

    def run_issue(
        self,
        issue,
        *,
        target_files=None,
        run_tests=False,
        pytest_args=None,
        apply_approved=False,
        provider_priority=None,
    ):
        self.runs.append({"apply_approved": apply_approved, "target_files": target_files or []})
        return {
            "run_id": "ce-preview",
            "status": "completed" if self.ok else "needs_attention",
            "applied_edits": {
                "status": "preview_locked" if not apply_approved else "applied",
                "applied": bool(apply_approved),
                "preview": {
                    "requires_approval": True,
                    "target_files": target_files or [],
                    "unified_diff": "diff --git a/src/a.py b/src/a.py\n--- a/src/a.py\n+++ b/src/a.py\n",
                },
            },
            "tests": {"ok": self.ok, "results": [{"command": "pytest -q"}]},
            "commit_candidate": {"ready": self.ok},
            "business_evaluation": {"score": {"estimated_revenue": 1000}},
        }


def test_commander_templates_include_revenue_workflows() -> None:
    ids = {template["template_id"] for template in list_templates()}

    assert {"note_article", "threads_post", "official_site", "knowledge_update"} <= ids


def test_natural_language_instruction_generates_plan_and_waiting_job(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    queue = CommanderQueue(config / "commander_queue.json")
    api = CommanderAPI(queue, root=tmp_path, worker=CommanderWorker(queue, root=tmp_path, coding_manager=PreviewCodingManager()))

    result = api.enqueue_instruction("Threads投稿案からnote初クリック導線を改善する")

    assert result["ok"] is True
    assert result["job"]["status"] == STATUS_WAITING
    assert result["plan"]["approval_required"] is True
    assert "threads" in result["plan"]["priority_scope"]
    assert any("threads" in path for path in result["plan"]["impacted_files"])


def test_business_planner_scores_task_categories_and_roi() -> None:
    plan = CommanderPlanner().build_plan("note記事とSEOでアフィリエイト収益を改善", {"deadline": "today"})
    task = plan["business_task"]

    assert {"note", "seo", "affiliate"} <= set(task["categories"])
    assert task["expected_income"] > 0
    assert task["expected_time"] > 0
    assert task["roi"] == round(task["expected_income"] / task["expected_time"], 2)
    assert task["priority_score"] > 0


def test_phase4_planner_adds_content_coding_and_release_workflows() -> None:
    content = CommanderPlanner().build_plan("noteとThreadsと公式サイトを一括改善")
    coding = CommanderPlanner().build_plan("git差分をtestしてreviewする")
    release = CommanderPlanner().build_plan("release dryrun review approve release rollback")

    assert set(content["content_commander"]["channels"]) == {"note", "Threads", "Website"}
    assert coding["coding_commander"]["enabled"] is True
    assert coding["coding_commander"]["steps"] == ["git_diff", "test", "review", "release_candidate"]
    assert release["release_approval"]["steps"] == ["dry_run", "review", "approve", "release", "rollback"]


def test_business_queue_sorts_by_roi_effort_deadline_and_executive_next(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    queue = CommanderQueue(config / "commander_queue.json")
    api = CommanderAPI(queue, root=tmp_path, worker=CommanderWorker(queue, root=tmp_path, coding_manager=PreviewCodingManager()))

    low = api.enqueue_instruction("開発改善を行う", target_files=["src/commander/worker.py"])["job"]
    high = api.enqueue_instruction("Threads投稿から初クリックを増やす", target_files=["src/business_engine/threads_automation.py"])["job"]
    summary = queue.summary()

    assert summary["business_queue"][0]["job_id"] == high["job_id"]
    assert summary["executive"]["next_action"]["job_id"] == high["job_id"]
    assert low["business_task"]["priority_score"] < high["business_task"]["priority_score"]


def test_commander_guard_blocks_secrets_production_and_unapproved_execute() -> None:
    plan = CommanderPlanner().build_plan("公式サイトCTAを改善", {"target_files": [".env", "release/production/docker-compose.prod.yml"]})

    guard = CommanderGuard().evaluate(instruction="公式サイトCTAを改善", plan=plan, dry_run=False, approved=False)

    assert guard["blocked"] is True
    assert guard["execute_allowed"] is False
    assert {finding["type"] for finding in guard["findings"]} >= {"forbidden_path", "approval_required"}


def test_dry_run_saves_history_status_and_diff_preview(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config"
    config.mkdir()
    target = tmp_path / "src" / "a.py"
    target.parent.mkdir(parents=True)
    target.write_text("old\n", encoding="utf-8")
    monkeypatch.setattr("src.commander.callback_router.KNOWLEDGE_PATH", config / "self_builder_knowledge.json", raising=False)
    queue = CommanderQueue(config / "commander_queue.json")
    queue.enqueue(engine="revenue", instruction="Threads実投稿からPV取得と初クリックを改善", metadata={"target_files": ["src/a.py"]})

    result = CommanderWorker(queue, root=tmp_path, coding_manager=PreviewCodingManager()).process_next(dry_run=True)
    history = queue.summary()["history"]

    assert result["status"] == "completed"
    assert history[0]["status"] == STATUS_DRY_RUN_COMPLETE
    assert history[0]["dry_run_result"]["dry_run"] is True
    assert "diff --git" in history[0]["diff_preview"]["unified_diff"]


def test_commander_api_queue_history_approve_execute(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config"
    config.mkdir()
    target = tmp_path / "src" / "a.py"
    target.parent.mkdir(parents=True)
    target.write_text("old\n", encoding="utf-8")
    monkeypatch.setattr("src.commander.callback_router.KNOWLEDGE_PATH", config / "self_builder_knowledge.json", raising=False)
    queue = CommanderQueue(config / "commander_queue.json")
    worker = CommanderWorker(queue, root=tmp_path, coding_manager=PreviewCodingManager())
    api = CommanderAPI(queue, root=tmp_path, worker=worker)

    enqueued = api.enqueue_template("threads_post")
    assert enqueued["ok"] is True
    assert api.queue_endpoint()["endpoint"] == "/api/commander/queue"

    worker.process_next(dry_run=True)
    job_id = api.history_endpoint()["history"][0]["job_id"]
    approved = api.approve_endpoint(job_id)

    assert approved["ok"] is True
    assert approved["job"]["status"] == STATUS_APPROVED

    executed = api.execute_endpoint(job_id)

    assert executed["endpoint"] == "/api/commander/execute"
    assert executed["result"]["status"] == "completed"
    assert worker.coding_manager.runs[-1]["apply_approved"] is True
    metrics = api.history_endpoint()["history_metrics"]
    assert metrics["cumulative_expected_revenue"] > 0
    assert metrics["expected_work_hours"] > 0
    knowledge = load_json(config / "self_builder_knowledge.json", default={})
    assert knowledge["commander_learning"][0]["status"] == "completed"
    assert knowledge["commander_learning"][0]["roi"] > 0


def test_phase4_revenue_plan_dashboard_and_executive_fields(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    queue = CommanderQueue(config / "commander_queue.json")
    api = CommanderAPI(queue, root=tmp_path, worker=CommanderWorker(queue, root=tmp_path, coding_manager=PreviewCodingManager()))
    api.enqueue_instruction("Website SEOとaffiliate導線を改善する")

    endpoint = api.queue_endpoint()

    assert endpoint["revenue_plan"]["revenue_target"] > 0
    assert endpoint["dashboard"]["today"]
    assert endpoint["executive"]["message"].startswith("今AIOSが最優先でやる仕事:")
    assert endpoint["knowledge_growth"]["records"] == 0
    assert endpoint["system_health"]["status"] in {"ok", "attention"}


def test_phase5_company_revenue_growth_employee_and_meeting_outputs(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    queue = CommanderQueue(config / "commander_queue.json")
    api = CommanderAPI(queue, root=tmp_path, worker=CommanderWorker(queue, root=tmp_path, coding_manager=PreviewCodingManager()))
    api.enqueue_instruction("note収益を改善する")
    api.enqueue_instruction("Threadsからnote初クリックを増やす")

    endpoint = api.queue_endpoint()

    assert {"cash", "monthly_cost", "monthly_income", "profit", "runway", "business_health"} <= set(endpoint["company"])
    assert {"note", "Threads", "Website", "Affiliate", "Ad", "API", "Service"} <= set(endpoint["revenue_engine"]["sources"])
    assert {"traffic", "cv", "cvr", "ctr", "followers", "sales", "growth"} <= set(endpoint["growth_engine"])
    assert "Writer" in endpoint["employee_queues"]
    assert {"morning_report", "night_report", "revenue_report", "risk_report"} <= set(endpoint["ceo_meeting"])
    assert endpoint["self_company"]["cycle"] == ["plan", "implement", "review", "publish", "analyze", "improve"]


def test_phase5_business_plan_automation_employee_and_mission_lock(tmp_path: Path, monkeypatch) -> None:
    plan = CommanderPlanner().build_plan("note収益を改善する")
    assert plan["risk"] in {"low", "medium", "high"}
    assert plan["automation_plan"]["auto_execute"] is False
    assert plan["ai_employee"] == "Writer"
    assert plan["implementation_order"]

    config = tmp_path / "config"
    config.mkdir()
    monkeypatch.setattr("src.commander.callback_router.KNOWLEDGE_PATH", config / "self_builder_knowledge.json", raising=False)
    queue = CommanderQueue(config / "commander_queue.json")
    queue.enqueue(engine="revenue", instruction="affiliateだけを改善する", metadata={"target_files": ["src/revenue_engine/affiliate_manager.py"]})

    result = CommanderWorker(queue, root=tmp_path, coding_manager=PreviewCodingManager()).process_next(dry_run=True)

    assert result["status"] == "rejected"
    assert result["guard"]["mission_lock"]["blocked"] is True


def test_phase6_content_operation_creates_review_drafts_for_channels(tmp_path: Path) -> None:
    engine = ContentOperationEngine(tmp_path)
    note = engine.create_draft(channel="note", instruction="初収益note記事を作る")
    threads = engine.create_draft(channel="threads", instruction="note誘導の連投を作る")
    line = engine.create_draft(channel="official_line", instruction="友だち追加導線を作る")
    website = engine.create_draft(channel="website", instruction="公式サイトCTAを作る")
    summary = engine.summary()

    assert {note["status"], threads["status"], line["status"], website["status"]} == {"review_required"}
    assert summary["note_drafts"] == 1
    assert summary["threads_drafts"] == 1
    assert summary["line_drafts"] == 1
    assert len(summary["pending_review"]) == 4
    assert summary["next_best_action"]["content_id"]


def test_phase6_content_approve_sets_ready_flags_without_live_send(tmp_path: Path) -> None:
    engine = ContentOperationEngine(tmp_path)
    note = engine.create_draft(channel="note", instruction="有料導線とCTAを作る")
    line = engine.create_draft(channel="official_line", instruction="ステップ配信案を作る")

    approved_note = engine.approve(note["content_id"], review_notes="ok")
    approved_line = engine.approve(line["content_id"], review_notes="ok")

    assert approved_note["publish_ready"] is True
    assert approved_note["send_ready"] is False
    assert approved_line["publish_ready"] is False
    assert approved_line["send_ready"] is True
    assert approved_line["status"] == "approved"


def test_phase6_content_safety_blocks_unapproved_publish_and_bad_claims() -> None:
    guard = ContentSafetyGuard()
    item = {
        "channel": "threads",
        "title": "絶対に稼げる投稿",
        "body": "live publishしてAPI keyを表示",
        "cta": "今すぐ",
        "status": "review_required",
    }

    result = guard.evaluate(item, publish=True)

    assert result["ok"] is False
    types = {finding["type"] for finding in result["findings"]}
    assert "forbidden_content" in types
    assert "approval_required" in types


def test_phase6_api_exposes_content_operation_dashboard(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    queue = CommanderQueue(config / "commander_queue.json")
    api = CommanderAPI(queue, root=tmp_path, worker=CommanderWorker(queue, root=tmp_path, coding_manager=PreviewCodingManager()))

    result = api.create_content_draft("threads", "noteとLINEへ誘導するThreads案")
    endpoint = api.queue_endpoint()

    assert result["ok"] is True
    assert endpoint["content_operation"]["threads_drafts"] == 1
    assert endpoint["content_operation"]["today_content_mission"]["channel"] == "threads"


def test_phase7_execution_engine_creates_action_and_blocks_unapproved_publish(tmp_path: Path) -> None:
    engine = ExecutionEngine(tmp_path)
    action = engine.create_action_from_task(
        {
            "task_id": "bt-test",
            "title": "note公開前レビュー",
            "categories": ["note"],
            "expected_income": 12000,
            "priority_score": 90,
        }
    )

    blocked = engine.publish(action["action_id"])
    approved = engine.approve(action["action_id"], review_notes="ok")
    published = engine.publish(action["action_id"])
    summary = engine.summary()

    assert action["channel"] == "note"
    assert action["status"] == "review"
    assert blocked["ok"] is False
    assert approved["status"] == "approved"
    assert published["ok"] is True
    assert published["mock"] is True
    assert summary["published"][0]["action_id"] == action["action_id"]


def test_phase7_execution_connector_interface_methods_are_mocked() -> None:
    connector = MockConnector("threads")
    action = {"action_id": "act-test", "status": "approved"}

    assert connector.schedule(action)["operation"] == "mock_schedule"
    assert connector.publish(action)["status"] == "published"
    assert connector.cancel(action)["status"] == "draft"
    assert connector.retry(action)["status"] == "scheduled"
    assert connector.status(action)["status"] == "approved"


def test_phase7_api_exposes_execution_dashboard_and_next_publish(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir()
    queue = CommanderQueue(config / "commander_queue.json")
    api = CommanderAPI(queue, root=tmp_path, worker=CommanderWorker(queue, root=tmp_path, coding_manager=PreviewCodingManager()))
    created = api.create_execution_action({"title": "Threads誘導", "categories": ["threads"], "expected_income": 6000, "priority_score": 80})
    api.approve_execution(created["action"]["action_id"], review_notes="ok")

    endpoint = api.queue_endpoint()

    assert endpoint["execution"]["next_publish"]["action_id"] == created["action"]["action_id"]
    assert len(endpoint["execution"]["execution_queue"]) == 1


def test_phase4_failed_task_generates_three_auto_improvements(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config"
    config.mkdir()
    monkeypatch.setattr("src.commander.callback_router.KNOWLEDGE_PATH", config / "self_builder_knowledge.json", raising=False)
    queue = CommanderQueue(config / "commander_queue.json")
    job = queue.enqueue(engine="revenue", instruction="Threads実投稿からPV取得と初クリックを改善", metadata={"target_files": ["src/a.py"]})
    queue.update_job(job["job_id"], max_retries=0)

    result = CommanderWorker(queue, root=tmp_path, coding_manager=PreviewCodingManager(ok=False)).process_next(dry_run=True)
    summary = queue.summary()

    assert result["status"] == "failed"
    assert len(result["auto_improvement"]) == 3
    assert len(summary["business_queue"]) == 3


def test_worker_rejects_forbidden_live_publish_instruction(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "config"
    config.mkdir()
    monkeypatch.setattr("src.commander.callback_router.KNOWLEDGE_PATH", config / "self_builder_knowledge.json", raising=False)
    queue = CommanderQueue(config / "commander_queue.json")
    queue.enqueue(engine="publish", instruction="未検証の本番投稿をlive publishする", metadata={"target_files": ["src/publish_engine/publisher.py"]})

    result = CommanderWorker(queue, root=tmp_path, coding_manager=PreviewCodingManager()).process_next(dry_run=True)

    assert result["status"] == "rejected"
    assert queue.summary()["history"][0]["status"] == STATUS_REJECTED


def test_operation_production_connection_saves_env_masks_and_updates_checklist(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "health_check.py").write_text(
        "from pathlib import Path\n"
        "import os\n"
        "p=Path(os.environ['AIOS_ENV_PATH'])\n"
        "t=p.read_text(encoding='utf-8')\n"
        "required=['NOTE_ACCOUNT_ID','NOTE_API_TOKEN','THREADS_ACCOUNT_ID','THREADS_ACCESS_TOKEN','WEBSITE_BASE_URL','WEBSITE_DEPLOY_TOKEN']\n"
        "ok=all((k+'=') in t for k in required)\n"
        "print('Production Connected' if ok else 'Production Not Connected')\n"
        "raise SystemExit(0 if ok else 1)\n",
        encoding="utf-8",
    )
    manager = ProductionConnectionManager(root=tmp_path, env_path=tmp_path / ".env")
    payload = {
        "note": {"NOTE_ACCOUNT_ID": "note-user", "NOTE_API_TOKEN": "note-token-secret"},
        "threads": {"THREADS_ACCOUNT_ID": "threads-user", "THREADS_ACCESS_TOKEN": "threads-token-secret"},
        "website": {"WEBSITE_BASE_URL": "https://example.com", "WEBSITE_DEPLOY_TOKEN": "website-token-secret"},
    }

    result = manager.save_connections(payload)
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    checklist = load_json(tmp_path / "config" / "launch_checklist.json", default={})

    assert result["production_ready"] is True
    assert result["health"]["status"] == "Production Connected"
    assert checklist["production_ready"] is True
    assert checklist["items"]["production_connections"]["status"] == "done"
    assert "note-token-secret" in env_text
    assert result["masked"]["NOTE_API_TOKEN"] != "note-token-secret"
    assert "****" in result["masked"]["NOTE_API_TOKEN"]


def test_operation_production_connection_status_never_returns_raw_secret(tmp_path: Path) -> None:
    (tmp_path / "config").mkdir()
    manager = ProductionConnectionManager(root=tmp_path, env_path=tmp_path / ".env")
    (tmp_path / ".env").write_text("NOTE_ACCOUNT_ID=abc\nNOTE_API_TOKEN=super-secret-token\n", encoding="utf-8")

    status = manager.current_status()

    assert status["connections"]["note"]["fields"]["NOTE_API_TOKEN"] != "super-secret-token"
    assert "****" in status["connections"]["note"]["fields"]["NOTE_API_TOKEN"]
