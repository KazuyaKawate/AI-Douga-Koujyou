"""AIOS Kernel — central dependency injection and lifecycle manager.

このモジュールが AIOS の唯一の組み立て点です。
Factory が 100 個追加されても Kernel は変更しません。
Router / Memory / WorkflowRunner / Orchestrator はすべてここで初期化されます。

使い方:
    from src.core.kernel import get_kernel
    kernel = get_kernel()
    kernel.router.route(task)
    kernel.memory.set("key", "value")
    kernel.run_workflow("writing.article_draft", context={"topic": "AI"})
"""
from __future__ import annotations

import threading
from pathlib import Path  # noqa: F401 — used in _init_router
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.ai.router import AIRouter
    from src.ai.memory import BaseMemoryProvider
    from src.workflow.runner import WorkflowRunner
    from src.orchestrator.orchestrator import FactoryOrchestrator
    from src.orchestrator.registry import FactoryRegistry
    from src.workflow.models import WorkflowStatus

_lock = threading.Lock()
_instance: "AIOSKernel | None" = None


class AIOSKernel:
    """
    AIOS の中央カーネル。

    起動フロー:
        1. FileMemoryProvider をロード（data/aios_memory.json から復元）
        2. AIRouter を初期化（config/ai_router.json 読み込み）
        3. WorkflowRunner に router / memory を注入
        4. FactoryRegistry.auto_discover() で Factory / Executor / Workflow を全登録
        5. FactoryOrchestrator を起動

    設計原則:
        - Factory は Kernel を参照しない（依存逆転）
        - Kernel はプロバイダー名を知らない（Router が選択する）
        - get_kernel() はシングルトン → Streamlit セッション間で共有される
    """

    def __init__(self) -> None:
        self._init_memory()
        self._init_router()
        self._init_runner()
        self._init_orchestrator()

    # ---- Public accessors -----------------------------------------------

    @property
    def router(self) -> "AIRouter":
        return self._router

    @property
    def memory(self) -> "BaseMemoryProvider":
        return self._memory

    @property
    def runner(self) -> "WorkflowRunner":
        return self._runner

    @property
    def orchestrator(self) -> "FactoryOrchestrator":
        return self._orchestrator

    @property
    def registry(self) -> "FactoryRegistry":
        return self._registry

    # ---- High-level API ------------------------------------------------

    def run_workflow(
        self,
        definition_name: str,
        context: dict | None = None,
    ) -> "WorkflowStatus":
        """Workflow を同期実行して WorkflowStatus を返す。"""
        definition = self._registry.get_workflow(definition_name)
        if definition is None:
            raise ValueError(f"Workflow not found: {definition_name!r}")
        return self._runner.run(definition, context=context)

    def health(self) -> dict:
        """全コンポーネントの健全性を返す。"""
        router_h = self._router.health_check()
        mem_count = self._memory.count()
        wf_list   = self._registry.list_workflows()
        factories  = self._registry.list_factories()
        return {
            "kernel":    "ok",
            "router":    router_h,
            "memory":    {"provider": type(self._memory).__name__, "entries": mem_count},
            "workflows": {"registered": len(wf_list), "names": wf_list},
            "factories": {"registered": len(factories), "names": factories},
        }

    # ---- Initializers --------------------------------------------------

    def _init_memory(self) -> None:
        from src.ai.memory import FileMemoryProvider
        self._memory: "BaseMemoryProvider" = FileMemoryProvider()

    def _init_router(self) -> None:
        # .env は プロジェクトルート固定パスで読み込む（cwd 非依存）
        from dotenv import load_dotenv
        _root = Path(__file__).parent.parent.parent
        load_dotenv(dotenv_path=_root / ".env", override=False)
        from src.ai.router import AIRouter
        from src.ai.logger import NullLogger
        self._router: "AIRouter" = AIRouter(logger=NullLogger(), memory=self._memory)

    def _init_runner(self) -> None:
        from src.workflow.runner import WorkflowRunner
        self._runner: "WorkflowRunner" = WorkflowRunner(
            router=self._router,
            memory=self._memory,
        )

    def _init_orchestrator(self) -> None:
        from src.orchestrator.registry import FactoryRegistry
        from src.orchestrator.orchestrator import FactoryOrchestrator
        from src.orchestrator.models import OrchestratorConfig

        self._registry: "FactoryRegistry" = FactoryRegistry()
        self._registry.auto_discover()

        config = OrchestratorConfig(
            max_concurrent_workflows=4,
            retry_max=1,
            retry_delay_sec=2.0,
        )
        self._orchestrator: "FactoryOrchestrator" = FactoryOrchestrator(
            workflow_runner=self._runner,
            config=config,
            registry=self._registry,
        )


def get_kernel() -> AIOSKernel:
    """シングルトンの AIOSKernel を返す。初回呼び出し時に初期化する。"""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = AIOSKernel()
    return _instance


def reset_kernel() -> None:
    """テスト / 再起動用。次回 get_kernel() で再初期化される。"""
    global _instance
    with _lock:
        _instance = None
