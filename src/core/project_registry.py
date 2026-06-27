"""ProjectRegistry — aggregate health and status across all projects and factories."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


class ProjectRegistry:
    """System-level view: aggregates projects + factory health into one summary."""

    @staticmethod
    def get_system_summary() -> dict:
        from src.core.project_manager import get_all_projects
        from src.core.factory_registry import FactoryRegistry

        projects = get_all_projects()
        factory_summary = FactoryRegistry.get_summary()

        active_projects   = sum(1 for p in projects if p.status == "active")
        total_revenue     = sum(p.revenue for p in projects)
        total_factories   = factory_summary["total"]
        healthy_factories = factory_summary["healthy"]

        if total_factories > 0:
            health_pct = round(healthy_factories / total_factories * 100)
        else:
            health_pct = 0

        if health_pct == 100:
            system_health = "ok"
        elif health_pct >= 60:
            system_health = "degraded"
        else:
            system_health = "failed"

        return {
            "total_projects":    len(projects),
            "active_projects":   active_projects,
            "total_revenue":     total_revenue,
            "total_factories":   total_factories,
            "healthy_factories": healthy_factories,
            "health_pct":        health_pct,
            "system_health":     system_health,
            "generated_at":      datetime.now().isoformat(timespec="seconds"),
        }

    @staticmethod
    def get_project_factory_health(project_id: str) -> dict:
        from src.core.project_manager import get_project
        from src.core.factory_registry import FactoryRegistry

        project = get_project(project_id)
        if not project:
            return {"error": "project not found"}

        health_results = [
            FactoryRegistry.check_health(name)
            for name in project.factories
        ]
        ok_count = sum(1 for h in health_results if h["health"] == "ok")
        return {
            "project_id":   project_id,
            "project_name": project.name,
            "factory_count": len(project.factories),
            "healthy_count": ok_count,
            "factory_health": health_results,
        }

    @staticmethod
    def get_all_project_summaries() -> list[dict]:
        from src.core.project_manager import get_all_projects
        return [p.get_summary() for p in get_all_projects()]

    @staticmethod
    def find_projects_by_factory(factory_name: str) -> list[dict]:
        from src.core.project_manager import get_all_projects
        return [
            p.get_summary()
            for p in get_all_projects()
            if factory_name in p.factories
        ]
