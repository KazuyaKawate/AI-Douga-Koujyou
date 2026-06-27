"""registry_builder — ModuleRegistry for Creator Factory OS SDK v5.1.

Aggregates all discovered module manifests into a queryable registry.
Provides export to config/module_registry.json (write-on-demand, never automatic).
"""
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

from src.sdk.module_loader import (
    load_all_manifests, load_all_with_errors,
    get_manifests_by_type, get_manifest, get_manifest_by_id,
)
from src.sdk.module_validator import validate_all
from src.sdk.module_manifest import SDK_VERSION

ROOT = Path(__file__).parent.parent.parent
REGISTRY_PATH = ROOT / "config" / "module_registry.json"

TYPE_ICONS = {
    "factory":     "🏭",
    "executive":   "🧠",
    "development": "🛠️",
    "utility":     "🔧",
}

STATUS_ICONS = {
    "stable":       "✅",
    "beta":         "🔶",
    "alpha":        "🔷",
    "deprecated":   "⚠️",
    "experimental": "🧪",
}


class ModuleRegistry:

    @staticmethod
    def get_all() -> list[dict]:
        return load_all_manifests()

    @staticmethod
    def get_by_type(module_type: str) -> list[dict]:
        return get_manifests_by_type(module_type)

    @staticmethod
    def get(module_name: str) -> dict | None:
        return get_manifest(module_name)

    @staticmethod
    def get_by_id(module_id: str) -> dict | None:
        return get_manifest_by_id(module_id)

    @staticmethod
    def get_factories() -> list[dict]:
        return get_manifests_by_type("factory")

    @staticmethod
    def get_executive_modules() -> list[dict]:
        return get_manifests_by_type("executive")

    @staticmethod
    def get_dev_modules() -> list[dict]:
        return get_manifests_by_type("development")

    @staticmethod
    def get_utilities() -> list[dict]:
        return get_manifests_by_type("utility")

    @staticmethod
    def get_summary() -> dict:
        all_modules = load_all_manifests()
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for m in all_modules:
            t = m.get("module_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
            s = m.get("status", "stable")
            by_status[s] = by_status.get(s, 0) + 1

        validation = validate_all(all_modules)
        registry_exported = REGISTRY_PATH.exists()
        registry_age: str | None = None
        if registry_exported:
            try:
                mtime = REGISTRY_PATH.stat().st_mtime
                registry_age = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        return {
            "sdk_version":      SDK_VERSION,
            "total":            len(all_modules),
            "by_type":          by_type,
            "by_status":        by_status,
            "factories":        by_type.get("factory", 0),
            "executive":        by_type.get("executive", 0),
            "development":      by_type.get("development", 0),
            "utilities":        by_type.get("utility", 0),
            "valid":            validation["valid"],
            "invalid":          validation["invalid"],
            "with_dashboard":   sum(1 for m in all_modules if m.get("dashboard_widget")),
            "with_mc_widget":   sum(1 for m in all_modules if m.get("mission_control_widget")),
            "registry_exported": registry_exported,
            "registry_age":     registry_age,
        }

    @staticmethod
    def get_validation_report() -> dict:
        """Return full validation results including per-module errors."""
        all_modules = load_all_manifests(include_invalid=True)
        return validate_all(all_modules)

    @staticmethod
    def get_icon(module_name: str) -> str:
        m = get_manifest(module_name)
        if not m:
            return "📦"
        return TYPE_ICONS.get(m.get("module_type", ""), "📦")

    @staticmethod
    def get_status_icon(module_name: str) -> str:
        m = get_manifest(module_name)
        if not m:
            return "❓"
        return STATUS_ICONS.get(m.get("status", "stable"), "❓")

    @staticmethod
    def export_registry() -> Path:
        """Write config/module_registry.json from current manifests.

        Called only on explicit user action — never automatically.
        Returns the path to the written file.
        """
        all_modules = load_all_manifests(include_invalid=True)
        validation = validate_all(all_modules)

        _SERIALIZABLE_KEYS = [
            "module_id", "display_name", "module_name", "module_type",
            "version", "sdk_version", "minimum_os_version", "status",
            "author", "description", "entrypoint", "package_path",
            "page_path", "health_check", "dashboard_widget",
            "mission_control_widget", "project_support",
            "dependencies", "config_files", "report_dir", "tags",
        ]
        serialized = []
        for m in all_modules:
            entry = {k: m.get(k) for k in _SERIALIZABLE_KEYS}
            serialized.append(entry)

        data = {
            "meta": {
                "sdk_version":   SDK_VERSION,
                "generated_at":  datetime.now().isoformat(timespec="seconds"),
                "total":         len(serialized),
                "valid":         validation["valid"],
                "invalid":       validation["invalid"],
            },
            "modules": serialized,
        }
        REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return REGISTRY_PATH

    @staticmethod
    def load_exported_registry() -> dict | None:
        """Read config/module_registry.json if it exists. Returns None if missing."""
        if not REGISTRY_PATH.exists():
            return None
        try:
            return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
