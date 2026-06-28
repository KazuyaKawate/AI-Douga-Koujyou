from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class GitStatus:
    branch: str = ""
    latest_hash: str = ""
    latest_message: str = ""
    unpushed_count: int = 0
    error: Optional[str] = None


@dataclass
class ProviderStatus:
    name: str = ""
    enabled: bool = False
    has_api_key: bool = False
    model: str = ""


@dataclass
class ApiKeyStatus:
    configured_count: int = 0
    total_count: int = 0


@dataclass
class UsageStats:
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    request_count: int = 0


@dataclass
class SnapshotStatus:
    exists: bool = False
    created_at: Optional[str] = None
    schema_version: Optional[str] = None
    error: Optional[str] = None


@dataclass
class InfraStatus:
    logger_type: str = "NullLogger"
    sheets_connected: bool = False
    memory_count: int = 0
    snapshot: SnapshotStatus = field(default_factory=SnapshotStatus)


@dataclass
class TaskQueueStats:
    pending: int = 0
    running: int = 0
    completed_today: int = 0


@dataclass
class ErrorEntry:
    timestamp: str = ""
    provider: str = ""
    message: str = ""


@dataclass
class DashboardData:
    collected_at: datetime = field(default_factory=datetime.now)
    git: GitStatus = field(default_factory=GitStatus)
    providers: list[ProviderStatus] = field(default_factory=list)
    api_keys: ApiKeyStatus = field(default_factory=ApiKeyStatus)
    usage_today: UsageStats = field(default_factory=UsageStats)
    infra: InfraStatus = field(default_factory=InfraStatus)
    task_queue: TaskQueueStats = field(default_factory=TaskQueueStats)
    recent_errors: list[ErrorEntry] = field(default_factory=list)
