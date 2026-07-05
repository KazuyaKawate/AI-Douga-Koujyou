from __future__ import annotations
from enum import Enum


class WorkflowState(str, Enum):
    """ワークフロー実行インスタンス全体の状態。"""
    PENDING          = "pending"
    RUNNING          = "running"
    PAUSED           = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED        = "completed"
    FAILED           = "failed"
    CANCELLED        = "cancelled"


class StepState(str, Enum):
    """個別ステップのランタイム状態。"""
    PENDING          = "pending"
    RUNNING          = "running"
    COMPLETED        = "completed"
    FAILED           = "failed"
    SKIPPED          = "skipped"
    WAITING_APPROVAL = "waiting_approval"
    RETRYING         = "retrying"


class StepType(str, Enum):
    """ステップ種別。EXECUTOR_REGISTRY のキーと一致させる。"""
    AI_TASK          = "ai_task"
    MEMORY_UPDATE    = "memory_update"
    SNAPSHOT         = "snapshot"
    HUMAN_APPROVAL   = "human_approval"
    INBOX_POLL       = "inbox_poll"
    QUEUE_PUSH       = "queue_push"
    CONDITION        = "condition"      # スタブ（将来実装）
    NOTIFICATION     = "notification"   # スタブ（将来実装）
    FILE_SAVE        = "file_save"      # ファイル保存
    FILE_READ        = "file_read"      # ファイル読み込み（読み取り専用）
    DIFF_OUTPUT      = "diff_output"    # unified diff 生成・保存
    # Note Factory 専用ステップ
    NOTE_IDEA        = "note_idea"
    NOTE_PLAN        = "note_plan"
    NOTE_WRITE       = "note_write"
    NOTE_REVIEW      = "note_review"
    NOTE_PUBLISH     = "note_publish"
    NOTE_ANALYZE     = "note_analyze"
    NOTE_MEMORY      = "note_memory"


class OnFailure(str, Enum):
    """ステップ失敗時のワークフロー挙動。"""
    ABORT    = "abort"     # ワークフロー全体を失敗で終了（デフォルト）
    SKIP     = "skip"      # このステップをスキップして次へ
    CONTINUE = "continue"  # 失敗を記録して次へ（SKIP と同等）
