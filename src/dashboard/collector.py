from __future__ import annotations
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from .models import (
    ApiKeyStatus,
    DashboardData,
    ErrorEntry,
    GitStatus,
    InfraStatus,
    ProviderStatus,
    SchedulerStats,
    SnapshotStatus,
    TaskQueueStats,
    UsageStats,
)

if TYPE_CHECKING:
    from src.ai.logger import BaseRouterLogger, InMemoryLogger
    from src.ai.memory import BaseMemoryProvider


class DashboardCollector:
    """
    Factory Dashboard 用データ収集クラス。

    外部 API 通信は一切行わない。
    logger / memory は任意注入。未注入時は 0 / 空を返す。
    """

    def __init__(
        self,
        logger: "BaseRouterLogger | None" = None,
        memory: "BaseMemoryProvider | None" = None,
    ) -> None:
        self._logger = logger
        self._memory = memory

    def collect(self) -> DashboardData:
        providers, api_keys = self._collect_providers()
        return DashboardData(
            collected_at=datetime.now(),
            git=self._collect_git(),
            providers=providers,
            api_keys=api_keys,
            usage_today=self._collect_usage_today(),
            infra=self._collect_infra(),
            task_queue=self._collect_task_queue(),
            scheduler=self._collect_scheduler(),
            recent_errors=self._collect_errors(),
        )

    # ---- Git -------------------------------------------------------

    def _collect_git(self) -> GitStatus:
        try:
            def _run(*args: str) -> str:
                r = subprocess.run(
                    list(args),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                return r.stdout.strip() if r.returncode == 0 else ""

            branch = _run("git", "rev-parse", "--abbrev-ref", "HEAD")
            log    = _run("git", "log", "--oneline", "-1")
            parts  = log.split(" ", 1)
            latest_hash = parts[0] if parts else ""
            latest_msg  = parts[1] if len(parts) > 1 else ""

            # upstream がない場合も returncode != 0 になるため個別チェック
            up_result = subprocess.run(
                ["git", "rev-list", "@{u}..HEAD", "--count"],
                capture_output=True, text=True, encoding="utf-8",
            )
            unpushed = int(up_result.stdout.strip()) if up_result.returncode == 0 else 0

            return GitStatus(
                branch=branch,
                latest_hash=latest_hash,
                latest_message=latest_msg,
                unpushed_count=unpushed,
            )
        except Exception as exc:
            return GitStatus(error=str(exc))

    # ---- AI Provider ------------------------------------------------

    def _collect_providers(self) -> tuple[list[ProviderStatus], ApiKeyStatus]:
        try:
            from src.ai.router import AIRouter
            router = AIRouter()
            health = router.health_check()

            statuses: list[ProviderStatus] = []
            key_configured = 0
            for name, h in health.get("providers", {}).items():
                has_key = bool(h.get("api_key_configured", False))
                statuses.append(ProviderStatus(
                    name=name,
                    enabled=bool(h.get("enabled", False)),
                    has_api_key=has_key,
                    model=str(h.get("model", "")),
                ))
                if has_key:
                    key_configured += 1

            return statuses, ApiKeyStatus(
                configured_count=key_configured,
                total_count=len(statuses),
            )
        except Exception:
            return [], ApiKeyStatus()

    # ---- Usage 統計 -------------------------------------------------

    def _collect_usage_today(self) -> UsageStats:
        try:
            from src.ai.logger import InMemoryLogger
            if not isinstance(self._logger, InMemoryLogger):
                return UsageStats()
            entries = self._logger.get_today()
            total_tokens = sum(
                (e.input_tokens or 0) + (e.output_tokens or 0)
                for e in entries
            )
            total_cost = sum(e.cost_usd or 0.0 for e in entries)
            return UsageStats(
                total_tokens=total_tokens,
                total_cost_usd=total_cost,
                request_count=len(entries),
            )
        except Exception:
            return UsageStats()

    # ---- インフラ ------------------------------------------------

    def _collect_infra(self) -> InfraStatus:
        # Logger 型名
        try:
            logger_type = type(self._logger).__name__ if self._logger else "NullLogger"
        except Exception:
            logger_type = "不明"

        # Memory 件数
        memory_count = 0
        try:
            if self._memory is not None:
                memory_count = self._memory.count()
        except Exception:
            pass

        # Snapshot
        snapshot = self._collect_snapshot()

        return InfraStatus(
            logger_type=logger_type,
            sheets_connected=False,  # Google Sheets は allow_write=False の間は未接続扱い
            memory_count=memory_count,
            snapshot=snapshot,
        )

    def _collect_snapshot(self) -> SnapshotStatus:
        try:
            path = Path("snapshots/latest.json")
            if not path.exists():
                return SnapshotStatus(exists=False)
            data = json.loads(path.read_text(encoding="utf-8"))
            return SnapshotStatus(
                exists=True,
                created_at=data.get("created_at"),
                schema_version=data.get("schema_version"),
            )
        except Exception as exc:
            return SnapshotStatus(exists=False, error=str(exc))

    # ---- Task Queue -----------------------------------------------

    def _collect_task_queue(self) -> TaskQueueStats:
        """data/inbox_queue_stats.json から統計を読む。ファイル未生成時は 0 を返す。"""
        try:
            stats_path = Path("data/inbox_queue_stats.json")
            if not stats_path.exists():
                return TaskQueueStats()
            data = json.loads(stats_path.read_text(encoding="utf-8"))
            return TaskQueueStats(
                pending=int(data.get("pending", 0)),
                running=int(data.get("running", 0)),
                completed_today=int(data.get("completed_today", 0)),
            )
        except Exception:
            return TaskQueueStats()

    # ---- Scheduler -----------------------------------------------

    def _collect_scheduler(self) -> SchedulerStats:
        """data/scheduler_status.json から統計を読む。ファイル未生成時はデフォルト値を返す。"""
        try:
            path = Path("data/scheduler_status.json")
            if not path.exists():
                return SchedulerStats()
            data = json.loads(path.read_text(encoding="utf-8"))
            return SchedulerStats(
                running=bool(data.get("running", False)),
                trigger_name=str(data.get("trigger_name", "---") or "---"),
                iteration_count=int(data.get("iteration_count", 0)),
                tasks_processed_today=int(data.get("tasks_processed_today", 0)),
                last_started_at=data.get("last_started_at"),
                last_ended_at=data.get("last_ended_at"),
                last_duration_ms=int(data.get("last_duration_ms", 0)),
                last_success=bool(data.get("last_success", True)),
                next_scheduled_at=data.get("next_scheduled_at"),
                last_error=data.get("last_error"),
            )
        except Exception:
            return SchedulerStats()

    # ---- エラーログ -----------------------------------------------

    def _collect_errors(self) -> list[ErrorEntry]:
        try:
            from src.ai.logger import InMemoryLogger
            if not isinstance(self._logger, InMemoryLogger):
                return []
            failed = [e for e in self._logger.get_all() if not e.success]
            recent = failed[-5:]  # 直近 5 件
            return [
                ErrorEntry(
                    timestamp=e.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    provider=e.provider,
                    message=e.error_message or "",
                )
                for e in recent
            ]
        except Exception:
            return []
