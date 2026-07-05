"""IntelligenceAnalyzer — 実行ログを集計して AIOS の自己分析レポートを生成する。

集計項目:
    - Workflow 別: 実行回数・成功率・平均時間・出力量
    - Factory 別: 利用頻度・成功率
    - Agent ランキング: 最多利用・最高成功率
    - 改善提案: 失敗率が高い / 実行時間が長い Workflow
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

from .tracker import ExecutionRecord, get_tracker


@dataclass
class WorkflowStats:
    name:         str
    factory_id:   str
    total:        int    = 0
    success:      int    = 0
    failure:      int    = 0
    avg_ms:       float  = 0.0
    avg_chars:    float  = 0.0
    last_run:     str    = ""

    @property
    def success_rate(self) -> float:
        return (self.success / self.total * 100) if self.total else 0.0

    def to_dict(self) -> dict:
        return {
            "name":         self.name,
            "factory_id":   self.factory_id,
            "total":        self.total,
            "success":      self.success,
            "failure":      self.failure,
            "success_rate": round(self.success_rate, 1),
            "avg_ms":       round(self.avg_ms),
            "avg_chars":    round(self.avg_chars),
            "last_run":     self.last_run,
        }


@dataclass
class FactoryStats:
    factory_id:   str
    total:        int   = 0
    success:      int   = 0
    workflows:    int   = 0

    @property
    def success_rate(self) -> float:
        return (self.success / self.total * 100) if self.total else 0.0

    def to_dict(self) -> dict:
        return {
            "factory_id":   self.factory_id,
            "total":        self.total,
            "success":      self.success,
            "success_rate": round(self.success_rate, 1),
            "workflows":    self.workflows,
        }


@dataclass
class AgentRankEntry:
    agent_id:   str
    uses:       int   = 0
    successes:  int   = 0

    @property
    def success_rate(self) -> float:
        return (self.successes / self.uses * 100) if self.uses else 0.0

    def to_dict(self) -> dict:
        return {
            "agent_id":    self.agent_id,
            "uses":        self.uses,
            "success_rate": round(self.success_rate, 1),
        }


@dataclass
class ImprovementSuggestion:
    level:    str     # "warning" | "info"
    target:   str     # workflow_name or factory_id
    message:  str
    metric:   str
    value:    float

    def to_dict(self) -> dict:
        return {
            "level":   self.level,
            "target":  self.target,
            "message": self.message,
            "metric":  self.metric,
            "value":   round(self.value, 1),
        }


@dataclass
class IntelligenceReport:
    generated_at:     str
    total_executions: int
    overall_success:  float
    period_days:      int
    workflow_stats:   list[WorkflowStats]   = field(default_factory=list)
    factory_stats:    list[FactoryStats]    = field(default_factory=list)
    agent_ranking:    list[AgentRankEntry]  = field(default_factory=list)
    suggestions:      list[ImprovementSuggestion] = field(default_factory=list)
    top_workflows:    list[WorkflowStats]   = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "generated_at":     self.generated_at,
            "total_executions": self.total_executions,
            "overall_success":  round(self.overall_success, 1),
            "period_days":      self.period_days,
            "workflow_stats":   [w.to_dict() for w in self.workflow_stats],
            "factory_stats":    [f.to_dict() for f in self.factory_stats],
            "agent_ranking":    [a.to_dict() for a in self.agent_ranking],
            "suggestions":      [s.to_dict() for s in self.suggestions],
            "top_workflows":    [w.to_dict() for w in self.top_workflows],
        }

    def to_markdown(self) -> str:
        lines = [
            f"# AIOS Intelligence Report",
            f"**生成日時**: {self.generated_at}  |  **期間**: 直近 {self.period_days} 日",
            f"**総実行数**: {self.total_executions}  |  **全体成功率**: {self.overall_success:.1f}%",
            "",
            "## Workflow ランキング（利用頻度順）",
        ]
        for i, w in enumerate(self.top_workflows[:10], 1):
            lines.append(
                f"{i}. **{w.name}** — {w.total}回 / 成功率{w.success_rate:.0f}% / "
                f"平均{w.avg_ms:.0f}ms"
            )
        lines += ["", "## Factory 別サマリー"]
        for f in self.factory_stats:
            lines.append(
                f"- **{f.factory_id}**: {f.total}回 / 成功率{f.success_rate:.0f}%"
            )
        lines += ["", "## Agent ランキング（利用回数順）"]
        for i, a in enumerate(self.agent_ranking[:10], 1):
            lines.append(
                f"{i}. **{a.agent_id}** — {a.uses}回使用 / 成功率{a.success_rate:.0f}%"
            )
        if self.suggestions:
            lines += ["", "## 改善提案"]
            for s in self.suggestions:
                icon = "⚠️" if s.level == "warning" else "ℹ️"
                lines.append(f"- {icon} **{s.target}**: {s.message} ({s.metric}: {s.value:.1f})")
        return "\n".join(lines)


class IntelligenceAnalyzer:
    """
    ExecutionTracker のログを集計して IntelligenceReport を生成する。

    使い方:
        analyzer = IntelligenceAnalyzer()
        report   = analyzer.analyze(period_days=30)
        print(report.to_markdown())
    """

    def analyze(self, period_days: int = 30) -> IntelligenceReport:
        records = get_tracker().load_all()

        # 期間フィルタ
        cutoff = datetime.now() - timedelta(days=period_days)
        records = [
            r for r in records
            if self._parse_ts(r.timestamp) >= cutoff
        ]

        if not records:
            return IntelligenceReport(
                generated_at     = datetime.now().isoformat(timespec="seconds"),
                total_executions = 0,
                overall_success  = 0.0,
                period_days      = period_days,
            )

        total   = len(records)
        success = sum(1 for r in records if r.success)

        wf_map:  dict[str, WorkflowStats]  = {}
        fac_map: dict[str, FactoryStats]   = {}
        agt_map: dict[str, AgentRankEntry] = {}

        for rec in records:
            # Workflow 集計
            ws = wf_map.setdefault(
                rec.workflow_name,
                WorkflowStats(name=rec.workflow_name, factory_id=rec.factory_id)
            )
            ws.total += 1
            if rec.success:
                ws.success += 1
            else:
                ws.failure += 1
            ws.avg_ms    = (ws.avg_ms * (ws.total - 1) + rec.duration_ms) / ws.total
            ws.avg_chars = (ws.avg_chars * (ws.total - 1) + rec.output_chars) / ws.total
            if rec.timestamp > ws.last_run:
                ws.last_run = rec.timestamp

            # Factory 集計
            fs = fac_map.setdefault(
                rec.factory_id,
                FactoryStats(factory_id=rec.factory_id)
            )
            fs.total += 1
            if rec.success:
                fs.success += 1

            # Agent 集計
            for aid in rec.agent_ids:
                ae = agt_map.setdefault(aid, AgentRankEntry(agent_id=aid))
                ae.uses += 1
                if rec.success:
                    ae.successes += 1

        # Factory workflows カウント
        for ws in wf_map.values():
            fac_map.setdefault(ws.factory_id, FactoryStats(factory_id=ws.factory_id)).workflows += 1

        workflow_list = sorted(wf_map.values(), key=lambda w: w.total, reverse=True)
        factory_list  = sorted(fac_map.values(), key=lambda f: f.total, reverse=True)
        agent_list    = sorted(agt_map.values(), key=lambda a: a.uses, reverse=True)

        suggestions = self._generate_suggestions(workflow_list, factory_list)

        return IntelligenceReport(
            generated_at     = datetime.now().isoformat(timespec="seconds"),
            total_executions = total,
            overall_success  = success / total * 100,
            period_days      = period_days,
            workflow_stats   = workflow_list,
            factory_stats    = factory_list,
            agent_ranking    = agent_list,
            suggestions      = suggestions,
            top_workflows    = workflow_list[:10],
        )

    def _generate_suggestions(
        self,
        workflows: list[WorkflowStats],
        factories: list[FactoryStats],
    ) -> list[ImprovementSuggestion]:
        suggestions: list[ImprovementSuggestion] = []

        for ws in workflows:
            if ws.total >= 3 and ws.success_rate < 50:
                suggestions.append(ImprovementSuggestion(
                    level   = "warning",
                    target  = ws.name,
                    message = f"失敗率が高い ({100 - ws.success_rate:.0f}%) — プロンプトまたは Agent 設定を見直してください",
                    metric  = "success_rate",
                    value   = ws.success_rate,
                ))
            if ws.total >= 3 and ws.avg_ms > 30_000:
                suggestions.append(ImprovementSuggestion(
                    level   = "info",
                    target  = ws.name,
                    message = f"実行時間が長い — timeout_sec の調整、または並列 Step への分割を検討してください",
                    metric  = "avg_ms",
                    value   = ws.avg_ms / 1000,
                ))

        # 未使用 Factory を検出
        try:
            from src.core.kernel import get_kernel
            all_factories = set(get_kernel().registry.list_factories())
            used_factories = {f.factory_id for f in factories}
            unused = all_factories - used_factories
            for fid in sorted(unused):
                suggestions.append(ImprovementSuggestion(
                    level   = "info",
                    target  = fid,
                    message = "まだ一度も実行されていません — Marketplace から関連 Agent を追加することも可能です",
                    metric  = "usage",
                    value   = 0.0,
                ))
        except Exception:
            pass

        return suggestions

    @staticmethod
    def _parse_ts(ts: str) -> datetime:
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.min
