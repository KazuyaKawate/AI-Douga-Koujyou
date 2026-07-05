from __future__ import annotations
import json
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .models import SchedulerConfig, SchedulerStatus
from .triggers.base import BaseTrigger

from src.utils.json_store import save_json_atomic
if TYPE_CHECKING:
    from src.inbox.poller import InboxPoller
    from src.inbox.runner import TaskRunner

_STATUS_PATH  = Path("data/scheduler_status.json")
_CONTROL_PATH = Path("data/scheduler_control.json")
_LOOP_TICK_SEC = 1.0   # ループ内ポーリング間隔。制御ファイルの検知速度に影響


class FactoryScheduler:
    """
    InboxPoller と TaskRunner を定期的に実行するスケジューラー。

    Trigger と Router に依存しない設計:
        - 「いつ発火するか」は BaseTrigger サブクラスに委譲
        - AIRouter は TaskRunner に注入済み。Scheduler は直接参照しない
        - バックグラウンドスレッドで動作し、stop() でグレースフルシャットダウン

    Dashboard との連携:
        - _flush_status() が data/scheduler_status.json を書き出す
        - Dashboard は別プロセスからこのファイルを読む (DashboardCollector)
        - stop/start 命令は data/scheduler_control.json 経由 (_read_control)

    使い方:
        config  = SchedulerConfig.from_file()
        trigger = IntervalTrigger(interval_sec=config.poll_interval_sec)
        sched   = FactoryScheduler(poller=poller, runner=runner,
                                   trigger=trigger, config=config)
        sched.start()
        ...
        sched.stop()
    """

    def __init__(
        self,
        poller: "InboxPoller",
        runner: "TaskRunner",
        trigger: BaseTrigger,
        config: SchedulerConfig,
        status_path:  Path = _STATUS_PATH,
        control_path: Path = _CONTROL_PATH,
    ) -> None:
        self._poller       = poller
        self._runner       = runner
        self._trigger      = trigger
        self._config       = config
        self._status_path  = status_path
        self._control_path = control_path
        self._status       = SchedulerStatus(trigger_name=trigger.trigger_name)
        self._thread: threading.Thread | None = None
        self._stop_event   = threading.Event()

    # ---- Public API --------------------------------------------------

    def start(self) -> None:
        """バックグラウンドスレッドでスケジューラーを起動する。二重起動は無視する。"""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="FactoryScheduler")
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        """グレースフルシャットダウン。実行中の tick が終わるまで待つ。"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def run_once(self) -> int:
        """
        トリガーに関係なく _tick() を1回実行する。手動実行・テスト用。

        バックグラウンドスレッドを起動せず、呼び出し元のスレッドで同期実行する。
        処理したタスク数を返す。
        """
        return self._tick()

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def get_status(self) -> SchedulerStatus:
        return self._status

    # ---- Private: ループ -------------------------------------------

    def _loop(self) -> None:
        """バックグラウンドスレッドのメインループ。"""
        self._status.running    = True
        self._status.started_at = datetime.now().isoformat(timespec="seconds")
        nf = self._trigger.next_fire_at()
        self._status.next_scheduled_at = nf.isoformat(timespec="seconds") if nf else None
        self._flush_status()

        iterations = 0
        while not self._stop_event.is_set():

            # 制御ファイルチェック（Dashboard からの stop 命令）
            if self._read_control() == "stop":
                break

            if self._trigger.should_fire():
                self._tick()
                self._trigger.on_fired()
                iterations += 1

                # 次回実行予定を更新
                nf = self._trigger.next_fire_at()
                self._status.next_scheduled_at = (
                    nf.isoformat(timespec="seconds") if nf else None
                )
                self._flush_status()

                # max_iterations チェック（テスト・手動実行用）
                if (self._config.max_iterations is not None
                        and iterations >= self._config.max_iterations):
                    break

            # 短いスリープ（busy-wait 回避 + 制御ファイル検知速度の確保）
            self._stop_event.wait(timeout=_LOOP_TICK_SEC)

        self._status.running           = False
        self._status.next_scheduled_at = None
        self._flush_status()

    # ---- Private: 1 tick -------------------------------------------

    def _tick(self) -> int:
        """
        1インターバルの処理: poll → run loop → mark done/error。

        処理件数を返す。成功・失敗どちらでも SchedulerStatus を更新する。
        """
        t0             = time.monotonic()
        started_at_str = datetime.now().isoformat(timespec="seconds")
        self._status.last_started_at = started_at_str

        count   = 0
        success = True

        try:
            self._poller.poll_once()

            # キューが空になるまで処理
            while True:
                result = self._runner.run_once()
                if result is None:
                    break
                entry, resp = result
                if resp.ok:
                    self._poller.mark_done(entry.id)
                else:
                    self._poller.mark_error(entry.id, resp.error or "unknown error")
                count += 1

        except Exception as exc:
            success = False
            self._status.last_error = str(exc)

        duration_ms    = int((time.monotonic() - t0) * 1000)
        ended_at_str   = datetime.now().isoformat(timespec="seconds")

        self._status.last_ended_at          = ended_at_str
        self._status.last_duration_ms       = duration_ms
        self._status.last_success           = success
        self._status.iteration_count       += 1
        self._status.tasks_processed_today += count

        self._flush_status()
        return count

    # ---- Private: ファイル I/O -------------------------------------

    def _flush_status(self) -> None:
        """SchedulerStatus を data/scheduler_status.json に書き出す。例外は握りつぶす。"""
        try:
            self._status_path.parent.mkdir(parents=True, exist_ok=True)
            save_json_atomic(self._status_path, self._status.to_dict())
        except Exception:
            pass

    def _read_control(self) -> str | None:
        """
        data/scheduler_control.json から命令を読む。

        ファイルが存在しない・読めない場合は None を返す。
        命令を読んだ後はファイルを削除して再実行を防ぐ。
        """
        try:
            if not self._control_path.exists():
                return None
            data    = json.loads(self._control_path.read_text(encoding="utf-8"))
            command = data.get("command")
            self._control_path.unlink(missing_ok=True)
            return str(command) if command else None
        except Exception:
            return None
