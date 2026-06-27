"""Shared type definitions and Protocols for Creator Factory OS factories."""
from __future__ import annotations
from typing import Protocol, TypedDict, runtime_checkable


# ── TypedDicts ────────────────────────────────────────────────────────────────

class FactoryCatalogEntry(TypedDict):
    name: str
    icon: str
    version: str
    module_path: str
    page: str
    config_files: list[str]
    dependencies: list[str]
    description: str


class ProjectRecord(TypedDict):
    project_id: str
    name: str
    owner: str
    factories: list[str]
    status: str          # active | paused | completed | archived
    revenue: int
    priority: int        # 1–5
    progress: float      # 0–100
    description: str
    created_at: str
    updated_at: str


class FactoryEventRecord(TypedDict):
    event_id: str
    event_type: str
    factory_name: str
    payload: dict
    timestamp: str


# ── Protocols ─────────────────────────────────────────────────────────────────

@runtime_checkable
class FactoryProtocol(Protocol):
    """Structural typing check — any object matching this shape is a valid factory."""
    NAME: str
    VERSION: str
    ICON: str

    def initialize(self) -> bool: ...
    def health_check(self) -> object: ...
    def sync_kpi(self) -> dict: ...
    def sync_dashboard(self) -> dict: ...
    def sync_mission_control(self) -> object: ...
    def generate_report(self, year_month: str = "") -> str: ...
    def export_status(self) -> dict: ...


@runtime_checkable
class ProjectProtocol(Protocol):
    """Structural typing check for project objects."""
    project_id: str
    name: str
    owner: str
    factories: list[str]
    status: str

    def get_summary(self) -> dict: ...
    def add_factory(self, factory_name: str) -> None: ...
    def remove_factory(self, factory_name: str) -> None: ...


# ── Factory status constants ───────────────────────────────────────────────────

FACTORY_STATUSES = ("active", "idle", "warning", "stopped")
FACTORY_HEALTH   = ("ok", "degraded", "failed")
PROJECT_STATUSES = ("active", "paused", "completed", "archived")

# Factory name → canonical icon
FACTORY_ICONS: dict[str, str] = {
    "AI動画工場":       "🎬",
    "note投稿工場":     "📝",
    "SNS投稿工場":      "📱",
    "承認アシスタント": "🔍",
    "営業工場":         "💼",
    "会計監査工場":     "💰",
    "アナリティクス工場": "📊",
}
