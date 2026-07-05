"""SafeMode — Branch / Patch / Review / Approve / Merge フロー。

from src.utils.json_store import save_json_atomic
既存コードは直接変更しない。
すべての変更は Patch として生成・レビュー・承認・Merge のステップを踏む。

    Branch  : タスクの作業ディレクトリを data/autonomous/patches/{task_id}/ に作成
    Patch   : Dev Factory の workflow を実行し .patch ファイルを生成
    Review  : AI が patch の品質・安全性・目的適合性をスコアリング
    Approve : Dashboard でユーザーが承認（または AI 自動承認: score >= AUTO_APPROVE_SCORE）
    Merge   : approved ディレクトリにコピー + 履歴記録（実ファイル変更は別途手動 or future）
"""
from __future__ import annotations

import json
import re
import shutil
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.autonomous.queue_manager import (
    AutonomousQueue, ImprovementTask, TaskStatus, get_autonomous_queue,
)

_PATCHES_DIR  = Path("data/autonomous/patches")
_APPROVED_DIR = Path("data/autonomous/approved")
_HISTORY_FILE = Path("data/autonomous/history.jsonl")
_lock         = threading.Lock()

# この閾値以上の AI レビュースコアなら自動承認
AUTO_APPROVE_SCORE = 8.5


@dataclass
class BranchInfo:
    task_id:   str
    branch_dir:str
    created_at:str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PatchResult:
    success:        bool
    patch_path:     Optional[str]
    patch_text:     str
    report_path:    Optional[str]
    diff_stats:     dict
    error:          str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ReviewResult:
    success:    bool
    score:      float        # 0〜10 (高いほど良い)
    summary:    str
    risks:      list[str]
    suggestions:list[str]
    auto_approve:bool        # score >= AUTO_APPROVE_SCORE
    error:      str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MergeResult:
    success:       bool
    task_id:       str
    patch_path:    Optional[str]
    approved_dir:  Optional[str]
    applied_at:    str
    error:         str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class SafeMode:
    """
    Branch/Patch/Review/Approve/Merge の一連のフローを管理する。

    使い方:
        sm     = SafeMode()
        branch = sm.create_branch(task)
        patch  = sm.generate_patch(task)
        review = sm.review_patch(task)
        if review.auto_approve:
            sm.approve(task.task_id, "ai_auto")
        merge  = sm.merge(task.task_id)
    """

    def __init__(self, queue: Optional[AutonomousQueue] = None) -> None:
        self._queue = queue or get_autonomous_queue()

    # ── Branch ─────────────────────────────────────────────────────

    def create_branch(self, task: ImprovementTask) -> BranchInfo:
        """タスク専用の作業ディレクトリを作成する。"""
        branch_dir = _PATCHES_DIR / task.task_id
        branch_dir.mkdir(parents=True, exist_ok=True)
        info = BranchInfo(
            task_id    = task.task_id,
            branch_dir = str(branch_dir),
            created_at = datetime.now().isoformat(timespec="seconds"),
        )
        save_json_atomic(branch_dir / "task.json", task.to_dict())
        return info

    # ── Patch ──────────────────────────────────────────────────────

    def generate_patch(self, task: ImprovementTask) -> PatchResult:
        """
        Dev Factory workflow を実行して .patch ファイルを生成する。
        結果は data/autonomous/patches/{task_id}/ に保存される。
        """
        self._queue.set_status(task.task_id, TaskStatus.RUNNING)
        branch_dir = _PATCHES_DIR / task.task_id
        branch_dir.mkdir(parents=True, exist_ok=True)

        try:
            from src.core.kernel import get_kernel
            from src.ai_agents.registry import get_agent_registry

            get_agent_registry().auto_load()
            k = get_kernel()

            # workflow context に出力先を上書き
            ctx = dict(task.context)
            ctx.setdefault("output_dir", str(branch_dir))

            status = k.run_workflow(task.workflow_to_run, ctx)

            # 結果から patch ファイルパスを探す
            patch_path   : Optional[str] = None
            report_path  : Optional[str] = None
            diff_stats   : dict          = {}

            final_ctx = getattr(status, "context", {})
            if "diff_file" in final_ctx:
                src_patch = Path(str(final_ctx["diff_file"]))
                dst_patch = branch_dir / src_patch.name
                if src_patch.exists() and src_patch != dst_patch:
                    shutil.copy2(src_patch, dst_patch)
                patch_path = str(dst_patch) if dst_patch.exists() else str(src_patch)

            if "unified_diff_stats" in final_ctx:
                diff_stats = final_ctx["unified_diff_stats"]

            # report ファイルを探す
            for f in branch_dir.glob("review_*.md"):
                report_path = str(f); break

            patch_text = ""
            if patch_path and Path(patch_path).exists():
                patch_text = Path(patch_path).read_text(encoding="utf-8")

            success = getattr(status, "is_success", lambda: True)()

            result = PatchResult(
                success     = success,
                patch_path  = patch_path,
                patch_text  = patch_text,
                report_path = report_path,
                diff_stats  = diff_stats,
            )
            save_json_atomic(branch_dir / "patch_result.json", result.to_dict())
            return result

        except Exception as exc:
            self._queue.set_status(task.task_id, TaskStatus.FAILED)
            return PatchResult(
                success=False, patch_path=None, patch_text="",
                report_path=None, diff_stats={}, error=str(exc),
            )

    # ── Review ─────────────────────────────────────────────────────

    def review_patch(self, task: ImprovementTask) -> ReviewResult:
        """AI に patch の品質・安全性をレビューさせる。"""
        branch_dir = _PATCHES_DIR / task.task_id
        patch_path = task.patch_path or self._find_patch(branch_dir)

        if not patch_path or not Path(patch_path).exists():
            return ReviewResult(
                success=False, score=0.0, summary="Patch ファイルが見つかりません",
                risks=[], suggestions=[], auto_approve=False,
                error="no_patch_file",
            )

        patch_text = Path(patch_path).read_text(encoding="utf-8")[:3000]

        try:
            from src.ai.router import get_router
            from src.ai.task import AITask, TaskType

            prompt = (
                "あなたは AIOS の品質レビュアーです。\n\n"
                f"## タスク\n{task.title}\n{task.description}\n\n"
                f"## 生成された Patch\n```diff\n{patch_text}\n```\n\n"
                "以下の観点でレビューし、JSON で回答してください:\n"
                "- score: 0〜10 (品質スコア。8.5以上で自動承認)\n"
                "- summary: 1〜2文のサマリー\n"
                "- risks: リスク一覧 (リスト, 最大3件)\n"
                "- suggestions: 改善提案 (リスト, 最大3件)\n\n"
                "形式:\n"
                '{"score":8.5,"summary":"...","risks":["..."],"suggestions":["..."]}\n'
                "JSON のみ出力。"
            )

            resp_task = AITask(task_type=TaskType.DEFAULT, prompt=prompt)
            resp = get_router().route(resp_task)
            if not (resp and resp.ok):
                raise RuntimeError("AI Router エラー")

            match = re.search(r"\{.*?\}", resp.content, re.DOTALL)
            if not match:
                raise ValueError("JSON が見つかりません")
            data = json.loads(match.group())

            score       = float(data.get("score", 5.0))
            auto_approve= score >= AUTO_APPROVE_SCORE
            review      = ReviewResult(
                success     = True,
                score       = score,
                summary     = data.get("summary", ""),
                risks       = data.get("risks", []),
                suggestions = data.get("suggestions", []),
                auto_approve= auto_approve,
            )

            # キューに保存
            self._queue.set_patch(
                task.task_id,
                patch_path   = patch_path,
                review_summary = review.summary,
                review_score   = score,
            )

            # review.json を保存
            save_json_atomic(branch_dir / "review.json", review.to_dict())
            return review

        except Exception as exc:
            return ReviewResult(
                success=False, score=0.0, summary=f"レビューエラー: {exc}",
                risks=[], suggestions=[], auto_approve=False, error=str(exc),
            )

    # ── Approve ────────────────────────────────────────────────────

    def approve(self, task_id: str, approved_by: str = "human") -> bool:
        return self._queue.approve(task_id, approved_by)

    def reject(self, task_id: str, reason: str = "") -> bool:
        return self._queue.reject(task_id, reason)

    # ── Merge ──────────────────────────────────────────────────────

    def merge(self, task_id: str) -> MergeResult:
        """
        承認済み Patch を approved ディレクトリにコピーして履歴に記録する。
        実ファイルへの適用は git apply などで手動実行 (または将来の自動化)。
        """
        task = self._queue.get(task_id)
        if not task:
            return MergeResult(success=False, task_id=task_id, patch_path=None,
                               approved_dir=None, applied_at="", error="タスクが見つかりません")

        if task.status != TaskStatus.APPROVED:
            return MergeResult(success=False, task_id=task_id, patch_path=task.patch_path,
                               approved_dir=None, applied_at="", error="承認済み状態ではありません")

        try:
            applied_at  = datetime.now().isoformat(timespec="seconds")
            approved_dir= _APPROVED_DIR / task_id
            approved_dir.mkdir(parents=True, exist_ok=True)

            # patch ファイルをコピー
            src_patch = Path(task.patch_path) if task.patch_path else None
            dst_patch = None
            if src_patch and src_patch.exists():
                dst_patch = approved_dir / src_patch.name
                shutil.copy2(src_patch, dst_patch)

            # branch ディレクトリ全体をコピー
            branch_dir = _PATCHES_DIR / task_id
            if branch_dir.exists():
                for f in branch_dir.iterdir():
                    shutil.copy2(f, approved_dir / f.name)

            # キューを MERGED に
            self._queue.merge(task_id)

            # 履歴ログに追記
            history_entry = {
                "task_id"     : task_id,
                "title"       : task.title,
                "patch_path"  : str(dst_patch) if dst_patch else None,
                "approved_by" : task.approved_by,
                "review_score": task.review_score,
                "applied_at"  : applied_at,
            }
            _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with _lock:
                with _HISTORY_FILE.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(history_entry, ensure_ascii=False) + "\n")

            return MergeResult(
                success      = True,
                task_id      = task_id,
                patch_path   = str(dst_patch) if dst_patch else None,
                approved_dir = str(approved_dir),
                applied_at   = applied_at,
            )

        except Exception as exc:
            return MergeResult(
                success=False, task_id=task_id, patch_path=task.patch_path,
                approved_dir=None, applied_at="", error=str(exc),
            )

    # ── Cycle: one-shot 実行 ───────────────────────────────────────

    def run_full_cycle(self, task: ImprovementTask, auto_approve: bool = False) -> dict:
        """Branch → Patch → Review → (Approve) → (Merge) を一括実行する。"""
        results: dict = {"task_id": task.task_id}

        branch = self.create_branch(task)
        results["branch"] = branch.to_dict()

        patch = self.generate_patch(task)
        results["patch"] = patch.to_dict()
        if not patch.success:
            return results

        review = self.review_patch(task)
        results["review"] = review.to_dict()

        if auto_approve and review.auto_approve:
            self.approve(task.task_id, "ai_auto")
            merge = self.merge(task.task_id)
            results["merge"] = merge.to_dict()

        return results

    # ── Helpers ────────────────────────────────────────────────────

    def load_history(self, limit: int = 50) -> list[dict]:
        if not _HISTORY_FILE.exists():
            return []
        with _lock:
            lines = _HISTORY_FILE.read_text(encoding="utf-8").splitlines()
        records = []
        for line in reversed(lines[-limit:]):
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
        return records

    def get_patch_text(self, task_id: str) -> str:
        """タスクの Patch テキストを返す。"""
        task = self._queue.get(task_id)
        if task and task.patch_path and Path(task.patch_path).exists():
            return Path(task.patch_path).read_text(encoding="utf-8")
        # branch ディレクトリから探す
        branch_dir = _PATCHES_DIR / task_id
        for f in branch_dir.glob("*.patch") if branch_dir.exists() else []:
            return f.read_text(encoding="utf-8")
        return "(Patch ファイルが見つかりません)"

    @staticmethod
    def _find_patch(branch_dir: Path) -> Optional[str]:
        for f in sorted(branch_dir.glob("*.patch")):
            return str(f)
        return None

