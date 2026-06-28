from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class InboxEntry:
    """Inbox の 1 メッセージ。どの Source 由来かに関わらず共通の型。"""

    id:          str      = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:  datetime = field(default_factory=datetime.now)
    source_name: str      = ""           # BaseInboxSource.source_name に対応
    task_type:   str      = "default"    # TaskType.value
    prompt:      str      = ""
    status:      str      = "pending"    # pending → processing → done / error
    priority:    int      = 3            # 0=低 .. 5=高


@dataclass
class OutboxEntry:
    """AIResponse から生成するレスポンスレコード。Source の Outbox に書き戻す。"""

    inbox_id:     str               = ""
    completed_at: datetime          = field(default_factory=datetime.now)
    provider:     str               = ""
    model:        str               = ""
    response:     str               = ""
    input_tokens: int | None        = None
    output_tokens: int | None       = None
    cost_usd:     float | None      = None
    error:        str | None        = None


@dataclass
class InboxConfig:
    """Inbox 全体の設定。認証情報・ID は含まない。"""

    inbox_sheet:       str  = "Factory_Inbox"
    outbox_sheet:      str  = "Factory_Outbox"
    poll_interval_sec: int  = 60
    max_batch:         int  = 5
    allow_write:       bool = False   # False = dry-run（コミット済みコードはFalse固定）
    task_type_default: str  = "default"

    @classmethod
    def from_file(cls, path: Path = Path("config/inbox_config.json")) -> "InboxConfig":
        """設定ファイルを読み込む。存在しない場合はデフォルト値を使う。"""
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(
                inbox_sheet=data.get("inbox_sheet", "Factory_Inbox"),
                outbox_sheet=data.get("outbox_sheet", "Factory_Outbox"),
                poll_interval_sec=int(data.get("poll_interval_sec", 60)),
                max_batch=int(data.get("max_batch", 5)),
                allow_write=bool(data.get("allow_write", False)),
                task_type_default=data.get("task_type_default", "default"),
            )
        except Exception:
            return cls()
