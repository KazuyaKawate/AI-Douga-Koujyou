from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Optional


@dataclass
class SchedulerConfig:
    """スケジューラー設定。認証情報は含まない。"""

    poll_interval_sec: int  = 60    # IntervalTrigger に渡すデフォルト間隔
    enabled:           bool = True
    max_iterations:    Optional[int] = None  # テスト・手動用。None = 無限

    @classmethod
    def from_file(cls, path: Path = Path("config/scheduler_config.json")) -> "SchedulerConfig":
        """設定ファイルを読み込む。存在しない場合はデフォルト値を使う。"""
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                poll_interval_sec=int(data.get("poll_interval_sec", 60)),
                enabled=bool(data.get("enabled", True)),
                max_iterations=data.get("max_iterations"),  # None 許容
            )
        except Exception:
            return cls()


@dataclass
class SchedulerStatus:
    """
    スケジューラーのランタイム状態。

    data/scheduler_status.json に書き出され、
    Dashboard が別プロセスからも読み取れる。

    フィールドは全て JSON シリアライズ可能な型（str / int / bool / None）のみ。
    datetime は ISO8601 文字列として保持する。
    """

    # ---- スケジューラー状態 ----------------------------------------
    running:      bool        = False
    trigger_name: str         = ""
    started_at:   Optional[str] = None   # スケジューラー起動日時 (ISO8601)

    # ---- 実行統計 --------------------------------------------------
    iteration_count:       int = 0   # tick の総実行回数
    tasks_processed_today: int = 0   # 今日の処理タスク数

    # ---- 最終実行の詳細 -------------------------------------------
    last_started_at:  Optional[str] = None  # 最終 tick 開始時刻 (ISO8601)
    last_ended_at:    Optional[str] = None  # 最終 tick 終了時刻 / 最終実行日時 (ISO8601)
    last_duration_ms: int           = 0     # 最終 tick 実行時間 (ms)
    last_success:     bool          = True  # 最終 tick 成否

    # ---- 次回実行 -------------------------------------------------
    next_scheduled_at: Optional[str] = None  # 次回実行予定 (ISO8601)

    # ---- エラー ---------------------------------------------------
    last_error: Optional[str] = None

    # ---- シリアライズ -------------------------------------------

    def to_dict(self) -> dict:
        """JSON 書き出し用の dict を返す。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SchedulerStatus":
        """dict から復元する。未知キーは無視する。"""
        valid = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})
