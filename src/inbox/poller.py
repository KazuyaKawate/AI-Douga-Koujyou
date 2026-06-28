from __future__ import annotations

from .models import InboxConfig
from .queue import TaskQueue
from .sources.base import BaseInboxSource


class InboxPoller:
    """
    Source をポーリングし、新着エントリを TaskQueue に投入する。

    Source と Queue をつなぐ中継役。TaskRunner とは独立している。

    使い方（呼び出し元がフローを制御する）:
        poller = InboxPoller(source=GoogleSheetsInboxSource(cfg), queue=queue, config=cfg)
        runner = TaskRunner(router=router, queue=queue, ...)

        # ポーリング
        n = poller.poll_once()

        # 処理
        result = runner.run_once()
        if result:
            entry, resp = result
            if resp.ok:
                poller.mark_done(entry.id)
            else:
                poller.mark_error(entry.id, resp.error or "unknown error")
    """

    def __init__(
        self,
        source: BaseInboxSource,
        queue: TaskQueue,
        config: InboxConfig,
    ) -> None:
        self._source = source
        self._queue  = queue
        self._config = config

    # ---- Public API --------------------------------------------------

    def poll_once(self) -> int:
        """
        Source から pending エントリを取得し、Queue に投入する。

        - Source が利用不可なら 0 を返す
        - 各エントリを mark_processing() した後に queue.put() する
        - 投入件数を返す
        """
        if not self._source.is_available():
            return 0

        entries = self._source.fetch_pending(self._config.max_batch)
        for entry in entries:
            # source_name を確実に設定
            entry.source_name = self._source.source_name
            self._source.mark_processing(entry.id)
            self._queue.put(entry)

        return len(entries)

    def mark_done(self, entry_id: str) -> None:
        """TaskRunner が正常完了後に呼ぶ。Source の status を "done" に更新する。"""
        self._source.mark_done(entry_id)

    def mark_error(self, entry_id: str, message: str) -> None:
        """TaskRunner がエラー時に呼ぶ。Source の status を "error" に更新する。"""
        self._source.mark_error(entry_id, message)

    @property
    def source_name(self) -> str:
        return self._source.source_name
