from __future__ import annotations
import json
import threading
from collections import deque
from pathlib import Path

from .models import InboxEntry

from src.utils.json_store import save_json_atomic
_STATS_PATH = Path("data/inbox_queue_stats.json")


class TaskQueue:
    """
    スレッドセーフな InboxEntry キュー。

    Source / Runner から独立した設計。
    put() / get() / complete() のたびに data/inbox_queue_stats.json を更新し、
    Dashboard が別プロセスからも統計を読み取れるようにする。
    """

    def __init__(self, stats_path: Path = _STATS_PATH) -> None:
        self._queue:           deque[InboxEntry] = deque()
        self._lock:            threading.Lock    = threading.Lock()
        self._running:         bool              = False
        self._completed_today: int               = 0
        self._stats_path:      Path              = stats_path

    # ---- Public API ---------------------------------------------------

    def put(self, entry: InboxEntry) -> None:
        """エントリをキューに追加する。"""
        with self._lock:
            self._queue.append(entry)
        self._flush_stats()

    def get(self) -> InboxEntry | None:
        """先頭のエントリを取り出す。空なら None を返す。"""
        with self._lock:
            if not self._queue:
                return None
            entry = self._queue.popleft()
            self._running = True
        self._flush_stats()
        return entry

    def complete(self) -> None:
        """処理中フラグを解除し、完了カウントをインクリメントする。"""
        with self._lock:
            self._running = False
            self._completed_today += 1
        self._flush_stats()

    def size(self) -> int:
        """現在のキューサイズ（未処理件数）を返す。"""
        with self._lock:
            return len(self._queue)

    def stats(self) -> dict:
        """Dashboard 向け統計を dict で返す。"""
        with self._lock:
            return {
                "pending":         len(self._queue),
                "running":         1 if self._running else 0,
                "completed_today": self._completed_today,
            }

    # ---- Private ------------------------------------------------------

    def _flush_stats(self) -> None:
        """統計を data/inbox_queue_stats.json に書き出す。例外は握りつぶす。"""
        try:
            self._stats_path.parent.mkdir(parents=True, exist_ok=True)
            save_json_atomic(self._stats_path, self.stats(), indent=None)
        except Exception:
            pass
