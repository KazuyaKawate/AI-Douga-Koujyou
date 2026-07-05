"""ExecutionTracker — Workflow 実行ログを JSONL に追記する。

Kernel / Router 無変更で動作する。
GUI または Workflow 呼び出しコードから track() を呼ぶだけで記録される。
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

_LOG_PATH = Path("data/intelligence/executions.jsonl")
_lock     = threading.Lock()


@dataclass
class ExecutionRecord:
    """1回の Workflow/Agent 実行ログエントリ。"""
    record_id:     str
    workflow_name: str
    factory_id:    str          = ""
    agent_ids:     list[str]    = field(default_factory=list)
    success:       bool         = True
    duration_ms:   int          = 0
    output_chars:  int          = 0
    error:         Optional[str]= None
    context:       dict         = field(default_factory=dict)
    timestamp:     str          = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ExecutionRecord":
        return cls(
            record_id    = d.get("record_id", ""),
            workflow_name= d.get("workflow_name", ""),
            factory_id   = d.get("factory_id", ""),
            agent_ids    = list(d.get("agent_ids", [])),
            success      = bool(d.get("success", True)),
            duration_ms  = int(d.get("duration_ms", 0)),
            output_chars = int(d.get("output_chars", 0)),
            error        = d.get("error"),
            context      = dict(d.get("context", {})),
            timestamp    = d.get("timestamp", ""),
        )


class ExecutionTracker:
    """
    実行ログを data/intelligence/executions.jsonl に追記するトラッカー。

    スレッドセーフ・ファイルロック付き。

    使い方:
        tracker = ExecutionTracker()
        t0 = time.monotonic()
        # ... workflow実行 ...
        tracker.record(
            workflow_name="social.x_post",
            factory_id="social",
            success=True,
            duration_ms=int((time.monotonic() - t0) * 1000),
            output_chars=len(result_text),
        )
    """

    def __init__(self, log_path: Path = _LOG_PATH) -> None:
        self._path = log_path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        workflow_name: str,
        factory_id:    str            = "",
        agent_ids:     list[str]      = None,
        success:       bool           = True,
        duration_ms:   int            = 0,
        output_chars:  int            = 0,
        error:         Optional[str]  = None,
        context:       dict           = None,
    ) -> ExecutionRecord:
        """実行記録を JSONL に追記する。"""
        import uuid
        rec = ExecutionRecord(
            record_id    = str(uuid.uuid4())[:8],
            workflow_name= workflow_name,
            factory_id   = factory_id or workflow_name.split(".")[0],
            agent_ids    = list(agent_ids or []),
            success      = success,
            duration_ms  = duration_ms,
            output_chars = output_chars,
            error        = error,
            context      = dict(context or {}),
        )
        with _lock:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
        return rec

    def load_all(self, limit: int = 0) -> list[ExecutionRecord]:
        """全ログを読み込む。limit=0 で全件。"""
        if not self._path.exists():
            return []
        records: list[ExecutionRecord] = []
        with _lock:
            lines = self._path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(ExecutionRecord.from_dict(json.loads(line)))
            except Exception:
                continue
        if limit > 0:
            records = records[-limit:]
        return records

    def load_recent(self, n: int = 20) -> list[ExecutionRecord]:
        """最新 n 件を返す（新しい順）。"""
        return list(reversed(self.load_all(limit=n)))

    def clear(self) -> None:
        """ログをリセットする（テスト用）。"""
        with _lock:
            self._path.write_text("", encoding="utf-8")


_tracker_instance: Optional[ExecutionTracker] = None

def get_tracker() -> ExecutionTracker:
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = ExecutionTracker()
    return _tracker_instance
