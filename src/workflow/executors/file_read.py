"""FileReadExecutor — ファイルを読み込んでコンテキストに格納する Executor。

Dev Factory でコードファイルを AI に渡す際に使用する。
実ファイルを変更しない（読み取り専用）。

config フィールド:
    file_path             : str  直接パスを指定（省略可）
    file_path_from_context: str  context[key] からパスを取得するキー名
    output_key            : str  context に格納するキー（デフォルト: "file_content"）
    max_lines             : int  最大行数（デフォルト: 600。超過分は切り捨て）
    encoding              : str  エンコーディング（デフォルト: "utf-8"）
    include_line_numbers  : bool 行番号を付加するか（デフォルト: true）
    language_hint         : str  コードブロックの言語ヒント（デフォルト: 自動判定）
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.utils.config import PROJECT_ROOT
from src.utils.path_safety import safe_resolve_path

from .base import BaseStepExecutor, StepResult

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus

_LANG_MAP = {
    ".py":   "python",
    ".js":   "javascript",
    ".ts":   "typescript",
    ".json": "json",
    ".yaml": "yaml",
    ".yml":  "yaml",
    ".md":   "markdown",
    ".sh":   "bash",
    ".html": "html",
    ".css":  "css",
    ".sql":  "sql",
    ".toml": "toml",
    ".txt":  "",
}


class FileReadExecutor(BaseStepExecutor):

    @property
    def step_type(self) -> str:
        return "file_read"

    def execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        try:
            cfg = step.config

            # パスを解決
            file_path: str = cfg.get("file_path", "")
            ctx_key   = cfg.get("file_path_from_context", "")
            if not file_path and ctx_key:
                file_path = str(status.context.get(ctx_key, ""))

            if not file_path:
                status.context[cfg.get("output_key", "file_content")] = "(ファイルパスが指定されていません)"
                return StepResult(
                    success=True,
                    output={cfg.get("output_key", "file_content"): "(ファイルパスが指定されていません)"},
                )

            p = safe_resolve_path(PROJECT_ROOT, file_path)

            if not p.exists():
                out_key = cfg.get("output_key", "file_content")
                msg     = f"(ファイルが見つかりません: {file_path})"
                status.context[out_key]          = msg
                status.context["file_exists"]    = False
                return StepResult(
                    success=True,
                    output={
                        out_key:               msg,
                        "file_exists":         False,
                        "file_path_resolved":  str(p),
                    },
                )

            encoding    = cfg.get("encoding", "utf-8")
            max_lines   = int(cfg.get("max_lines", 600))
            line_nums   = cfg.get("include_line_numbers", True)
            lang_hint   = cfg.get("language_hint", "")
            output_key  = cfg.get("output_key", "file_content")

            raw = p.read_text(encoding=encoding, errors="replace")
            lines = raw.splitlines()
            total_lines = len(lines)
            truncated   = False

            if max_lines and len(lines) > max_lines:
                lines     = lines[:max_lines]
                truncated = True

            if line_nums:
                width      = len(str(total_lines))
                lines_out  = [f"{str(i+1).rjust(width)} | {line}" for i, line in enumerate(lines)]
            else:
                lines_out  = lines

            content_body = "\n".join(lines_out)
            if truncated:
                content_body += f"\n... (表示: {max_lines}/{total_lines} 行)"

            # 言語ヒント（コードブロック表示用）
            if not lang_hint:
                lang_hint = _LANG_MAP.get(p.suffix.lower(), "")

            # コードブロック付きで格納
            formatted = (
                f"# ファイル: {file_path}  ({total_lines} 行)\n"
                f"```{lang_hint}\n{content_body}\n```"
            )

            # context に直接書き込む（AITaskExecutor と同じパターン）
            status.context[output_key]             = formatted
            status.context[f"{output_key}_raw"]    = raw if not truncated else raw[:max_lines * 200]
            status.context["file_path_read"]       = str(p)
            status.context["file_lines"]           = total_lines
            status.context["file_lang"]            = lang_hint
            status.context["file_exists"]          = True

            return StepResult(
                success=True,
                output={
                    output_key:           formatted,
                    f"{output_key}_raw":  status.context[f"{output_key}_raw"],
                    "file_path_read":     str(p),
                    "file_lines":         total_lines,
                    "file_lang":          lang_hint,
                    "file_exists":        True,
                },
            )

        except Exception as exc:
            output_key = step.config.get("output_key", "file_content")
            status.context[output_key] = f"(読み込みエラー: {exc})"
            return StepResult(
                success=True,   # on_failure: continue で続行させる
                output={output_key: f"(読み込みエラー: {exc})"},
            )
