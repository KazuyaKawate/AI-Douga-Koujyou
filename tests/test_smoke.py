import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SKIP_PARTS = {".git", "venv", ".venv", "__pycache__"}


def _iter_files(pattern: str):
    for path in ROOT.rglob(pattern):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        yield path


def test_python_files_parse_as_ast():
    errors = []
    count = 0
    for path in _iter_files("*.py"):
        count += 1
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = path.read_text(encoding="cp932")
        try:
            ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc.msg} line {exc.lineno}:{exc.offset}")

    assert count > 0
    assert errors == []


def test_json_files_are_valid():
    errors = []
    count = 0
    for path in _iter_files("*.json"):
        count += 1
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")

    assert count > 0
    assert errors == []


def test_kernel_starts_and_reports_health():
    from src.core.kernel import get_kernel, reset_kernel

    reset_kernel()
    kernel = get_kernel()
    health = kernel.health()

    assert health["kernel"] == "ok"
    assert health["workflows"]["registered"] >= 1
    assert health["factories"]["registered"] >= 1


def test_workflow_registry_discovers_note_daily_and_required_executors():
    from src.orchestrator.registry import FactoryRegistry
    from src.workflow.executors import EXECUTOR_REGISTRY

    workflow_path = ROOT / "config" / "workflow_definitions" / "note_daily.json"
    workflow_data = json.loads(workflow_path.read_text(encoding="utf-8"))
    required_step_types = {step["step_type"] for step in workflow_data["steps"]}

    missing = sorted(required_step_types - set(EXECUTOR_REGISTRY))
    assert missing == []

    registry = FactoryRegistry()
    summary = registry.auto_discover()

    assert summary["executors"] >= len(required_step_types)
    assert "note" in registry.list_factories()
    assert registry.get_workflow("note_daily") is not None


def test_ai_router_virtual_provider_routes_without_external_api(tmp_path):
    from src.ai.router import AIRouter
    from src.ai.task import AITask, TaskType

    config_path = tmp_path / "ai_router_virtual.json"
    config_path.write_text(
        json.dumps(
            {
                "version": "test",
                "default_provider": "virtual",
                "task_routing": {"default": ["virtual"]},
                "providers": {
                    "virtual": {
                        "enabled": True,
                        "model": "virtual-agent-v1",
                        "capabilities": ["default", "writing", "analysis"],
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    router = AIRouter(config_path=config_path)
    response = router.route(AITask(task_type=TaskType.DEFAULT, prompt="ping"))

    assert response.ok is True
    assert response.provider == "virtual"
    assert response.metadata and response.metadata.get("virtual") is True
    assert response.content


def test_streamlit_import_smoke():
    import streamlit as st

    assert hasattr(st, "set_page_config")
    assert hasattr(st, "title")


def test_safe_workflow_execution_with_memory_update(tmp_path):
    from src.ai.memory import InMemoryProvider, MemoryScope
    from src.workflow.enums import OnFailure, StepType, WorkflowState
    from src.workflow.models import WorkflowDefinition, WorkflowStep
    from src.workflow.runner import WorkflowRunner

    memory = InMemoryProvider()
    runner = WorkflowRunner(memory=memory, store_dir=tmp_path)
    definition = WorkflowDefinition(
        name="smoke.memory_update",
        description="Safe smoke workflow with no external API calls",
        steps=[
            WorkflowStep(
                step_id="remember",
                step_type=StepType.MEMORY_UPDATE,
                name="Remember smoke value",
                config={
                    "key": "smoke_key",
                    "value": "smoke_value",
                    "scope": "session",
                },
                on_failure=OnFailure.ABORT,
            )
        ],
    )

    status = runner.run(definition)

    assert status.state == WorkflowState.COMPLETED
    assert memory.get("smoke_key", MemoryScope.SESSION) == "smoke_value"
    assert (tmp_path / f"{status.workflow_id}.json").exists()
