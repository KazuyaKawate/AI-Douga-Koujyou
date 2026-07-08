from __future__ import annotations

import subprocess
from pathlib import Path

from src.coding_engine.code_editor import CodeEditor
from src.coding_engine.coding_manager import CodingEngineManager
from src.coding_engine.provider_router import CodingProviderRouter
from src.coding_engine.revenue_gate import CommanderRevenueGate
from src.coding_engine.task_executor import CodingTaskExecutor
from src.utils.json_store import load_json


def test_revenue_gate_prioritizes_first_revenue_paths_and_defers_low_roi() -> None:
    gate = CommanderRevenueGate()

    high = gate.evaluate("実投稿からPV取得、初クリック、アフィリエイト収益を改善", ["src/publish_engine/publisher.py"])
    low = gate.evaluate("設定画面の見た目を大型リファクタする", ["pages/9_Settings.py"])

    assert high["decision"] == "prioritize"
    assert high["score"] > low["score"]
    assert low["decision"] == "defer"
    assert high["question"] == "この機能は初収益を近付けるか？"


def test_provider_health_probe_reports_ollama_missing(monkeypatch) -> None:
    monkeypatch.setattr("src.coding_engine.provider_router.shutil.which", lambda name: None)

    health = CodingProviderRouter(["ollama"]).health_probe(timeout_seconds=1)

    assert health[0]["provider"] == "ollama"
    assert health[0]["status"] == "missing"


def test_provider_health_probe_reports_ollama_ready_and_models(monkeypatch) -> None:
    def fake_run(command, **kwargs):
        normalized = [Path(command[0]).stem, *command[1:]]
        if normalized == ["ollama", "version"]:
            return subprocess.CompletedProcess(command, 0, stdout="ollama version 0.1.0\n", stderr="")
        if normalized == ["ollama", "list"]:
            return subprocess.CompletedProcess(command, 0, stdout="NAME ID SIZE\ncodellama latest 4GB\n", stderr="")
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="bad command")

    monkeypatch.setattr("src.coding_engine.provider_router.shutil.which", lambda name: "ollama.exe")
    monkeypatch.setattr("src.coding_engine.provider_router.subprocess.run", fake_run)

    health = CodingProviderRouter(["ollama"]).health_probe(timeout_seconds=1)

    assert health[0]["status"] == "ready"
    assert health[0]["models"]["status"] == "ready"
    assert health[0]["models"]["items"]


def test_diff_preview_lock_blocks_apply_without_approval(tmp_path: Path, monkeypatch) -> None:
    editor = CodeEditor(tmp_path)
    generated = {
        "content": """```diff
diff --git a/src/a.py b/src/a.py
--- a/src/a.py
+++ b/src/a.py
@@ -1 +1 @@
-old
+new
```"""
    }
    calls = []

    def fake_git_apply(patch: str, *, check: bool):
        calls.append(check)
        return {"ok": True, "command": "git apply --check" if check else "git apply", "stdout": "", "stderr": ""}

    monkeypatch.setattr(editor, "_git_apply", fake_git_apply)

    result = editor.apply_generated_patch(generated, approved=False, target_files=["src/a.py"])

    assert result["status"] == "preview_locked"
    assert result["applied"] is False
    assert calls == [True]
    assert result["preview"]["requires_approval"] is True
    assert "diff --git" in result["preview"]["unified_diff"]


def test_diff_preview_lock_allows_apply_with_approval(tmp_path: Path, monkeypatch) -> None:
    editor = CodeEditor(tmp_path)
    generated = {"content": "diff --git a/src/a.py b/src/a.py\n--- a/src/a.py\n+++ b/src/a.py\n@@ -1 +1 @@\n-old\n+new\n"}
    calls = []

    def fake_git_apply(patch: str, *, check: bool):
        calls.append(check)
        return {"ok": True, "command": "git apply --check" if check else "git apply", "stdout": "", "stderr": ""}

    monkeypatch.setattr(editor, "_git_apply", fake_git_apply)

    result = editor.apply_generated_patch(generated, approved=True, target_files=["src/a.py"])

    assert result["status"] == "applied"
    assert result["applied"] is True
    assert calls == [True, False]


def test_coding_manager_saves_revenue_queue_and_business_manager_feedback(tmp_path: Path, monkeypatch) -> None:
    config_root = tmp_path
    (config_root / "config").mkdir()
    state_path = config_root / "config" / "coding_engine.json"
    monkeypatch.setattr("src.coding_engine.coding_manager.PROJECT_ROOT", config_root)

    def fake_execute(self, issue, *, target_files=None, run_tests=False, pytest_args=None, apply_approved=False):
        return {
            "run_id": "ce-test",
            "status": "needs_attention",
            "issue": issue,
            "plan": {"plan_id": "cp-test", "target_files": target_files or []},
            "applied_edits": {"status": "preview_locked", "applied": False},
            "revenue_gate": {"score": 88, "decision": "prioritize"},
            "review": {"status": "approved"},
            "tests": {"ok": True, "results": []},
            "commit_candidate": {"ready": True},
            "business_evaluation": {"score": {"constitution_priority_score": 90, "estimated_revenue": 12000}},
            "knowledge_record": {"id": "knowledge-test"},
        }

    monkeypatch.setattr(CodingTaskExecutor, "execute", fake_execute)

    manager = CodingEngineManager(path=state_path, root=tmp_path)
    manager.run_issue("実投稿とPV取得を改善", target_files=["src/publish_engine/publisher.py"])
    coding_state = load_json(state_path, default={})
    business_state = load_json(config_root / "config" / "business_manager.json", default={})

    assert coding_state["revenue_improvement_queue"][0]["revenue_gate"]["decision"] == "prioritize"
    assert coding_state["business_manager_feedback"][0]["run_id"] == "ce-test"
    assert business_state["coding_engine_feedback"][0]["run_id"] == "ce-test"
