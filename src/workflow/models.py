from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .enums import OnFailure, StepState, StepType, WorkflowState


# ---------------------------------------------------------------------------
# WorkflowStep  —  定義内の1ステップの設定
# ---------------------------------------------------------------------------

@dataclass
class WorkflowStep:
    """
    WorkflowDefinition 内の1ステップの静的設定。

    実行時の状態は StepStatus が保持する。
    depends_on に記載された step_id がすべて COMPLETED になるまで実行されない。
    """

    step_id:         str
    step_type:       StepType
    name:            str                = ""
    depends_on:      list[str]          = field(default_factory=list)
    config:          dict               = field(default_factory=dict)
    retry_max:       int                = 0      # リトライ最大回数（0 = リトライなし）
    retry_delay_sec: float              = 1.0    # リトライ間隔（秒）
    timeout_sec:     Optional[int]      = None   # タイムアウト（将来実装）
    on_failure:      OnFailure          = OnFailure.ABORT

    def to_dict(self) -> dict:
        return {
            "step_id":         self.step_id,
            "step_type":       self.step_type.value,
            "name":            self.name,
            "depends_on":      list(self.depends_on),
            "config":          dict(self.config),
            "retry_max":       self.retry_max,
            "retry_delay_sec": self.retry_delay_sec,
            "timeout_sec":     self.timeout_sec,
            "on_failure":      self.on_failure.value,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowStep":
        return cls(
            step_id=d["step_id"],
            step_type=StepType(d.get("step_type", "ai_task")),
            name=d.get("name", d["step_id"]),
            depends_on=list(d.get("depends_on", [])),
            config=dict(d.get("config", {})),
            retry_max=int(d.get("retry_max", 0)),
            retry_delay_sec=float(d.get("retry_delay_sec", 1.0)),
            timeout_sec=d.get("timeout_sec"),
            on_failure=OnFailure(d.get("on_failure", "abort")),
        )


# ---------------------------------------------------------------------------
# WorkflowDefinition  —  ワークフローの静的テンプレート
# ---------------------------------------------------------------------------

@dataclass
class WorkflowDefinition:
    """
    ワークフローの静的テンプレート（クラスに相当）。

    config/workflow_definitions/*.json に保存する。
    WorkflowRunner.run(definition) に渡して実行する。
    """

    name:        str
    description: str               = ""
    version:     str               = "1.0.0"
    steps:       list[WorkflowStep] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name":        self.name,
            "description": self.description,
            "version":     self.version,
            "steps":       [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowDefinition":
        return cls(
            name=d.get("name", "unnamed"),
            description=d.get("description", ""),
            version=d.get("version", "1.0.0"),
            steps=[WorkflowStep.from_dict(s) for s in d.get("steps", [])],
        )

    @classmethod
    def from_file(cls, path: Path) -> "WorkflowDefinition":
        """JSON ファイルから WorkflowDefinition を読み込む。"""
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# StepStatus  —  ステップのランタイム状態
# ---------------------------------------------------------------------------

@dataclass
class StepStatus:
    """1ステップの実行時状態。WorkflowStatus.steps に格納される。"""

    step_id:       str
    state:         StepState         = StepState.PENDING
    attempt_count: int                = 0
    started_at:    Optional[str]     = None   # ISO8601
    ended_at:      Optional[str]     = None   # ISO8601
    duration_ms:   int               = 0
    output:        Optional[dict]    = None   # Executor の出力。次ステップが context 経由で参照できる
    last_error:    Optional[str]     = None

    def to_dict(self) -> dict:
        return {
            "step_id":       self.step_id,
            "state":         self.state.value,
            "attempt_count": self.attempt_count,
            "started_at":    self.started_at,
            "ended_at":      self.ended_at,
            "duration_ms":   self.duration_ms,
            "output":        self.output,
            "last_error":    self.last_error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StepStatus":
        return cls(
            step_id=d.get("step_id", ""),
            state=StepState(d.get("state", "pending")),
            attempt_count=int(d.get("attempt_count", 0)),
            started_at=d.get("started_at"),
            ended_at=d.get("ended_at"),
            duration_ms=int(d.get("duration_ms", 0)),
            output=d.get("output"),
            last_error=d.get("last_error"),
        )


# ---------------------------------------------------------------------------
# WorkflowStatus  —  ワークフロー実行インスタンスの全状態
# ---------------------------------------------------------------------------

@dataclass
class WorkflowStatus:
    """
    WorkflowDefinition の1実行インスタンスの状態。

    data/workflows/{workflow_id}.json に永続化され、
    Dashboard や外部プロセスから読み取れる。

    context は steps 間でデータを受け渡すための dict。
    例: InboxPollExecutor が context["polled_count"] = 3 をセット
        → AITaskExecutor が prompt の {polled_count} に埋め込む
    """

    workflow_id:      str                   = field(default_factory=lambda: str(uuid.uuid4()))
    definition_name:  str                   = ""
    state:            WorkflowState         = WorkflowState.PENDING
    steps:            dict[str, StepStatus] = field(default_factory=dict)
    context:          dict                  = field(default_factory=dict)
    created_at:       str                   = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    started_at:       Optional[str]         = None
    ended_at:         Optional[str]         = None
    duration_ms:      int                   = 0
    error:            Optional[str]         = None

    def to_dict(self) -> dict:
        return {
            "workflow_id":     self.workflow_id,
            "definition_name": self.definition_name,
            "state":           self.state.value,
            "steps":           {sid: ss.to_dict() for sid, ss in self.steps.items()},
            "context":         self.context,
            "created_at":      self.created_at,
            "started_at":      self.started_at,
            "ended_at":        self.ended_at,
            "duration_ms":     self.duration_ms,
            "error":           self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowStatus":
        steps = {
            sid: StepStatus.from_dict(ss_data)
            for sid, ss_data in d.get("steps", {}).items()
        }
        return cls(
            workflow_id=d.get("workflow_id", str(uuid.uuid4())),
            definition_name=d.get("definition_name", ""),
            state=WorkflowState(d.get("state", "pending")),
            steps=steps,
            context=dict(d.get("context", {})),
            created_at=d.get("created_at", ""),
            started_at=d.get("started_at"),
            ended_at=d.get("ended_at"),
            duration_ms=int(d.get("duration_ms", 0)),
            error=d.get("error"),
        )
