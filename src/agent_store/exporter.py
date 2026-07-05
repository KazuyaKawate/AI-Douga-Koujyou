"""AgentExporter — Agent を .apagent パッケージにエクスポートする。

.apagent は ZIP アーカイブ:
    manifest.json   — PackageManifest
    agent.json      — AgentDefinition
    workflow.json   — WorkflowDefinition (optional)
    template.txt    — プロンプトテンプレート (optional)
    icon.png        — アイコン画像 (optional, placeholder)
"""
from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .manifest import PackageManifest

from src.utils.config import PROJECT_ROOT
from src.utils.path_safety import safe_resolve_path, workspace_relative_path

_OUTPUT_DIR = Path("output/store")

# 最小サイズの有効 PNG (1×1 透明ピクセル)
_PLACEHOLDER_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
    0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
    0x54, 0x78, 0x9C, 0x62, 0x00, 0x01, 0x00, 0x00,
    0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
    0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
    0x42, 0x60, 0x82,
])


def _safe_output_dir(output_dir: Path) -> Path:
    """Resolve package export output under local workspace output/ or data/."""
    p = Path(output_dir)
    rel = workspace_relative_path(PROJECT_ROOT, p) if p.is_absolute() else p
    return safe_resolve_path(PROJECT_ROOT, rel, allowed_subdirs=["output", "data"])


@dataclass
class ExportResult:
    success:      bool
    package_path: Optional[Path] = None
    manifest:     Optional[PackageManifest] = None
    error:        Optional[str] = None

    def __str__(self) -> str:
        if self.success:
            return f"OK → {self.package_path}"
        return f"FAIL: {self.error}"


class AgentExporter:
    """
    AgentDefinition (+ 任意で Workflow / Template) を .apagent にパッケージする。

    使い方:
        exporter = AgentExporter()
        result = exporter.export(
            agent_id       = "writing_specialist",
            author         = "AIOS Team",
            workflow_name  = "writing.article_draft",   # optional
            template_text  = "...",                      # optional
            output_dir     = Path("output/store"),
        )
    """

    def export(
        self,
        agent_id:      str,
        author:        str       = "unknown",
        workflow_name: Optional[str] = None,
        template_text: Optional[str] = None,
        include_icon:  bool      = True,
        output_dir:    Path      = _OUTPUT_DIR,
        tags:          Optional[list[str]] = None,
    ) -> ExportResult:
        """Agent を .apagent ファイルにエクスポートする。"""
        try:
            from src.ai_agents.registry import get_agent_registry
            registry = get_agent_registry()
            agent    = registry.get(agent_id)
            if agent is None:
                return ExportResult(success=False, error=f"Agent not found: {agent_id!r}")

            agent_json = agent.to_json()
            checksum   = PackageManifest.compute_checksum(agent_json)

            # Workflow
            wf_json: Optional[str] = None
            if workflow_name:
                try:
                    from src.core.kernel import get_kernel
                    wf_def = get_kernel().registry.get_workflow(workflow_name)
                    if wf_def:
                        wf_json = json.dumps(wf_def.to_dict(), ensure_ascii=False, indent=2)
                except Exception:
                    pass

            # Manifest
            package_id = f"{agent_id}_pkg"
            manifest   = PackageManifest(
                package_id       = package_id,
                name             = agent.name,
                version          = agent.version,
                author           = author,
                description      = agent.description,
                agent_id         = agent_id,
                workflow_name    = workflow_name,
                has_template     = bool(template_text),
                has_icon         = include_icon,
                tags             = list(tags or agent.tags),
                checksum         = checksum,
                created_at       = datetime.now().isoformat(timespec="seconds"),
            )

            # Build ZIP in memory
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("manifest.json", manifest.to_json())
                zf.writestr("agent.json",    agent_json)
                if wf_json:
                    zf.writestr("workflow.json", wf_json)
                if template_text:
                    zf.writestr("template.txt", template_text)
                if include_icon:
                    zf.writestr("icon.png", _PLACEHOLDER_PNG)

            # Write to disk
            output_dir = _safe_output_dir(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            pkg_path = output_dir / manifest.package_filename()
            pkg_path.write_bytes(buf.getvalue())

            return ExportResult(success=True, package_path=pkg_path, manifest=manifest)

        except Exception as exc:
            return ExportResult(success=False, error=str(exc))

    def export_multiple(
        self,
        agent_ids:  list[str],
        output_dir: Path = _OUTPUT_DIR,
        author:     str  = "unknown",
    ) -> list[ExportResult]:
        """複数 Agent を一括エクスポートする。"""
        return [self.export(aid, author=author, output_dir=output_dir) for aid in agent_ids]

