from __future__ import annotations
import inspect
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from .enums import OnFailure, StepState, WorkflowState
from .models import StepStatus, WorkflowDefinition, WorkflowStatus
from .store import WorkflowStore

if TYPE_CHECKING:
    from .models import WorkflowStep

_DEFAULT_STORE_DIR = Path("data/workflows")
_POLL_SEC = 0.25   # pause / approval 待ちのポーリング間隔（秒）


class WorkflowRunner:
    """
    WorkflowDefinition を実行するエンジン。

    設計原則:
        - Router / Inbox / Scheduler は変更しない。それぞれへの参照を DI で受け取る
        - Trigger に依存しない（Scheduler から呼ばれる場合も、run() / run_async() を直接呼ぶ）
        - step 間の状態共有は WorkflowStatus.context（dict）を使う
        - 外部プロセス（Dashboard）向けに WorkflowStore でファイル永続化する

    使い方:
        runner = WorkflowRunner(router=router, memory=memory, snapshot_builder=sb)
        status = runner.run(definition)              # 同期（テスト・手動実行向け）
        status = runner.run_async(definition)        # 非同期（Scheduler から起動向け）
        runner.pause(status.workflow_id)
        runner.resume(status.workflow_id)
        runner.approve(status.workflow_id, step_id) # Human Approval 承認
    """

    def __init__(
        self,
        router: Any | None = None,
        memory: Any | None = None,
        snapshot_builder: Any | None = None,
        poller: Any | None = None,
        queue: Any | None = None,
        store_dir: Path | None = None,
        executor_registry: dict | None = None,  # テスト・拡張用オーバーライド
    ) -> None:
        from .executors import EXECUTOR_REGISTRY

        self._deps: dict[str, Any] = {
            "router":           router,
            "memory":           memory,
            "snapshot_builder": snapshot_builder,
            "poller":           poller,
            "queue":            queue,
        }
        self._registry  = executor_registry if executor_registry is not None else EXECUTOR_REGISTRY
        self._store     = WorkflowStore(store_dir or _DEFAULT_STORE_DIR)
        self._statuses: dict[str, WorkflowStatus] = {}   # workflow_id → 実行中 status
        self._lock      = threading.Lock()

    # ---- Public API --------------------------------------------------

    def run(
        self,
        definition: WorkflowDefinition,
        context: dict | None = None,
    ) -> WorkflowStatus:
        """同期実行。ワークフロー完了まで呼び出しスレッドをブロックする。"""
        status = _new_status(definition, context)
        with self._lock:
            self._statuses[status.workflow_id] = status
        try:
            self._execute(status, definition)
        finally:
            with self._lock:
                self._statuses.pop(status.workflow_id, None)
        return status

    def run_async(
        self,
        definition: WorkflowDefinition,
        context: dict | None = None,
    ) -> WorkflowStatus:
        """
        バックグラウンドスレッドで非同期実行。即座に WorkflowStatus を返す。

        返された status オブジェクトはスレッドから直接更新される。
        完了を確認するには status.state を参照する。
        """
        status = _new_status(definition, context)
        with self._lock:
            self._statuses[status.workflow_id] = status

        def _worker() -> None:
            try:
                self._execute(status, definition)
            finally:
                with self._lock:
                    self._statuses.pop(status.workflow_id, None)

        threading.Thread(
            target=_worker,
            daemon=True,
            name=f"WF-{status.workflow_id[:8]}",
        ).start()
        return status

    def pause(self, workflow_id: str) -> bool:
        """実行中ワークフローを一時停止する。次ステップの前に停止する。"""
        with self._lock:
            s = self._statuses.get(workflow_id)
            if s and s.state == WorkflowState.RUNNING:
                s.state = WorkflowState.PAUSED
                return True
        return False

    def resume(self, workflow_id: str) -> bool:
        """一時停止中ワークフローを再開する。"""
        with self._lock:
            s = self._statuses.get(workflow_id)
            if s and s.state == WorkflowState.PAUSED:
                s.state = WorkflowState.RUNNING
                return True
        return False

    def cancel(self, workflow_id: str) -> bool:
        """実行中・一時停止中・承認待ちワークフローをキャンセルする。"""
        _cancellable = {
            WorkflowState.RUNNING,
            WorkflowState.PAUSED,
            WorkflowState.WAITING_APPROVAL,
        }
        with self._lock:
            s = self._statuses.get(workflow_id)
            if s and s.state in _cancellable:
                s.state    = WorkflowState.CANCELLED
                s.ended_at = datetime.now().isoformat(timespec="seconds")
                return True
        return False

    def approve(self, workflow_id: str, step_id: str) -> bool:
        """Human Approval ステップを承認する。"""
        with self._lock:
            s  = self._statuses.get(workflow_id)
            if not s:
                return False
            ss = s.steps.get(step_id)
            if not ss or ss.state != StepState.WAITING_APPROVAL:
                return False
            ss.state    = StepState.COMPLETED
            ss.ended_at = datetime.now().isoformat(timespec="seconds")
            if s.state == WorkflowState.WAITING_APPROVAL:
                s.state = WorkflowState.RUNNING
            return True

    def reject(self, workflow_id: str, step_id: str, reason: str = "") -> bool:
        """Human Approval ステップを却下する。"""
        with self._lock:
            s  = self._statuses.get(workflow_id)
            if not s:
                return False
            ss = s.steps.get(step_id)
            if not ss or ss.state != StepState.WAITING_APPROVAL:
                return False
            ss.state      = StepState.FAILED
            ss.last_error = reason or "却下されました"
            ss.ended_at   = datetime.now().isoformat(timespec="seconds")
            if s.state == WorkflowState.WAITING_APPROVAL:
                s.state = WorkflowState.RUNNING
            return True

    def get_status(self, workflow_id: str) -> Optional[WorkflowStatus]:
        with self._lock:
            return self._statuses.get(workflow_id)

    def list_active(self) -> list[WorkflowStatus]:
        with self._lock:
            return list(self._statuses.values())

    # ---- Private: Workflow 実行 ------------------------------------

    def _execute(self, status: WorkflowStatus, definition: WorkflowDefinition) -> None:
        """ワークフロー全体の実行ループ。status を直接変更する。"""
        t0 = time.monotonic()
        with self._lock:
            status.state      = WorkflowState.RUNNING
            status.started_at = datetime.now().isoformat(timespec="seconds")
        self._store.save(status)

        # 依存関係解決（循環・未定義があれば即 FAILED）
        try:
            ordered = _resolve_order(definition.steps)
        except ValueError as exc:
            with self._lock:
                status.state = WorkflowState.FAILED
                status.error = str(exc)
            _set_ended(status, t0)
            self._store.save(status)
            return

        for step in ordered:
            # pause / cancel チェック（各ステップの前に確認）
            while True:
                with self._lock:
                    state = status.state
                if state == WorkflowState.RUNNING:
                    break
                if state in (WorkflowState.CANCELLED, WorkflowState.FAILED):
                    _set_ended(status, t0)
                    self._store.save(status)
                    return
                time.sleep(_POLL_SEC)   # PAUSED → resume() を待つ

            # 依存ステップが失敗/スキップの場合は実行できない
            with self._lock:
                can_run = _can_run(step, status)
            if not can_run:
                with self._lock:
                    status.steps[step.step_id].state = StepState.SKIPPED
                self._store.save(status)
                continue

            # ステップ実行（リトライ・承認待ち込み）
            final_state = self._run_step(step, status)

            # cancel が承認待ち中に来た場合
            with self._lock:
                if status.state == WorkflowState.CANCELLED:
                    break

            # on_failure=ABORT → ワークフロー失敗
            if final_state == StepState.FAILED and step.on_failure == OnFailure.ABORT:
                with self._lock:
                    status.state = WorkflowState.FAILED
                    status.error = status.steps[step.step_id].last_error
                break

        with self._lock:
            if status.state == WorkflowState.RUNNING:
                status.state = WorkflowState.COMPLETED

        _set_ended(status, t0)
        self._store.save(status)

    def _run_step(self, step: "WorkflowStep", status: WorkflowStatus) -> StepState:
        """1ステップをリトライ・承認待ち込みで実行。最終 StepState を返す。"""
        ss       = status.steps[step.step_id]
        executor = self._build_executor(step)

        while True:   # retry loop
            with self._lock:
                ss.state       = StepState.RUNNING
                ss.started_at  = datetime.now().isoformat(timespec="seconds")
                ss.attempt_count += 1
            self._store.save(status)

            t0 = time.monotonic()
            try:
                result = executor.execute(step, status)
            except Exception as exc:
                from .executors.base import StepResult
                result = StepResult(success=False, error=str(exc))

            duration_ms = int((time.monotonic() - t0) * 1000)
            with self._lock:
                ss.duration_ms = duration_ms

            # ---- Human Approval 待ち --------------------------------
            if result.wait_for_approval:
                with self._lock:
                    ss.state    = StepState.WAITING_APPROVAL
                    ss.output   = result.output
                    ss.ended_at = datetime.now().isoformat(timespec="seconds")
                    status.state = WorkflowState.WAITING_APPROVAL
                self._store.save(status)

                while True:
                    with self._lock:
                        step_state = ss.state
                        wf_state   = status.state
                    if step_state != StepState.WAITING_APPROVAL:
                        break
                    if wf_state == WorkflowState.CANCELLED:
                        with self._lock:
                            ss.state      = StepState.FAILED
                            ss.last_error = "キャンセルされました"
                            ss.ended_at   = datetime.now().isoformat(timespec="seconds")
                        break
                    time.sleep(_POLL_SEC)

                with self._lock:
                    return ss.state

            # ---- 成功 -----------------------------------------------
            if result.success:
                with self._lock:
                    ss.state    = StepState.COMPLETED
                    ss.output   = result.output
                    ss.ended_at = datetime.now().isoformat(timespec="seconds")
                self._store.save(status)
                return StepState.COMPLETED

            # ---- 失敗 / リトライ ------------------------------------
            with self._lock:
                ss.last_error   = result.error
                attempt         = ss.attempt_count
                max_retry       = step.retry_max

            if attempt <= max_retry:   # まだリトライ回数が残っている
                with self._lock:
                    ss.state = StepState.RETRYING
                self._store.save(status)
                time.sleep(step.retry_delay_sec)
                continue   # retry

            with self._lock:
                ss.state    = StepState.FAILED
                ss.ended_at = datetime.now().isoformat(timespec="seconds")
            self._store.save(status)
            return StepState.FAILED

    def _build_executor(self, step: "WorkflowStep"):
        """EXECUTOR_REGISTRY から Executor を取得し、依存を注入してインスタンス化する。"""
        cls = self._registry.get(step.step_type.value)
        if cls is None:
            from .executors.base import BaseStepExecutor, StepResult

            class _Unknown(BaseStepExecutor):
                @property
                def step_type(self) -> str:
                    return "unknown"
                def execute(self, s, st) -> StepResult:
                    return StepResult(success=False, error=f"未登録の StepType: {step.step_type}")
            return _Unknown()

        # __init__ のパラメータ名と self._deps のキーが一致する引数だけ注入
        params = set(inspect.signature(cls.__init__).parameters.keys()) - {"self"}
        kwargs = {k: v for k, v in self._deps.items() if k in params}
        return cls(**kwargs)


# ---------------------------------------------------------------------------
# モジュールレベル純粋関数（状態を持たない）
# ---------------------------------------------------------------------------

def _new_status(definition: WorkflowDefinition, context: dict | None) -> WorkflowStatus:
    """WorkflowDefinition から WorkflowStatus の初期インスタンスを生成する。"""
    step_statuses = {
        step.step_id: StepStatus(step_id=step.step_id)
        for step in definition.steps
    }
    return WorkflowStatus(
        definition_name=definition.name,
        steps=step_statuses,
        context=dict(context) if context else {},
    )


def _set_ended(status: WorkflowStatus, t0: float) -> None:
    """ended_at と duration_ms を設定する。"""
    if status.ended_at is None:
        status.ended_at = datetime.now().isoformat(timespec="seconds")
    status.duration_ms = int((time.monotonic() - t0) * 1000)


def _resolve_order(steps: list["WorkflowStep"]) -> list["WorkflowStep"]:
    """
    Kahn's algorithm によるトポロジカルソート。

    依存関係を解決し、実行可能な順序でステップを返す。
    循環依存または未定義依存があれば ValueError を投げる。
    """
    step_map: dict[str, "WorkflowStep"] = {s.step_id: s for s in steps}
    in_degree: dict[str, int]           = {s.step_id: 0 for s in steps}
    dependents: dict[str, list[str]]    = {s.step_id: [] for s in steps}

    for step in steps:
        for dep_id in step.depends_on:
            if dep_id not in step_map:
                raise ValueError(f"未定義の依存ステップ: {dep_id!r} (参照元: {step.step_id!r})")
            in_degree[step.step_id] += 1
            dependents[dep_id].append(step.step_id)

    queue  = [sid for sid, d in in_degree.items() if d == 0]
    result: list["WorkflowStep"] = []

    while queue:
        sid = queue.pop(0)
        result.append(step_map[sid])
        for child_id in dependents[sid]:
            in_degree[child_id] -= 1
            if in_degree[child_id] == 0:
                queue.append(child_id)

    if len(result) != len(steps):
        raise ValueError("循環依存が検出されました")

    return result


def _can_run(step: "WorkflowStep", status: WorkflowStatus) -> bool:
    """すべての依存ステップが COMPLETED かどうかを返す。"""
    for dep_id in step.depends_on:
        dep_ss = status.steps.get(dep_id)
        if dep_ss is None or dep_ss.state != StepState.COMPLETED:
            return False
    return True
