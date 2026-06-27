"""FactoryBase — abstract interface every Creator Factory OS factory must implement."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class HealthCheck:
    name: str
    passed: bool
    message: str = ""


@dataclass
class HealthReport:
    factory_name: str
    health: str                              # ok | degraded | failed
    checks: list[HealthCheck] = field(default_factory=list)
    checked_at: str = ""

    def to_dict(self) -> dict:
        return {
            "factory_name": self.factory_name,
            "health": self.health,
            "checks": [
                {"name": c.name, "passed": c.passed, "message": c.message}
                for c in self.checks
            ],
            "checked_at": self.checked_at,
        }


@dataclass
class FactoryStatus:
    name: str
    version: str
    status: str = "idle"       # active | idle | warning | stopped
    health: str = "ok"         # ok | degraded | failed
    last_update: str = ""
    completed_today: int = 0
    active_items: int = 0
    warning_count: int = 0
    next_action: str = ""
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name":            self.name,
            "version":         self.version,
            "status":          self.status,
            "health":          self.health,
            "last_update":     self.last_update,
            "completed_today": self.completed_today,
            "active_items":    self.active_items,
            "warning_count":   self.warning_count,
            "next_action":     self.next_action,
            "dependencies":    self.dependencies,
        }


class FactoryBase(ABC):
    """Abstract base class for all Creator Factory OS factories.

    Concrete factory adapters in factory_registry.py wrap existing factory
    modules and implement this interface without modifying the originals.
    """

    NAME: str = ""
    VERSION: str = ""
    ICON: str = "🏭"
    DEPENDENCIES: list[str] = []

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize factory. Return True if successful."""
        ...

    @abstractmethod
    def health_check(self) -> HealthReport:
        """Run factory health checks. Return HealthReport."""
        ...

    @abstractmethod
    def sync_kpi(self) -> dict:
        """Sync KPI data and return updated KPI dict."""
        ...

    @abstractmethod
    def sync_dashboard(self) -> dict:
        """Return dashboard summary dict."""
        ...

    @abstractmethod
    def sync_mission_control(self) -> FactoryStatus:
        """Return Mission Control status card data."""
        ...

    @abstractmethod
    def generate_report(self, year_month: str = "") -> str:
        """Generate factory Markdown report. Return report string."""
        ...

    @abstractmethod
    def export_status(self) -> dict:
        """Export current factory status as JSON-serializable dict."""
        ...

    def get_name(self) -> str:
        return self.NAME

    def get_version(self) -> str:
        return self.VERSION

    def get_icon(self) -> str:
        return self.ICON
