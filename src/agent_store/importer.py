"""AgentImporter — .apagent を読み込んで即時登録する（再起動不要）。

登録先:
    Agent    → AgentRegistry シングルトン（インメモリ + data/agents/*.json）
    Workflow → kernel.registry（インメモリ）
    Template → data/store/templates/{agent_id}.txt
"""
from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .manifest import PackageManifest

_TEMPLATE_DIR = Path("data/store/templates")


@dataclass
class ImportResult:
    success:        bool
    package_id:     str                  = ""
    agent_id:       str                  = ""
    workflow_name:  Optional[str]        = None
    has_template:   bool                 = False
    manifest:       Optional[PackageManifest] = None
    warnings:       list[str]            = field(default_factory=list)
    error:          Optional[str]        = None

    def __str__(self) -> str:
        if self.success:
            parts = [f"agent={self.agent_id}"]
            if self.workflow_name:
                parts.append(f"workflow={self.workflow_name}")
            if self.has_template:
                parts.append("template=yes")
            return "OK: " + ", ".join(parts)
        return f"FAIL: {self.error}"


class AgentImporter:
    """
    .apagent ファイルを読み込んで Agent / Workflow / Template を即時登録する。

    Kernel / Router / Memory は変更しない。
    AgentRegistry と kernel.registry の既存 API のみ使用する。
    """

    def import_package(
        self,
        package_path: Path,
        overwrite:    bool = True,
    ) -> ImportResult:
        """
        .apagent を読み込んで登録する。

        overwrite=True  : 同 agent_id が既に存在する場合は上書き
        overwrite=False : 既存 Agent がある場合はスキップ
        """
        try:
            path = Path(package_path)
            if not path.exists():
                return ImportResult(success=False, error=f"File not found: {path}")

            if not zipfile.is_zipfile(path):
                return ImportResult(success=False, error=f"Not a valid .apagent (ZIP): {path}")

            result = ImportResult(success=True)

            with zipfile.ZipFile(path, "r") as zf:
                names = zf.namelist()

                # ---- manifest.json (必須) ----
                if "manifest.json" not in names:
                    return ImportResult(success=False, error="manifest.json が見つかりません")
                manifest = PackageManifest.from_json(zf.read("manifest.json").decode("utf-8"))
                result.manifest    = manifest
                result.package_id  = manifest.package_id

                # ---- agent.json (必須) ----
                if "agent.json" not in names:
                    return ImportResult(success=False, error="agent.json が見つかりません")
                agent_json = zf.read("agent.json").decode("utf-8")

                # チェックサム検証
                if not manifest.verify_checksum(agent_json):
                    result.warnings.append("checksum mismatch — package may be tampered")

                agent_dict = json.loads(agent_json)
                from src.ai_agents.definition import AgentDefinition
                agent      = AgentDefinition.from_dict(agent_dict)
                result.agent_id = agent.agent_id

                # AgentRegistry に登録
                from src.ai_agents.registry import get_agent_registry
                reg = get_agent_registry()
                if not overwrite and reg.exists(agent.agent_id):
                    result.warnings.append(f"Agent {agent.agent_id!r} already exists, skipped")
                else:
                    reg.register(agent, overwrite=overwrite)
                    reg.save(agent)

                # ---- workflow.json (任意) ----
                if "workflow.json" in names:
                    try:
                        wf_dict = json.loads(zf.read("workflow.json").decode("utf-8"))
                        from src.workflow.models import WorkflowDefinition
                        wf_def  = WorkflowDefinition.from_dict(wf_dict)
                        from src.core.kernel import get_kernel
                        get_kernel().registry.register_workflow(wf_def)
                        result.workflow_name = wf_def.name
                    except Exception as e:
                        result.warnings.append(f"workflow.json 登録失敗: {e}")

                # ---- template.txt (任意) ----
                if "template.txt" in names:
                    try:
                        template_text = zf.read("template.txt").decode("utf-8")
                        _TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
                        tmpl_path = _TEMPLATE_DIR / f"{agent.agent_id}.txt"
                        tmpl_path.write_text(template_text, encoding="utf-8")
                        result.has_template = True
                    except Exception as e:
                        result.warnings.append(f"template.txt 保存失敗: {e}")

            return result

        except Exception as exc:
            return ImportResult(success=False, error=str(exc))

    def import_from_bytes(
        self,
        data:      bytes,
        overwrite: bool = True,
    ) -> ImportResult:
        """バイト列から直接インポートする（Marketplace ダウンロード用）。"""
        buf  = io.BytesIO(data)
        tmp  = Path("data/store/packages/_tmp_import.apagent")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(data)
        try:
            return self.import_package(tmp, overwrite=overwrite)
        finally:
            tmp.unlink(missing_ok=True)
