from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.business_engine.manager import BusinessEngineStore
from src.creator_factory.factory_manager import CreatorFactoryManager
from src.export.export_manager import ExportManager
from src.pipeline.pipeline_manager import PipelineManager
from src.utils.json_store import load_json, save_json_atomic

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_ROOT = ROOT / "data"

AUTOMATION_TYPES = [
    "creator_factory",
    "seo_blog",
    "sns",
    "affiliate",
    "business_report",
    "knowledge_update",
    "template_refresh",
    "pipeline_cleanup",
    "export_cleanup",
]
SCHEDULE_TYPES = ["hourly", "daily", "weekly", "monthly", "custom_interval", "manual"]
RULE_STATUSES = ["enabled", "disabled", "paused", "deleted"]
TYPE_TO_PIPELINE = {
    "creator_factory": "note",
    "seo_blog": "seo_blog",
    "sns": "sns",
    "affiliate": "affiliate",
    "business_report": "business_report",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _next_run(schedule_type: str, interval_minutes: int, anchor: datetime | None = None) -> str:
    if schedule_type == "manual":
        return ""
    anchor = anchor or datetime.now()
    if schedule_type == "hourly":
        delta = timedelta(hours=1)
    elif schedule_type == "daily":
        delta = timedelta(days=1)
    elif schedule_type == "weekly":
        delta = timedelta(weeks=1)
    elif schedule_type == "monthly":
        delta = timedelta(days=30)
    else:
        delta = timedelta(minutes=max(int(interval_minutes or 60), 1))
    return (anchor + delta).isoformat(timespec="seconds")


class AutomationManager:
    """Local scheduler and automation rule manager."""

    def __init__(
        self,
        data_root: str | Path = DEFAULT_DATA_ROOT,
        *,
        creator: CreatorFactoryManager | None = None,
        business: BusinessEngineStore | None = None,
        pipeline: PipelineManager | None = None,
        export_manager: ExportManager | None = None,
    ) -> None:
        self.data_root = Path(data_root)
        self.automation_dir = self.data_root / "automation"
        self.history_dir = self.automation_dir / "history"
        self.automation_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.rules_path = self.automation_dir / "rules.json"
        self.log_path = self.automation_dir / "execution_log.json"
        self.creator = creator or CreatorFactoryManager(self.data_root)
        self.business = business or BusinessEngineStore()
        self.export_manager = export_manager or ExportManager()
        self.pipeline = pipeline or PipelineManager(
            self.data_root,
            creator=self.creator,
            business=self.business,
            export_manager=self.export_manager,
        )

    def create_rule(
        self,
        name: str,
        automation_type: str,
        *,
        schedule_type: str = "manual",
        interval_minutes: int = 60,
        project_id: str = "",
        template_id: str = "",
        priority: str = "normal",
        auto_generate: bool = True,
        auto_queue: bool = True,
        auto_approve: bool = False,
        manual_override: bool = True,
        enabled: bool = True,
    ) -> dict[str, Any]:
        if automation_type not in AUTOMATION_TYPES:
            automation_type = "creator_factory"
        if schedule_type not in SCHEDULE_TYPES:
            schedule_type = "manual"
        interval_minutes = max(int(interval_minutes or 60), 1)
        rule = {
            "rule_id": _new_id("auto"),
            "name": name,
            "automation_type": automation_type,
            "schedule_type": schedule_type,
            "interval_minutes": interval_minutes,
            "project_id": project_id,
            "template_id": template_id,
            "priority": priority,
            "status": "enabled" if enabled else "disabled",
            "auto_generate": bool(auto_generate),
            "auto_queue": bool(auto_queue),
            "auto_approve": bool(auto_approve),
            "manual_override": bool(manual_override),
            "last_run": "",
            "next_run": _next_run(schedule_type, interval_minutes),
            "missed_runs": 0,
            "retry_count": 0,
            "created_at": _now(),
            "updated_at": _now(),
        }
        data = self._load_rules()
        data["rules"].insert(0, rule)
        self._save_rules(data)
        return rule

    def list_rules(self, include_deleted: bool = False) -> list[dict[str, Any]]:
        rules = self._load_rules().get("rules", [])
        if not include_deleted:
            rules = [rule for rule in rules if rule.get("status") != "deleted"]
        return sorted(rules, key=lambda row: row.get("updated_at", row.get("created_at", "")), reverse=True)

    def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        return next((rule for rule in self._load_rules().get("rules", []) if rule.get("rule_id") == rule_id), None)

    def enable_rule(self, rule_id: str) -> dict[str, Any] | None:
        return self._set_rule_status(rule_id, "enabled")

    def disable_rule(self, rule_id: str) -> dict[str, Any] | None:
        return self._set_rule_status(rule_id, "disabled")

    def pause_rule(self, rule_id: str) -> dict[str, Any] | None:
        return self._set_rule_status(rule_id, "paused")

    def resume_rule(self, rule_id: str) -> dict[str, Any] | None:
        return self._set_rule_status(rule_id, "enabled")

    def delete_rule(self, rule_id: str) -> dict[str, Any] | None:
        return self._set_rule_status(rule_id, "deleted")

    def due_rules(self, at: datetime | None = None) -> list[dict[str, Any]]:
        at = at or datetime.now()
        due = []
        for rule in self.list_rules():
            if rule.get("status") != "enabled" or rule.get("schedule_type") == "manual":
                continue
            try:
                if datetime.fromisoformat(rule.get("next_run", "")) <= at:
                    due.append(rule)
            except ValueError:
                due.append(rule)
        return due

    def detect_missed_runs(self, at: datetime | None = None) -> int:
        at = at or datetime.now()
        data = self._load_rules()
        count = 0
        for rule in data.get("rules", []):
            if rule.get("status") != "enabled" or not rule.get("next_run"):
                continue
            try:
                next_run = datetime.fromisoformat(rule["next_run"])
            except ValueError:
                continue
            if next_run < at - timedelta(minutes=max(int(rule.get("interval_minutes", 60)), 1)):
                rule["missed_runs"] = int(rule.get("missed_runs", 0)) + 1
                rule["updated_at"] = _now()
                count += 1
        if count:
            self._save_rules(data)
        return count

    def run_due(self, at: datetime | None = None, limit: int = 10) -> list[dict[str, Any]]:
        self.detect_missed_runs(at)
        return [self.run_rule(rule["rule_id"]) for rule in self.due_rules(at)[: max(limit, 0)]]

    def manual_run(self, rule_id: str) -> dict[str, Any]:
        return self.run_rule(rule_id, manual=True)

    def retry_execution(self, execution_id: str) -> dict[str, Any] | None:
        execution = self.get_execution(execution_id)
        if execution is None:
            return None
        rule = self.get_rule(execution.get("rule_id", ""))
        if rule is None:
            return None
        rule["retry_count"] = int(rule.get("retry_count", 0)) + 1
        self._update_rule(rule)
        return self.run_rule(rule["rule_id"], manual=True, retry_of=execution_id)

    def run_rule(self, rule_id: str, *, manual: bool = False, retry_of: str = "") -> dict[str, Any]:
        rule = self.get_rule(rule_id)
        if rule is None:
            raise ValueError(f"Automation rule not found: {rule_id}")
        if rule.get("status") in ("disabled", "paused", "deleted") and not manual:
            return self._record_execution(rule, "cancelled", ["Rule is not enabled."], retry_of=retry_of)

        execution = self._record_execution(rule, "running", ["Automation started."], retry_of=retry_of)
        started = datetime.now()
        try:
            if rule.get("automation_type") in TYPE_TO_PIPELINE:
                execution = self._run_pipeline_rule(rule, execution)
            else:
                execution = self._run_maintenance_rule(rule, execution)
            execution["status"] = "completed"
            execution["runtime_ms"] = int((datetime.now() - started).total_seconds() * 1000)
            execution["logs"].append("Automation completed locally.")
            self._save_execution(execution)
            self._append_log(execution)
            self._finalize_rule_success(rule)
            return execution
        except Exception as exc:
            execution["status"] = "failed"
            execution["runtime_ms"] = int((datetime.now() - started).total_seconds() * 1000)
            execution["error"] = str(exc)
            execution["logs"].append(str(exc))
            self._save_execution(execution)
            self._append_log(execution)
            return execution

    def history(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = []
        for path in self.history_dir.glob("exec_*.json"):
            data = load_json(path, default=None)
            if isinstance(data, dict):
                rows.append(data)
        return sorted(rows, key=lambda row: row.get("created_at", ""), reverse=True)[:limit]

    def execution_log(self, limit: int = 100) -> list[dict[str, Any]]:
        data = load_json(self.log_path, default=None)
        rows = data.get("logs", []) if isinstance(data, dict) else []
        return rows[:limit]

    def get_execution(self, execution_id: str) -> dict[str, Any] | None:
        data = load_json(self.history_dir / f"{execution_id}.json", default=None)
        return data if isinstance(data, dict) else None

    def dashboard_summary(self) -> dict[str, Any]:
        rules = self.list_rules()
        history = self.history()
        today = date.today().isoformat()
        running = [row for row in history if row.get("status") == "running"]
        failures = [row for row in history if row.get("status") == "failed"]
        retries = [row for row in history if row.get("retry_of")]
        completed = [row for row in history if row.get("status") == "completed"]
        avg_runtime = int(sum(int(row.get("runtime_ms", 0)) for row in completed) / len(completed)) if completed else 0
        upcoming = sorted(
            [rule for rule in rules if rule.get("status") == "enabled" and rule.get("next_run")],
            key=lambda rule: rule.get("next_run", ""),
        )
        return {
            "running_automations": len(running),
            "today_runs": sum(1 for row in history if str(row.get("created_at", "")).startswith(today)),
            "failures": len(failures),
            "retries": len(retries),
            "average_runtime": avg_runtime,
            "upcoming_jobs": len(upcoming),
            "disabled_jobs": sum(1 for rule in rules if rule.get("status") in ("disabled", "paused")),
            "automation_queue": len(self.due_rules()),
            "next_scheduled_job": upcoming[0].get("name", "None") if upcoming else "None",
            "local_first": True,
            "external_apis_enabled": False,
        }

    def _run_pipeline_rule(self, rule: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
        pipeline_name = TYPE_TO_PIPELINE[rule["automation_type"]]
        title = f"{rule.get('name', 'Automation')} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        if not rule.get("auto_queue", True):
            execution["logs"].append("Auto queue disabled; no pipeline job created.")
            return execution
        job = self.pipeline.create_production_job(
            pipeline_name,
            title,
            project_id=rule.get("project_id", ""),
            template_id=rule.get("template_id", ""),
            priority=rule.get("priority", "normal"),
        )
        execution["pipeline_id"] = job["job_id"]
        execution["runtime"] = job.get("runtime", "local_template")
        execution["logs"].append(f"Pipeline job created: {job['job_id']}")
        if rule.get("auto_generate", True):
            generated = self.pipeline.run_until_review(job["job_id"])
            execution["runtime"] = generated.get("runtime", execution.get("runtime", "virtual"))
            execution["provider"] = generated.get("provider", execution["runtime"])
            execution["generation_time_ms"] = generated.get("generation_time_ms", 0)
            execution["input_tokens"] = generated.get("input_tokens", 0)
            execution["output_tokens"] = generated.get("output_tokens", 0)
            execution["provider_error"] = generated.get("provider_error", "")
            execution["approval_id"] = generated.get("approval_result", {}).get("review_id", "")
            execution["checksum"] = generated.get("checksum", "")
            execution["logs"].append(f"Generated locally: {generated.get('status')}")
            if rule.get("auto_approve", False):
                self.pipeline.approve_pipeline_job(job["job_id"])
                completed = self.pipeline.export_pipeline_job(job["job_id"])
                execution["export_id"] = completed.get("export_result", {}).get("export_id", "")
                execution["checksum"] = completed.get("checksum", execution.get("checksum", ""))
                execution["logs"].append(f"Export completed: {completed.get('status')}")
        return execution

    def _run_maintenance_rule(self, rule: dict[str, Any], execution: dict[str, Any]) -> dict[str, Any]:
        automation_type = rule.get("automation_type", "")
        if automation_type == "knowledge_update":
            self.creator.add_knowledge_item(rule.get("name", "Automation note"), "business_knowledge", "Local automation knowledge update.")
            execution["logs"].append("Knowledge item updated locally.")
        elif automation_type == "template_refresh":
            self.creator.create_template(f"{rule.get('name', 'Template')} Refresh", "note_article")
            execution["logs"].append("Template refreshed locally.")
        elif automation_type == "pipeline_cleanup":
            execution["logs"].append("Pipeline cleanup checked local history.")
        elif automation_type == "export_cleanup":
            cleared = self.export_manager.clear_completed_exports()
            execution["logs"].append(f"Cleared completed export records: {cleared}")
        else:
            execution["logs"].append("No-op local automation.")
        return execution

    def _record_execution(
        self,
        rule: dict[str, Any],
        status: str,
        logs: list[str] | None = None,
        *,
        retry_of: str = "",
    ) -> dict[str, Any]:
        execution = {
            "execution_id": _new_id("exec"),
            "rule_id": rule.get("rule_id", ""),
            "project": rule.get("project_id", ""),
            "template": rule.get("template_id", ""),
            "runtime": "local_template",
            "provider": "virtual",
            "generation_time_ms": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "provider_error": "",
            "status": status,
            "pipeline_id": "",
            "approval_id": "",
            "export_id": "",
            "checksum": "",
            "logs": logs or [],
            "retry_of": retry_of,
            "created_at": _now(),
            "updated_at": _now(),
            "runtime_ms": 0,
            "local_first": True,
            "external_apis_enabled": False,
        }
        self._save_execution(execution)
        self._append_log(execution)
        return execution

    def _save_execution(self, execution: dict[str, Any]) -> Path:
        execution["updated_at"] = _now()
        return save_json_atomic(self.history_dir / f"{execution['execution_id']}.json", execution)

    def _append_log(self, execution: dict[str, Any]) -> None:
        data = load_json(self.log_path, default=None)
        if not isinstance(data, dict):
            data = {"logs": []}
        data.setdefault("logs", []).insert(0, {
            "execution_id": execution.get("execution_id", ""),
            "rule_id": execution.get("rule_id", ""),
            "status": execution.get("status", ""),
            "message": "; ".join(execution.get("logs", [])[-3:]),
            "created_at": _now(),
        })
        data["logs"] = data["logs"][:500]
        save_json_atomic(self.log_path, data)

    def _load_rules(self) -> dict[str, Any]:
        data = load_json(self.rules_path, default=None)
        if not isinstance(data, dict):
            data = {
                "meta": {
                    "version": "5.2-phase11",
                    "created_at": _now(),
                    "local_first": True,
                    "external_apis_enabled": False,
                },
                "rules": [],
            }
            self._save_rules(data)
        data.setdefault("rules", [])
        data.setdefault("meta", {})
        data["meta"].setdefault("local_first", True)
        data["meta"].setdefault("external_apis_enabled", False)
        return data

    def _save_rules(self, data: dict[str, Any]) -> Path:
        data.setdefault("meta", {})
        data["meta"]["updated_at"] = _now()
        return save_json_atomic(self.rules_path, data)

    def _set_rule_status(self, rule_id: str, status: str) -> dict[str, Any] | None:
        if status not in RULE_STATUSES:
            return None
        data = self._load_rules()
        for rule in data.get("rules", []):
            if rule.get("rule_id") == rule_id:
                rule["status"] = status
                if status == "enabled" and not rule.get("next_run"):
                    rule["next_run"] = _next_run(rule.get("schedule_type", "manual"), int(rule.get("interval_minutes", 60)))
                rule["updated_at"] = _now()
                self._save_rules(data)
                return rule
        return None

    def _update_rule(self, rule: dict[str, Any]) -> None:
        data = self._load_rules()
        for index, current in enumerate(data.get("rules", [])):
            if current.get("rule_id") == rule.get("rule_id"):
                rule["updated_at"] = _now()
                data["rules"][index] = rule
                self._save_rules(data)
                return

    def _finalize_rule_success(self, rule: dict[str, Any]) -> None:
        updated = dict(rule)
        updated["last_run"] = _now()
        updated["next_run"] = _next_run(
            updated.get("schedule_type", "manual"),
            int(updated.get("interval_minutes", 60)),
            datetime.now(),
        )
        updated["updated_at"] = _now()
        self._update_rule(updated)


def automation_summary(data_root: str | Path = DEFAULT_DATA_ROOT) -> dict[str, Any]:
    return AutomationManager(data_root).dashboard_summary()
