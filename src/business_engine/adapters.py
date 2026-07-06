from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PUBLISHING_ADAPTERS = ["note", "x", "threads", "instagram", "wordpress", "blogger", "medium"]
AFFILIATE_ADAPTERS = ["amazon", "a8", "rakuten", "valuecommerce", "linkshare"]
SEO_PROVIDERS = ["google_search_console", "google_analytics", "manual_csv"]


@dataclass(frozen=True)
class AdapterDefinition:
    adapter_id: str
    name: str
    category: str
    enabled: bool = False
    configured: bool = False
    api_status: str = "disabled"


class AdapterRegistry:
    """Disabled-by-default external integration registry.

    Phase 4 exposes deployable adapter boundaries, but execution remains
    local-first. No adapter performs network I/O from this registry.
    """

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state = state or {}

    def all(self) -> list[AdapterDefinition]:
        return [
            *self._build("publishing", PUBLISHING_ADAPTERS),
            *self._build("affiliate", AFFILIATE_ADAPTERS),
            *self._build("seo", SEO_PROVIDERS),
        ]

    def by_category(self, category: str) -> list[AdapterDefinition]:
        return [adapter for adapter in self.all() if adapter.category == category]

    def active_adapter(self) -> str:
        enabled = [adapter.name for adapter in self.all() if adapter.enabled]
        return ", ".join(enabled) if enabled else "None"

    def api_status(self) -> str:
        if any(adapter.enabled for adapter in self.all()):
            return "manual approval required"
        return "disabled"

    def assert_disabled(self, adapter_id: str) -> None:
        adapter = next((item for item in self.all() if item.adapter_id == adapter_id), None)
        if adapter is None:
            raise ValueError(f"Unknown adapter: {adapter_id}")
        if adapter.enabled:
            raise RuntimeError(f"Adapter requires explicit approval before execution: {adapter_id}")

    def _build(self, category: str, adapter_ids: list[str]) -> list[AdapterDefinition]:
        category_state = self.state.get(category, {}) if isinstance(self.state, dict) else {}
        adapters = []
        for adapter_id in adapter_ids:
            item_state = category_state.get(adapter_id, {}) if isinstance(category_state, dict) else {}
            enabled = bool(item_state.get("enabled", False))
            configured = bool(item_state.get("configured", False))
            adapters.append(
                AdapterDefinition(
                    adapter_id=adapter_id,
                    name=_label(adapter_id),
                    category=category,
                    enabled=enabled,
                    configured=configured,
                    api_status="disabled" if not enabled else "approval_required",
                )
            )
        return adapters


def default_adapter_state() -> dict[str, Any]:
    return {
        "publishing": {adapter_id: {"enabled": False, "configured": False} for adapter_id in PUBLISHING_ADAPTERS},
        "affiliate": {adapter_id: {"enabled": False, "configured": False} for adapter_id in AFFILIATE_ADAPTERS},
        "seo": {adapter_id: {"enabled": False, "configured": False} for adapter_id in SEO_PROVIDERS},
    }


def _label(adapter_id: str) -> str:
    labels = {
        "note": "note",
        "x": "X",
        "threads": "Threads",
        "instagram": "Instagram",
        "wordpress": "WordPress",
        "blogger": "Blogger",
        "medium": "Medium",
        "amazon": "Amazon",
        "a8": "A8",
        "rakuten": "Rakuten",
        "valuecommerce": "ValueCommerce",
        "linkshare": "LinkShare",
        "google_search_console": "Google Search Console",
        "google_analytics": "Google Analytics",
        "manual_csv": "Manual CSV",
    }
    return labels.get(adapter_id, adapter_id)
