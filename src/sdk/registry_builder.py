"""registry_builder — ModuleRegistry for Creator Factory OS SDK.

Aggregates all discovered module manifests into a queryable registry.
Read-only. No writes to any data store.
"""
from __future__ import annotations
from src.sdk.module_loader import load_all_manifests, get_manifests_by_type, get_manifest
from src.sdk.module_validator import validate_all

TYPE_ICONS = {
    "factory":     "🏭",
    "executive":   "🧠",
    "development": "🛠️",
    "utility":     "🔧",
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
        for m in all_modules:
            t = m.get("module_type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

        validation = validate_all(all_modules)
        return {
            "total":          len(all_modules),
            "by_type":        by_type,
            "factories":      by_type.get("factory", 0),
            "executive":      by_type.get("executive", 0),
            "development":    by_type.get("development", 0),
            "utilities":      by_type.get("utility", 0),
            "valid":          validation["valid"],
            "invalid":        validation["invalid"],
            "with_dashboard": sum(1 for m in all_modules if m.get("dashboard_widget")),
            "with_mc_widget": sum(1 for m in all_modules if m.get("mission_control_widget")),
        }

    @staticmethod
    def get_icon(module_name: str) -> str:
        m = get_manifest(module_name)
        if not m:
            return "📦"
        return TYPE_ICONS.get(m.get("module_type", ""), "📦")
