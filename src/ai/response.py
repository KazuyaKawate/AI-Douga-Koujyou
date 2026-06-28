from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class AIResponse:
    ok: bool
    content: str
    provider: str
    model: str
    task_type: str
    duration_ms: int
    error: str | None = None
    metadata: dict | None = field(default=None)


@dataclass
class ProviderHealth:
    name: str
    available: bool
    api_key_configured: bool
    capabilities: list[str]
    model: str
    enabled: bool
    error: str | None = None
