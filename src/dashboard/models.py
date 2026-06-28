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
class SchedulerStats:
    """Dashboard 表示用スケジューラー統計。data/scheduler_status.json から読む。"""

    running:               bool          = False
    trigger_name:          str           = "---"
    iteration_count:       int           = 0
    tasks_processed_today: int           = 0
    last_started_at:       Optional[str] = None  # 最終 tick 開始時刻
    last_ended_at:         Optional[str] = None  # 最終 tick 終了時刻 / 最終実行日時
    last_duration_ms:      int           = 0     # 最終 tick 実行時間 (ms)
    last_success:          bool          = True  # 最終 tick 成否
    next_scheduled_at:     Optional[str] = None  # 次回実行予定
    last_error:            Optional[str] = None


@dataclass
class WorkflowStats:
    """Dashboard 表示用ワークフロー統計。data/workflows/ ディレクトリから読む。"""

    total_count:      int           = 0
    running_count:    int           = 0
    completed_today:  int           = 0
    failed_count:     int           = 0
    last_definition:  str           = "---"
    last_ended_at:    Optional[str] = None
    last_success:     bool          = True


@dataclass
class OrchestratorStats:
    """Dashboard 表示用 Orchestrator 統計。data/orchestrator_status.json から読む。"""

    running:               bool          = False
    active_workflow_count: int           = 0
    pending_job_count:     int           = 0
    completed_today:       int           = 0
    failed_count:          int           = 0
    total_jobs:            int           = 0
    avg_duration_ms:       float         = 0.0
    last_event:            Optional[str] = None
    last_event_at:         Optional[str] = None
    cpu_usage_pct:         float         = 0.0   # スタブ
    memory_usage_mb:       float         = 0.0   # スタブ


@dataclass
class NoteFactoryStats:
    """Dashboard 表示用 Note Factory 統計。data/note_stats.json から読む。"""

    articles_today:        int   = 0
    articles_this_month:   int   = 0
    waiting_publish:       int   = 0
    waiting_approval:      int   = 0
    published_total:       int   = 0
    total_word_count:      int   = 0
    avg_word_count:        float = 0.0
    estimated_revenue_jpy: int   = 0


@dataclass
class DashboardData:
    collected_at:  datetime              = field(default_factory=datetime.now)
    git:           GitStatus             = field(default_factory=GitStatus)
    providers:     list[ProviderStatus]  = field(default_factory=list)
    api_keys:      ApiKeyStatus          = field(default_factory=ApiKeyStatus)
    usage_today:   UsageStats            = field(default_factory=UsageStats)
    infra:         InfraStatus           = field(default_factory=InfraStatus)
    task_queue:    TaskQueueStats        = field(default_factory=TaskQueueStats)
    scheduler:     SchedulerStats        = field(default_factory=SchedulerStats)
    workflow:      WorkflowStats         = field(default_factory=WorkflowStats)
    orchestrator:  OrchestratorStats     = field(default_factory=OrchestratorStats)
    note_factory:  NoteFactoryStats      = field(default_factory=NoteFactoryStats)
    recent_errors: list[ErrorEntry]      = field(default_factory=list)
