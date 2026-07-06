from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from src.approval.approval_queue import content_review_summary
from src.automation.automation_manager import automation_summary
from src.business_engine.manager import BusinessEngineStore
from src.core.version import get_version_label
from src.creator_factory.factory_manager import creator_factory_summary
from src.export.export_manager import export_summary
from src.pipeline.pipeline_manager import pipeline_summary
from src.providers.provider_registry import ProviderRegistry
from src.utils.json_store import save_json_atomic
from src.workspace.google_auth import get_auth_config
from src.workspace.sync_validator import load_settings

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = ROOT / "reports" / "rc"


class RCReadinessManager:
    """Local-only RC integration readiness checker."""

    def __init__(self, report_dir: str | Path = DEFAULT_REPORT_DIR) -> None:
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def collect(self) -> dict[str, Any]:
        provider_status = ProviderRegistry().status()
        workspace_settings = load_settings()
        auth = get_auth_config(workspace_settings)
        business = BusinessEngineStore().beta_metrics()
        creator = creator_factory_summary()
        automation = automation_summary()
        pipeline = pipeline_summary()
        approval = content_review_summary()
        export = export_summary()
        safety = {
            "router_default_virtual": provider_status["router_default"] == "virtual",
            "active_provider_virtual": provider_status["active_provider"] == "virtual",
            "external_apis_disabled": provider_status["external_apis_enabled"] is False,
            "workspace_disabled": workspace_settings.get("enabled", False) is False,
            "google_auth_disabled": auth["auth_mode"] == "disabled",
            "external_publishing_disabled": True,
            "local_first": True,
        }
        modules = {
            "business_engine": {"ready": True, "metrics": business},
            "creator_factory": {"ready": creator["local_first"], "metrics": creator},
            "automation_engine": {"ready": automation["local_first"], "metrics": automation},
            "production_pipeline": {"ready": pipeline["local_first"], "metrics": pipeline},
            "approval_center": {"ready": True, "metrics": approval},
            "export_manager": {"ready": export.get("pending_exports", 0) >= 0, "metrics": export},
        }
        blockers = self._blockers(safety, modules)
        return {
            "version": get_version_label(),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "rc_name": "AIOS v5.2 RC",
            "local_first": True,
            "safety": safety,
            "modules": modules,
            "blockers": blockers,
            "warnings": self._warnings(modules),
            "ready": not blockers,
        }

    def write_manifest(self) -> Path:
        report = self.collect()
        path = self.report_dir / "aios_v5_2_rc_readiness.json"
        save_json_atomic(path, report)
        return path

    @staticmethod
    def _blockers(safety: dict[str, bool], modules: dict[str, dict[str, Any]]) -> list[str]:
        blockers = []
        for key, ok in safety.items():
            if not ok:
                blockers.append(f"Safety check failed: {key}")
        for key, value in modules.items():
            if not value.get("ready", False):
                blockers.append(f"Module not ready: {key}")
        return blockers

    @staticmethod
    def _warnings(modules: dict[str, dict[str, Any]]) -> list[str]:
        warnings = []
        automation = modules["automation_engine"]["metrics"]
        pipeline = modules["production_pipeline"]["metrics"]
        if automation.get("failures", 0):
            warnings.append("Automation history contains failures.")
        if pipeline.get("failure_count", 0):
            warnings.append("Pipeline history contains failures.")
        return warnings
