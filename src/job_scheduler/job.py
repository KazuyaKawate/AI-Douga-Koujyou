"""ScheduledJob — Workflow を時間・イベント起動するジョブ定義。"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TriggerType(str, Enum):
    ONCE    = "once"      # 指定日時に1回だけ実行
    DAILY   = "daily"     # 毎日 HH:MM に実行
    WEEKLY  = "weekly"    # 毎週 weekday の HH:MM に実行
    INTERVAL= "interval"  # N 分ごとに実行
    WEBHOOK = "webhook"   # 外部から POST で起動
    MANUAL  = "manual"    # 手動実行のみ

class JobStatus(str, Enum):
    ACTIVE   = "active"
    PAUSED   = "paused"
    FINISHED = "finished"
    FAILED   = "failed"


@dataclass
class TriggerConfig:
    """トリガー種別ごとの設定。"""
    type:           TriggerType
    run_at:         Optional[str] = None   # "HH:MM" (daily/weekly/once)
    weekday:        Optional[int] = None   # 0=月 〜 6=日 (weekly)
    interval_min:   Optional[int] = None   # 分 (interval)
    run_once_at:    Optional[str] = None   # ISO8601 (once)
    webhook_token:  Optional[str] = None   # (webhook)

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict) -> "TriggerConfig":
        return cls(
            type         = TriggerType(d.get("type", "manual")),
            run_at       = d.get("run_at"),
            weekday      = d.get("weekday"),
            interval_min = d.get("interval_min"),
            run_once_at  = d.get("run_once_at"),
            webhook_token= d.get("webhook_token"),
        )


@dataclass
class JobRunRecord:
    """ジョブの1回の実行記録。"""
    started_at:  str
    ended_at:    str    = ""
    success:     bool   = True
    duration_ms: int    = 0
    error:       Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "JobRunRecord":
        return cls(**{k: v for k, v in d.items() if k in ("started_at","ended_at","success","duration_ms","error")})


@dataclass
class ScheduledJob:
    """
    スケジュール済みジョブ。

    workflow_name  : 実行する WorkflowDefinition の name
    context        : ワークフローに渡す初期コンテキスト
    trigger        : いつ起動するか
    """
    job_id:        str
    name:          str
    workflow_name: str
    context:       dict              = field(default_factory=dict)
    trigger:       TriggerConfig     = field(default_factory=lambda: TriggerConfig(TriggerType.MANUAL))
    status:        JobStatus         = JobStatus.ACTIVE
    created_at:    str               = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    updated_at:    str               = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    next_run_at:   Optional[str]     = None
    last_run_at:   Optional[str]     = None
    run_count:     int               = 0
    run_history:   list[JobRunRecord]= field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "job_id":        self.job_id,
            "name":          self.name,
            "workflow_name": self.workflow_name,
            "context":       self.context,
            "trigger":       self.trigger.to_dict(),
            "status":        self.status.value,
            "created_at":    self.created_at,
            "updated_at":    self.updated_at,
            "next_run_at":   self.next_run_at,
            "last_run_at":   self.last_run_at,
            "run_count":     self.run_count,
            "run_history":   [r.to_dict() for r in self.run_history[-20:]],
        }
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "ScheduledJob":
        return cls(
            job_id        = d["job_id"],
            name          = d.get("name", d["job_id"]),
            workflow_name = d["workflow_name"],
            context       = dict(d.get("context", {})),
            trigger       = TriggerConfig.from_dict(d.get("trigger", {"type": "manual"})),
            status        = JobStatus(d.get("status", "active")),
            created_at    = d.get("created_at", ""),
            updated_at    = d.get("updated_at", ""),
            next_run_at   = d.get("next_run_at"),
            last_run_at   = d.get("last_run_at"),
            run_count     = int(d.get("run_count", 0)),
            run_history   = [JobRunRecord.from_dict(r) for r in d.get("run_history", [])],
        )
