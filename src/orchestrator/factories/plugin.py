"""PluginFactory — JSON ファイルだけで追加できる Factory プラグイン。

新しい Factory を追加するには、以下のディレクトリを作成するだけです:

    src/orchestrator/factories/{factory_name}/
        plugin.json           ← Factory マニフェスト（必須）
        workflows/
            my_workflow.json  ← WorkflowDefinition（0個以上）
        agents/
            my_agent.json     ← AgentDefinition（0個以上）
        templates/
            my_prompt.txt     ← プロンプトテンプレート（オプション）

Kernel・Router・Memory の変更不要。
FACTORY_REGISTRY への手動登録不要。
Python コード不要。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from src.workflow.models import WorkflowDefinition
from .base import BaseFactory


class PluginFactory(BaseFactory):
    """
    plugin.json マニフェストと workflows/*.json から動的に構成される Factory。

    plugin.json の最小構成:
    {
        "factory_id": "my_factory",
        "name": "My Factory",
        "version": "1.0.0",
        "description": "説明文"
    }
    """

    def __init__(self, manifest_path: Path) -> None:
        self._plugin_dir    = manifest_path.parent
        self._manifest_path = manifest_path
        self._manifest      = json.loads(manifest_path.read_text(encoding="utf-8"))
        self._agents_loaded = False

    # ---- BaseFactory interface --------------------------------------

    @property
    def factory_name(self) -> str:
        return self._manifest["factory_id"]

    def build_workflow_definitions(self) -> list[WorkflowDefinition]:
        self._ensure_agents_loaded()
        workflows: list[WorkflowDefinition] = []
        wf_dir = self._plugin_dir / "workflows"
        if not wf_dir.exists():
            return workflows
        for wf_file in sorted(wf_dir.glob("*.json")):
            if wf_file.name.startswith("_"):
                continue
            try:
                wf = WorkflowDefinition.from_file(wf_file)
                workflows.append(wf)
            except Exception:
                continue
        return workflows

    def get_default_context(self) -> dict:
        return self._manifest.get("default_context", {})

    # ---- Plugin metadata -------------------------------------------

    @property
    def plugin_name(self) -> str:
        return self._manifest.get("name", self.factory_name)

    @property
    def plugin_version(self) -> str:
        return self._manifest.get("version", "1.0.0")

    @property
    def plugin_description(self) -> str:
        return self._manifest.get("description", "")

    def list_template_names(self) -> list[str]:
        templates_dir = self._plugin_dir / "templates"
        if not templates_dir.exists():
            return []
        return [f.stem for f in sorted(templates_dir.glob("*.*"))
                if not f.name.startswith("_")]

    def get_template_path(self, name: str) -> Optional[Path]:
        templates_dir = self._plugin_dir / "templates"
        for ext in (".txt", ".md", ".j2"):
            candidate = templates_dir / f"{name}{ext}"
            if candidate.exists():
                return candidate
        return None

    # ---- Private ----------------------------------------------------

    def _ensure_agents_loaded(self) -> None:
        if self._agents_loaded:
            return
        self._agents_loaded = True
        agents_dir = self._plugin_dir / "agents"
        if not agents_dir.exists():
            return
        try:
            from src.ai_agents.registry import get_agent_registry
            from src.ai_agents.definition import AgentDefinition
            registry = get_agent_registry()
            for agent_file in sorted(agents_dir.glob("*.json")):
                if agent_file.name.startswith("_"):
                    continue
                try:
                    data  = json.loads(agent_file.read_text(encoding="utf-8"))
                    agent = AgentDefinition.from_dict(data)
                    if agent.factory_id is None:
                        agent.factory_id = self.factory_name
                    registry.register(agent, overwrite=False)
                except Exception:
                    continue
        except Exception:
            pass
