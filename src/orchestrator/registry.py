from __future__ import annotations
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from src.workflow.models import WorkflowDefinition
from src.workflow.executors import EXECUTOR_REGISTRY, BaseStepExecutor

if TYPE_CHECKING:
    from src.orchestrator.factories.base import BaseFactory


class FactoryRegistry:
    """
    WorkflowDefinition / Executor / Factory の中央レジストリ。

    auto_discover() で以下を一括登録する:
        1. src.workflow.executors.EXECUTOR_REGISTRY から全 Executor
        2. src.orchestrator.factories.FACTORY_REGISTRY から全 Factory
        3. config/workflow_definitions/*.json から WorkflowDefinition
    """

    def __init__(self) -> None:
        self._workflow_defs:      dict[str, WorkflowDefinition]     = {}
        self._executor_types:     dict[str, type[BaseStepExecutor]] = {}
        self._factory_instances:  dict[str, "BaseFactory"]          = {}

    # ---- Workflow ------------------------------------------------

    def register_workflow(self, definition: WorkflowDefinition) -> None:
        self._workflow_defs[definition.name] = definition

    def get_workflow(self, name: str) -> Optional[WorkflowDefinition]:
        return self._workflow_defs.get(name)

    def list_workflows(self) -> list[str]:
        return list(self._workflow_defs.keys())

    # ---- Executor ------------------------------------------------

    def register_executor(self, name: str, cls: type[BaseStepExecutor]) -> None:
        self._executor_types[name] = cls

    def get_executor_type(self, name: str) -> Optional[type[BaseStepExecutor]]:
        return self._executor_types.get(name)

    def list_executors(self) -> list[str]:
        return list(self._executor_types.keys())

    # ---- Factory -------------------------------------------------

    def register_factory(self, name: str, factory: "BaseFactory") -> None:
        """Factory インスタンスを登録し、所有する WorkflowDefinition も併せて登録する。"""
        self._factory_instances[name] = factory
        for wf_def in factory.build_workflow_definitions():
            self.register_workflow(wf_def)

    def get_factory(self, name: str) -> Optional["BaseFactory"]:
        return self._factory_instances.get(name)

    def list_factories(self) -> list[str]:
        return list(self._factory_instances.keys())

    # ---- Auto Discovery -----------------------------------------

    def auto_discover(
        self,
        workflow_dir: Path = Path("config/workflow_definitions"),
    ) -> dict[str, int]:
        """全リソースを自動探索・登録し、登録件数の summary を返す。"""
        return {
            "executors": self.auto_discover_executors(),
            "factories": self.auto_discover_factories(),
            "workflows": self.auto_discover_workflows(workflow_dir),
        }

    def auto_discover_executors(self) -> int:
        """src.workflow.executors.EXECUTOR_REGISTRY から全 Executor を登録する。"""
        for name, cls in EXECUTOR_REGISTRY.items():
            self._executor_types[name] = cls
        return len(EXECUTOR_REGISTRY)

    def auto_discover_factories(self) -> int:
        """Python Factory と Plugin Factory を両方自動登録する。"""
        count = 0

        # 1. Python ベースの Factory (FACTORY_REGISTRY)
        try:
            from src.orchestrator.factories import FACTORY_REGISTRY
            for name, cls in FACTORY_REGISTRY.items():
                try:
                    instance = cls()
                    self.register_factory(name, instance)
                    count += 1
                except Exception:
                    continue
        except Exception:
            pass

        # 2. Plugin Factory (plugin.json を持つディレクトリを自動探索)
        count += self._discover_plugin_factories()
        return count

    def _discover_plugin_factories(self) -> int:
        """src/orchestrator/factories/ 以下の plugin.json を探索して登録する。

        Python Factory と重複する名前はスキップする（Python Factory が優先）。
        """
        from pathlib import Path
        from src.orchestrator.factories.plugin import PluginFactory

        factory_base = Path(__file__).parent.parent / "orchestrator" / "factories"
        count = 0

        for item in sorted(factory_base.iterdir()):
            if not item.is_dir() or item.name.startswith("_"):
                continue
            manifest = item / "plugin.json"
            if not manifest.exists():
                continue
            try:
                instance    = PluginFactory(manifest)
                plugin_name = instance.factory_name
                if plugin_name in self._factory_instances:
                    continue  # Python Factory が優先
                self.register_factory(plugin_name, instance)
                count += 1
            except Exception:
                continue

        return count

    def auto_discover_workflows(
        self,
        search_dir: Path = Path("config/workflow_definitions"),
    ) -> int:
        """JSON ファイルから WorkflowDefinition を読み込んで登録する。"""
        if not search_dir.exists():
            return 0
        count = 0
        for p in sorted(search_dir.glob("*.json")):
            if p.name.startswith("_"):
                continue
            try:
                wf_def = WorkflowDefinition.from_file(p)
                self.register_workflow(wf_def)
                count += 1
            except Exception:
                continue
        return count
