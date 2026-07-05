"""DiffOutputExecutor — AI 生成コードと元ファイルの unified diff を計算・保存する Executor。

実ファイルは変更しない（読み取り専用・差分出力のみ）。

config フィールド:
    original_from_context  : str  元コンテンツのコンテキストキー (raw テキスト)
    modified_from_context  : str  AI 生成コンテンツのコンテキストキー
    file_path_from_context : str  ファイルパスを context から取得するキー（diff ヘッダー用）
    file_path_hint         : str  直接指定するファイルパスヒント
    output_key             : str  diff 文字列を格納するキー（デフォルト: "unified_diff"）
    output_dir             : str  diff ファイルの保存先（デフォルト: "output/dev"）
    context_lines          : int  差分前後に表示するコンテキスト行数（デフォルト: 5）
    save_to_file           : bool ファイルに保存するか（デフォルト: true）
    extract_code_block     : bool AI レスポンスからコードブロックを抽出するか（デフォルト: true）
"""
from __future__ import annotations

import difflib
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from src.utils.config import PROJECT_ROOT
from src.utils.path_safety import safe_resolve_path

from .base import BaseStepExecutor, StepResult

if TYPE_CHECKING:
    from src.workflow.models import WorkflowStep, WorkflowStatus


def _extract_code_block(text: str) -> str:
    """
    ```lang ... ``` または ``` ... ``` からコードを抽出する。
    コードブロックが複数ある場合は最大のものを返す。
    コードブロックが見つからない場合は text をそのまま返す。
    """
    # ```lang\ncode\n``` パターン
    pattern  = r"```(?:\w+)?\n(.*?)```"
    matches  = re.findall(pattern, text, re.DOTALL)
    if matches:
        return max(matches, key=len).strip()
    # バッククォートなしの場合はそのまま
    return text.strip()


def _compute_diff(
    original:  str,
    modified:  str,
    file_path: str,
    context:   int = 5,
) -> str:
    """unified diff を生成して文字列で返す。"""
    orig_lines = original.splitlines(keepends=True)
    mod_lines  = modified.splitlines(keepends=True)

    # 最後に改行がなければ追加
    if orig_lines and not orig_lines[-1].endswith("\n"):
        orig_lines[-1] += "\n"
    if mod_lines and not mod_lines[-1].endswith("\n"):
        mod_lines[-1] += "\n"

    diff_lines = list(difflib.unified_diff(
        orig_lines,
        mod_lines,
        fromfile = f"a/{file_path}",
        tofile   = f"b/{file_path}",
        n        = context,
    ))

    if not diff_lines:
        return "(変更なし — 元ファイルと同一です)"

    return "".join(diff_lines)


def _count_changes(diff_text: str) -> dict:
    """差分の統計情報を計算する。"""
    added   = sum(1 for l in diff_text.splitlines() if l.startswith("+") and not l.startswith("+++"))
    removed = sum(1 for l in diff_text.splitlines() if l.startswith("-") and not l.startswith("---"))
    return {"added": added, "removed": removed, "net": added - removed}


class DiffOutputExecutor(BaseStepExecutor):

    @property
    def step_type(self) -> str:
        return "diff_output"

    def execute(self, step: "WorkflowStep", status: "WorkflowStatus") -> StepResult:
        try:
            cfg = step.config

            # 元コンテンツ（raw テキスト）を取得
            orig_key    = cfg.get("original_from_context", "file_content_raw")
            original    = str(status.context.get(orig_key, ""))

            # AI 生成コンテンツを取得
            mod_key     = cfg.get("modified_from_context", "modified_code")
            modified_raw= str(status.context.get(mod_key, ""))

            # コードブロック抽出
            if cfg.get("extract_code_block", True):
                modified = _extract_code_block(modified_raw)
            else:
                modified = modified_raw.strip()

            # ファイルパスヒント（diff ヘッダー用）
            path_ctx  = cfg.get("file_path_from_context", "target_file")
            file_path = str(status.context.get(path_ctx, "")) or cfg.get("file_path_hint", "target_file")
            safe_diff_path = safe_resolve_path(PROJECT_ROOT, file_path)
            display_path = str(safe_diff_path.relative_to(PROJECT_ROOT.resolve(strict=False)))

            output_key    = cfg.get("output_key", "unified_diff")
            context_lines = int(cfg.get("context_lines", 5))

            if not original:
                diff_text = (
                    f"--- /dev/null\n+++ b/{display_path}\n"
                    + "".join(f"+{l}\n" for l in modified.splitlines())
                )
                stats = {"added": len(modified.splitlines()), "removed": 0, "net": len(modified.splitlines())}
            elif not modified:
                return StepResult(
                    success=True,
                    output={output_key: "(AI が修正コードを生成しませんでした)"},
                )
            else:
                diff_text = _compute_diff(original, modified, display_path, context_lines)
                stats     = _count_changes(diff_text)

            output: dict = {
                output_key:             diff_text,
                f"{output_key}_stats":  stats,
                "modified_code_clean":  modified,
            }

            # ファイル保存
            if cfg.get("save_to_file", True):
                out_dir  = safe_resolve_path(PROJECT_ROOT, cfg.get("output_dir", "output/dev"))
                out_dir.mkdir(parents=True, exist_ok=True)
                ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe     = Path(display_path).stem or "unknown"
                diff_path= safe_resolve_path(out_dir, f"diff_{safe}_{ts}.patch")
                diff_path.write_text(diff_text, encoding="utf-8")
                output["diff_file"] = str(diff_path)

            # context に直接書き込む（AITaskExecutor と同じパターン）
            for k, v in output.items():
                status.context[k] = v

            return StepResult(success=True, output=output)

        except Exception as exc:
            return StepResult(success=False, error=f"DiffOutputExecutor: {exc}")

