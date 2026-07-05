"""FileSaveExecutor — コンテキスト値をファイルに保存する Executor。

config フィールド:
    output_dir          : str  保存先ディレクトリ（プロジェクトルート相対）
    value_from_context  : str  context から取得するキー
    filename_prefix     : str  ファイル名プレフィックス（デフォルト: "output"）
    extension           : str  拡張子（デフォルト: ".md"）
    append_timestamp    : bool タイムスタンプをファイル名に付加（デフォルト: true）
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.utils.config import PROJECT_ROOT
from src.utils.path_safety import safe_resolve_path

from .base import BaseStepExecutor, StepResult

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus


class FileSaveExecutor(BaseStepExecutor):

    @property
    def step_type(self) -> str:
        return "file_save"

    def execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        try:
            cfg        = step.config
            output_dir = safe_resolve_path(PROJECT_ROOT, cfg.get("output_dir", "output"))
            prefix     = cfg.get("filename_prefix", "output")
            ext        = cfg.get("extension", ".md")
            timestamp  = cfg.get("append_timestamp", True)
            ctx_key    = cfg.get("value_from_context", "")

            content = str(status.context.get(ctx_key, "")) if ctx_key else ""
            if not content:
                content = str(cfg.get("value", ""))

            if not content:
                return StepResult(success=True, output={"saved": False, "reason": "empty content"})

            output_dir.mkdir(parents=True, exist_ok=True)

            if timestamp:
                ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{prefix}_{ts}{ext}"
            else:
                filename = f"{prefix}{ext}"

            file_path = safe_resolve_path(output_dir, filename)
            file_path.write_text(content, encoding="utf-8")

            return StepResult(
                success=True,
                output={
                    "saved":     True,
                    "file_path": str(file_path),
                    "size_chars": len(content),
                },
            )
        except Exception as exc:
            return StepResult(success=False, error=str(exc))
