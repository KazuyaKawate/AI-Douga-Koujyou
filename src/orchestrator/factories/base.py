from __future__ import annotations
from abc import ABC, abstractmethod

from src.workflow.models import WorkflowDefinition


class BaseFactory(ABC):
    """
    Factory の基底クラス。

    各 Factory は factory_name と build_workflow_definitions() を実装する。
    FactoryRegistry.register_factory() が呼ぶと、
    build_workflow_definitions() の返す全 WorkflowDefinition が自動登録される。
    """

    @property
    @abstractmethod
    def factory_name(self) -> str:
        """Registry キーとなる一意名称。"""

    def build_workflow_definitions(self) -> list[WorkflowDefinition]:
        """この Factory が管理する WorkflowDefinition リストを返す。"""
        return []

    def get_default_context(self) -> dict:
        """Workflow 起動時に注入するデフォルトコンテキストを返す。"""
        return {}
