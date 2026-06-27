"""automation_runner — orchestrate workflow trigger evaluation and action execution."""
from __future__ import annotations
import uuid
from datetime import datetime


def run_workflow(workflow_id: str, dry_run: bool = True) -> dict:
    """Run a single workflow. dry_run=True by default. Returns run record."""
    from src.factories.automation.workflow_manager import get_workflow, record_run
    from src.factories.automation.trigger_engine   import evaluate_trigger
    from src.factories.automation.action_engine    import execute_action
    from src.factories.automation.automation_reporter import log_run

    workflow = get_workflow(workflow_id)
    if not workflow:
        return {
            "run_id": "run_" + uuid.uuid4().hex[:8],
            "workflow_id": workflow_id,
            "workflow_name": "不明",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "dry_run": dry_run,
            "trigger_fired": False,
            "trigger_reason": "ワークフローが見つかりません",
            "action_result": None,
            "success": False,
        }

    trigger_result = evaluate_trigger(
        workflow["trigger_type"],
        workflow.get("trigger_config", {}),
    )

    run_record: dict = {
        "run_id":          "run_" + uuid.uuid4().hex[:8],
        "workflow_id":     workflow_id,
        "workflow_name":   workflow["name"],
        "timestamp":       datetime.now().isoformat(timespec="seconds"),
        "dry_run":         dry_run,
        "trigger_fired":   trigger_result["fired"],
        "trigger_reason":  trigger_result["reason"],
        "action_result":   None,
        "success":         False,
    }

    if trigger_result["fired"]:
        action_result = execute_action(
            workflow["action_type"],
            workflow.get("action_config", {}),
            trigger_result.get("context", {}),
            dry_run=dry_run,
        )
        run_record["action_result"] = {
            "type":        workflow["action_type"],
            "success":     action_result["success"],
            "description": action_result["description"],
        }
        run_record["success"] = action_result["success"]
    else:
        run_record["success"] = True  # trigger didn't fire = no error

    log_run(run_record)
    if not dry_run and trigger_result["fired"]:
        record_run(workflow_id)
    return run_record


def run_all_enabled(dry_run: bool = True) -> list[dict]:
    """Run all enabled workflows. Returns list of run records."""
    from src.factories.automation.workflow_manager import get_enabled_workflows
    workflows = get_enabled_workflows()
    return [run_workflow(w["workflow_id"], dry_run=dry_run) for w in workflows]


def run_single_by_trigger(trigger_type: str, dry_run: bool = True) -> list[dict]:
    """Run all enabled workflows matching a specific trigger type."""
    from src.factories.automation.workflow_manager import get_enabled_workflows
    matching = [w for w in get_enabled_workflows() if w["trigger_type"] == trigger_type]
    return [run_workflow(w["workflow_id"], dry_run=dry_run) for w in matching]
