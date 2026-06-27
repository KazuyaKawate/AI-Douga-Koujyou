"""workflow_manager — CRUD for Automation Factory workflows."""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from pathlib import Path

from src.factories.automation.automation_rules import WORKFLOW_TEMPLATES

ROOT        = Path(__file__).parent.parent.parent.parent
CONFIG_PATH = ROOT / "config" / "automation_workflows.json"


# ── Persistence ────────────────────────────────────────────────────────────────

def _default_store() -> dict:
    return {
        "workflows": list(WORKFLOW_TEMPLATES),
        "meta": {"version": "4.8", "created_at": datetime.now().strftime("%Y-%m-%d")},
    }


def load_workflows() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    data = _default_store()
    save_workflows(data)
    return data


def save_workflows(data: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── CRUD ──────────────────────────────────────────────────────────────────────

def get_all_workflows() -> list[dict]:
    return load_workflows().get("workflows", [])


def get_workflow(workflow_id: str) -> dict | None:
    for w in get_all_workflows():
        if w["workflow_id"] == workflow_id:
            return w
    return None


def get_enabled_workflows() -> list[dict]:
    return [w for w in get_all_workflows() if w.get("enabled", False)]


def create_workflow(
    name: str,
    description: str,
    trigger_type: str,
    trigger_config: dict,
    action_type: str,
    action_config: dict,
    enabled: bool = False,
) -> dict:
    workflow = {
        "workflow_id":    "wf_" + uuid.uuid4().hex[:8],
        "name":           name,
        "description":    description,
        "trigger_type":   trigger_type,
        "trigger_config": trigger_config,
        "action_type":    action_type,
        "action_config":  action_config,
        "enabled":        enabled,
        "run_count":      0,
        "last_run":       "",
        "created_at":     datetime.now().strftime("%Y-%m-%d"),
    }
    data = load_workflows()
    data["workflows"].append(workflow)
    save_workflows(data)
    return workflow


def update_workflow(workflow_id: str, **kwargs) -> tuple[bool, str]:
    data = load_workflows()
    allowed = {"name", "description", "trigger_type", "trigger_config",
               "action_type", "action_config", "enabled"}
    for w in data["workflows"]:
        if w["workflow_id"] == workflow_id:
            for k, v in kwargs.items():
                if k in allowed:
                    w[k] = v
            save_workflows(data)
            return True, "更新しました"
    return False, "ワークフローが見つかりません"


def toggle_enabled(workflow_id: str) -> tuple[bool, str, bool]:
    data = load_workflows()
    for w in data["workflows"]:
        if w["workflow_id"] == workflow_id:
            w["enabled"] = not w.get("enabled", False)
            save_workflows(data)
            state = "有効" if w["enabled"] else "無効"
            return True, f"{state}にしました", w["enabled"]
    return False, "ワークフローが見つかりません", False


def delete_workflow(workflow_id: str) -> tuple[bool, str]:
    data = load_workflows()
    before = len(data["workflows"])
    data["workflows"] = [w for w in data["workflows"] if w["workflow_id"] != workflow_id]
    if len(data["workflows"]) == before:
        return False, "ワークフローが見つかりません"
    save_workflows(data)
    return True, "削除しました"


def record_run(workflow_id: str) -> None:
    data = load_workflows()
    for w in data["workflows"]:
        if w["workflow_id"] == workflow_id:
            w["run_count"] = w.get("run_count", 0) + 1
            w["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            break
    save_workflows(data)


def get_workflow_summary() -> dict:
    workflows = get_all_workflows()
    enabled   = sum(1 for w in workflows if w.get("enabled"))
    total_runs = sum(w.get("run_count", 0) for w in workflows)
    return {
        "total":      len(workflows),
        "enabled":    enabled,
        "disabled":   len(workflows) - enabled,
        "total_runs": total_runs,
    }
