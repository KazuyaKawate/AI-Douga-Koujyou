from __future__ import annotations
import json
import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class JobStatus(str, Enum):
    """WorkflowJob のライフサイクル状態。"""
    PENDING   = "pending"    # キュー待機中
    RUNNING   = "running"    # 実行中
    PAUSED    = "paused"     # 一時停止中
    COMPLETED = "completed"  # 正常完了
    FAILED    = "failed"     # 失敗（リトライ上限超過）
    CANCELLED = "cancelled"  # キャンセル済み


@dataclass
class WorkflowJob:
    """
    Orchestrator が管理する1ジョブの定義・実行状態。

    definition_name: FactoryRegistry に登録された WorkflowDefinition の名前
    priority:        1=低 / 10=高。同一優先度は作成順（created_at）で処理
    depends_on:      完了を待つ他ジョブの job_id リスト
    retry_after:     ISO8601。この時刻以降にのみリトライを開始する
    """

    job_id:           str           = field(default_factory=lambda: str(uuid.uuid4()))
    definition_name:  str           = ""
    priority:         int           = 5
    status:           JobStatus     = JobStatus.PENDING
    workflow_id:      Optional[str] = None   # run_async() が返す WorkflowStatus.workflow_id
    created_at:       str           = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    started_at:       Optional[str] = None
    ended_at:         Optional[str] = None
    duration_ms:      int           = 0
    attempt_count:    int           = 0
    retry_max:        int           = 0
    retry_delay_sec:  float         = 5.0
    retry_after:      Optional[str] = None   # ISO8601: この時刻以降に再実行
    error:            Optional[str] = None
    context:          dict          = field(default_factory=dict)
    depends_on:       list[str]     = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowJob":
        valid = {f.name for f in fields(cls)}
        kw    = {k: v for k, v in d.items() if k in valid}
        if "status" in kw:
            kw["status"] = JobStatus(kw["status"])
        return cls(**kw)


@dataclass
class OrchestratorConfig:
    """Orchestrator 設定。認証情報は含まない。"""

    max_concurrent_workflows: int   = 3
    retry_max:                int   = 0
    retry_delay_sec:          float = 5.0
    enabled:                  bool  = True

    @classmethod
    def from_file(
        cls,
        path: Path = Path("config/orchestrator_config.json"),
    ) -> "OrchestratorConfig":
        if not Path(path).exists():
            return cls()
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            return cls(
                max_concurrent_workflows=int(data.get("max_concurrent_workflows", 3)),
                retry_max=int(data.get("retry_max", 0)),
                retry_delay_sec=float(data.get("retry_delay_sec", 5.0)),
                enabled=bool(data.get("enabled", True)),
            )
        except Exception:
            return cls()


@dataclass
class OrchestratorStatus:
    """
    Orchestrator のランタイム状態サマリー。

    data/orchestrator_status.json に書き出され、
    Dashboard が別プロセスから読み取れる。
    cpu_usage_pct / memory_usage_mb は現フェーズではスタブ（常に 0.0）。
    """

    running:               bool          = False
    active_workflow_count: int           = 0
    pending_job_count:     int           = 0
    completed_today:       int           = 0
    failed_count:          int           = 0
    total_jobs:            int           = 0
    avg_duration_ms:       float         = 0.0
    last_event:            Optional[str] = None
    last_event_at:         Optional[str] = None
    started_at:            Optional[str] = None
    cpu_usage_pct:         float         = 0.0   # スタブ
    memory_usage_mb:       float         = 0.0   # スタブ

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "OrchestratorStatus":
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})
