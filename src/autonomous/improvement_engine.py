"""ImprovementEngine — Workflow 実行後に成功率・速度・品質・失敗内容を分析し改善候補を生成する。

IntelligenceAnalyzer の分析結果を元に、具体的な改善アクションを提案する。
実際の変更は行わない。SafeMode 経由の Patch/Review/Approve/Merge フローに渡す。
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

_ENGINE_LOG  = Path("data/autonomous/improvement_log.jsonl")
_lock        = threading.Lock()


# ── データ構造 ─────────────────────────────────────────────────────

@dataclass
class ImprovementCandidate:
    """1つの改善候補。"""
    candidate_id:     str
    target_type:      str            # "agent" | "workflow" | "factory" | "system"
    target_id:        str            # agent_id / workflow_name / factory_id
    issue_type:       str            # "low_success_rate"|"slow_speed"|"unused"|"low_quality"|"error_pattern"
    priority:         float          # 0.0〜1.0 (高いほど優先)
    title:            str
    description:      str
    suggestion:       str            # 具体的な改善案
    evidence:         dict           # 根拠となるメトリクス
    auto_executable:  bool           # 人間承認なしで自動実行可能か
    workflow_hint:    str            # 使うべき dev.* workflow
    created_at:       str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ImprovementCandidate":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ImprovementRecord:
    """改善サイクル1回の記録。"""
    record_id:    str
    analyzed_at:  str
    period_days:  int
    total_execs:  int
    candidates:   list[dict]   # ImprovementCandidate.to_dict()
    summary:      str

    def to_dict(self) -> dict:
        return asdict(self)


# ── ImprovementEngine ──────────────────────────────────────────────

class ImprovementEngine:
    """
    実行データを分析して ImprovementCandidate 一覧を生成する。

    使い方:
        engine     = ImprovementEngine()
        candidates = engine.analyze(period_days=30)
        for c in candidates:
            print(c.priority, c.title, c.suggestion)
    """

    # 閾値
    SUCCESS_RATE_WARN  = 70.0    # 成功率がこれを下回ったら警告
    AVG_MS_WARN        = 25_000  # 平均実行時間がこれを超えたら警告
    MIN_USES_FOR_RANK  = 3       # ランキング対象とする最小実行回数
    UNUSED_DAYS        = 7       # N日以上未使用なら「未使用」候補に

    def analyze(self, period_days: int = 30) -> list[ImprovementCandidate]:
        """現在の実行データを分析して改善候補を返す。"""
        from src.intelligence.analyzer import IntelligenceAnalyzer
        report     = IntelligenceAnalyzer().analyze(period_days)
        candidates: list[ImprovementCandidate] = []
        import uuid

        # ── Workflow 分析 ─────────────────────────────────────────
        for ws in report.workflow_stats:
            # 低成功率
            if ws.total >= self.MIN_USES_FOR_RANK and ws.success_rate < self.SUCCESS_RATE_WARN:
                candidates.append(ImprovementCandidate(
                    candidate_id   = str(uuid.uuid4())[:8],
                    target_type    = "workflow",
                    target_id      = ws.name,
                    issue_type     = "low_success_rate",
                    priority       = self._priority(ws.success_rate, 0, 100, invert=True),
                    title          = f"[低成功率] {ws.name}",
                    description    = f"成功率 {ws.success_rate:.1f}% ({ws.success}/{ws.total}回)",
                    suggestion     = (
                        f"AI プロンプトを見直す / retry_max を増やす / "
                        f"on_failure 戦略を変更する"
                    ),
                    evidence       = {"success_rate": ws.success_rate, "total": ws.total},
                    auto_executable= False,
                    workflow_hint  = "dev.fix_bug",
                ))

            # 低速
            if ws.total >= self.MIN_USES_FOR_RANK and ws.avg_ms > self.AVG_MS_WARN:
                candidates.append(ImprovementCandidate(
                    candidate_id   = str(uuid.uuid4())[:8],
                    target_type    = "workflow",
                    target_id      = ws.name,
                    issue_type     = "slow_speed",
                    priority       = self._priority(ws.avg_ms, 0, 120_000),
                    title          = f"[低速] {ws.name}",
                    description    = f"平均 {ws.avg_ms/1000:.1f}秒 — 目標: {self.AVG_MS_WARN/1000:.0f}秒以下",
                    suggestion     = "ステップを並列化 / timeout を短縮 / 軽量モデルへ切替",
                    evidence       = {"avg_ms": ws.avg_ms},
                    auto_executable= False,
                    workflow_hint  = "dev.refactor",
                ))

        # ── 未使用 Factory 分析 ───────────────────────────────────
        try:
            from src.core.kernel import get_kernel
            all_factories = set(get_kernel().registry.list_factories())
            used_factories = {ws.factory_id for ws in report.workflow_stats if ws.total > 0}
            for fid in sorted(all_factories - used_factories):
                if fid in ("demo_plugin",):
                    continue  # 無視リスト
                candidates.append(ImprovementCandidate(
                    candidate_id   = str(uuid.uuid4())[:8],
                    target_type    = "factory",
                    target_id      = fid,
                    issue_type     = "unused",
                    priority       = 0.3,
                    title          = f"[未使用] Factory: {fid}",
                    description    = f"直近 {period_days} 日間、一度も実行されていません",
                    suggestion     = "利用ガイドを追加 / Scheduler でデモ実行を登録",
                    evidence       = {"period_days": period_days},
                    auto_executable= True,
                    workflow_hint  = "composer.compose_workflow",
                ))
        except Exception:
            pass

        # ── AI による深層分析候補生成 ─────────────────────────────
        ai_candidates = self._ai_suggest(report, period_days)
        candidates.extend(ai_candidates)

        # 優先度順にソート
        candidates.sort(key=lambda c: c.priority, reverse=True)

        # ログに保存
        record = ImprovementRecord(
            record_id   = str(uuid.uuid4())[:8],
            analyzed_at = datetime.now().isoformat(timespec="seconds"),
            period_days = period_days,
            total_execs = report.total_executions,
            candidates  = [c.to_dict() for c in candidates],
            summary     = f"{len(candidates)} 件の改善候補を検出",
        )
        self._save_record(record)

        return candidates

    def load_latest_candidates(self) -> list[ImprovementCandidate]:
        """最新の分析結果から候補を復元する。"""
        records = self._load_records()
        if not records:
            return []
        latest = records[-1]
        return [ImprovementCandidate.from_dict(d) for d in latest.get("candidates", [])]

    def load_history(self, limit: int = 20) -> list[dict]:
        """過去の分析ログを返す。"""
        return self._load_records()[-limit:]

    # ── Private ────────────────────────────────────────────────────

    def _ai_suggest(self, report, period_days: int) -> list[ImprovementCandidate]:
        """AI (Router 経由) に深層分析を依頼して候補を追加生成する。"""
        if report.total_executions < 3:
            return []
        try:
            from src.ai.router import get_router
            from src.ai.task import AITask, TaskType
            import uuid

            summary = report.to_markdown()[:1500]
            prompt  = (
                f"以下は AIOS の実行分析レポートです。\n\n{summary}\n\n"
                "このデータから、まだ気づいていない改善点を JSON 配列で3件提案してください。\n"
                "形式:\n"
                '[{"title":"...","target_id":"...","issue_type":"...","suggestion":"...","priority":0.5}]\n'
                "priority は 0.0〜1.0。JSON 配列のみ出力。"
            )
            task = AITask(task_type=TaskType.DEFAULT, prompt=prompt)
            resp = get_router().route(task)
            if not (resp and resp.ok):
                return []

            import re, json
            match = re.search(r"\[.*?\]", resp.content, re.DOTALL)
            if not match:
                return []
            items = json.loads(match.group())
            out   = []
            for item in items[:3]:
                out.append(ImprovementCandidate(
                    candidate_id   = str(uuid.uuid4())[:8],
                    target_type    = "system",
                    target_id      = item.get("target_id", "aios"),
                    issue_type     = item.get("issue_type", "ai_suggestion"),
                    priority       = float(item.get("priority", 0.5)),
                    title          = f"[AI提案] {item.get('title','')}",
                    description    = item.get("title", ""),
                    suggestion     = item.get("suggestion", ""),
                    evidence       = {"source": "ai_analysis"},
                    auto_executable= False,
                    workflow_hint  = "dev.implement_plan",
                ))
            return out
        except Exception:
            return []

    @staticmethod
    def _priority(value: float, min_v: float, max_v: float, invert: bool = False) -> float:
        """値を 0.0〜1.0 の優先度に正規化する。"""
        if max_v == min_v:
            return 0.5
        norm = (value - min_v) / (max_v - min_v)
        norm = max(0.0, min(1.0, norm))
        return (1.0 - norm) if not invert else norm

    def _save_record(self, record: ImprovementRecord) -> None:
        _ENGINE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            with _ENGINE_LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    def _load_records(self) -> list[dict]:
        if not _ENGINE_LOG.exists():
            return []
        with _lock:
            lines = _ENGINE_LOG.read_text(encoding="utf-8").splitlines()
        records = []
        for line in lines:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
        return records

