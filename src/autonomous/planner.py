"""Planner — Goal + ImprovementCandidate → 次のアクションを決定する。

AI (Router) が現在の目標・メトリクス・改善候補を統合的に判断し、
「次に作る Factory / 改善する Agent / 追加する Workflow」を決定する。
判断結果は AutonomousQueue に登録するタスクとして返す。
"""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.autonomous.improvement_engine import ImprovementCandidate
    from src.autonomous.goal_manager import Goal


class ActionType:
    FIX_WORKFLOW     = "fix_workflow"      # 既存 Workflow を修正
    FIX_AGENT        = "fix_agent"         # 既存 Agent プロンプト修正
    ADD_WORKFLOW     = "add_workflow"      # 新規 Workflow 作成
    ADD_FACTORY      = "add_factory"       # 新規 Factory 作成
    REFACTOR         = "refactor"          # コードリファクタリング
    DEMO_SCHEDULE    = "demo_schedule"     # 未使用 Factory のデモ実行
    CUSTOM           = "custom"            # AI が自由提案


@dataclass
class PlannedAction:
    action_id:    str
    action_type:  str          # ActionType.*
    title:        str
    description:  str
    target:       str          # workflow_name / agent_id / factory_id
    priority:     float        # 0.0〜1.0
    workflow_hint:str          # 実行すべき dev.* / autonomous.* workflow
    context_hint: dict         # そのまま workflow の context に渡せるヒント
    goal_ids:     list[str]    # 関連する Goal ID
    candidate_ids:list[str]    # 根拠となる ImprovementCandidate ID
    reasoning:    str          # Planner が採用した理由
    created_at:   str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))

    def to_dict(self) -> dict:
        return asdict(self)


class Planner:
    """
    Goal + ImprovementCandidate を受け取り、次のアクション一覧を返す。

    使い方:
        planner = Planner()
        actions = planner.plan_next_actions(candidates, goals, max_actions=5)
        for a in actions:
            print(a.priority, a.title)
    """

    def plan_next_actions(
        self,
        candidates: list["ImprovementCandidate"],
        goals:      list["Goal"],
        max_actions: int = 5,
    ) -> list[PlannedAction]:
        """
        AI に計画を依頼し、優先順位付きの PlannedAction リストを返す。
        AI が使えない場合はルールベースのフォールバックを使う。
        """
        # AI に計画を依頼
        actions = self._ai_plan(candidates, goals, max_actions)
        if not actions:
            actions = self._rule_based_plan(candidates, goals, max_actions)

        actions.sort(key=lambda a: a.priority, reverse=True)
        return actions[:max_actions]

    # ── AI ベース計画 ──────────────────────────────────────────────

    def _ai_plan(
        self,
        candidates: list["ImprovementCandidate"],
        goals:      list["Goal"],
        max_actions: int,
    ) -> list[PlannedAction]:
        try:
            from src.ai.router import get_router
            from src.ai.task import AITask, TaskType

            goals_txt = "\n".join(
                f"- [{g.level}] {g.title} (priority={g.priority}, {g.completion_pct:.0f}%完了)"
                for g in goals[:8]
            ) or "(目標未設定)"

            cands_txt = "\n".join(
                f"- [{c.priority:.1f}] {c.title}: {c.suggestion}"
                for c in candidates[:8]
            ) or "(改善候補なし)"

            prompt = (
                "あなたは AIOS の自律改善プランナーです。\n\n"
                f"## 現在の目標\n{goals_txt}\n\n"
                f"## 改善候補\n{cands_txt}\n\n"
                f"上記を踏まえ、今すぐ実行すべき改善アクションを最大 {max_actions} 件、"
                "優先度順に JSON 配列で提案してください。\n"
                "形式:\n"
                """[
  {
    "action_type": "fix_workflow",
    "title": "xxx の成功率を改善",
    "description": "詳細説明",
    "target": "workflow_name",
    "priority": 0.9,
    "workflow_hint": "dev.fix_bug",
    "context_hint": {"instruction": "...", "target_file": "..."},
    "reasoning": "採用理由"
  }
]"""
                "\naction_type は: fix_workflow / fix_agent / add_workflow / add_factory / refactor / demo_schedule / custom\n"
                "JSON 配列のみ出力。"
            )

            task = AITask(task_type=TaskType.DEFAULT, prompt=prompt)
            resp = get_router().route(task)
            if not (resp and resp.ok):
                return []

            match = re.search(r"\[.*?\]", resp.content, re.DOTALL)
            if not match:
                return []
            items = json.loads(match.group())

            actions = []
            for item in items[:max_actions]:
                actions.append(PlannedAction(
                    action_id    = str(uuid.uuid4())[:8],
                    action_type  = item.get("action_type", ActionType.CUSTOM),
                    title        = item.get("title", ""),
                    description  = item.get("description", ""),
                    target       = item.get("target", ""),
                    priority     = float(item.get("priority", 0.5)),
                    workflow_hint= item.get("workflow_hint", "dev.implement_plan"),
                    context_hint = item.get("context_hint", {}),
                    goal_ids     = [],
                    candidate_ids= [],
                    reasoning    = item.get("reasoning", "AI 提案"),
                ))
            return actions

        except Exception:
            return []

    # ── ルールベースフォールバック ─────────────────────────────────

    def _rule_based_plan(
        self,
        candidates: list["ImprovementCandidate"],
        goals:      list["Goal"],
        max_actions: int,
    ) -> list[PlannedAction]:
        actions = []

        # 1. 低成功率 Workflow を最優先
        for c in candidates:
            if c.issue_type == "low_success_rate":
                actions.append(PlannedAction(
                    action_id    = str(uuid.uuid4())[:8],
                    action_type  = ActionType.FIX_WORKFLOW,
                    title        = f"修正: {c.target_id}",
                    description  = c.description,
                    target       = c.target_id,
                    priority     = c.priority,
                    workflow_hint= c.workflow_hint,
                    context_hint = {
                        "instruction": f"成功率を改善してください。{c.suggestion}",
                        "target_file" : f"src/orchestrator/factories/{c.target_id.split('.')[0]}/workflows/{c.target_id.split('.')[-1]}.json",
                    },
                    goal_ids      = [],
                    candidate_ids = [c.candidate_id],
                    reasoning     = f"成功率 {c.evidence.get('success_rate', '?')}% が閾値以下",
                ))

        # 2. 未使用 Factory のデモ
        for c in candidates:
            if c.issue_type == "unused":
                actions.append(PlannedAction(
                    action_id    = str(uuid.uuid4())[:8],
                    action_type  = ActionType.DEMO_SCHEDULE,
                    title        = f"デモ実行登録: {c.target_id}",
                    description  = c.description,
                    target       = c.target_id,
                    priority     = c.priority,
                    workflow_hint= "composer.compose_workflow",
                    context_hint = {"goal": f"{c.target_id} factory の活用 Workflow を作成"},
                    goal_ids      = [],
                    candidate_ids = [c.candidate_id],
                    reasoning     = "未使用 Factory の活用促進",
                ))

        # 3. 短期 Goal に紐づくアクション
        from src.autonomous.goal_manager import GoalLevel
        short_goals = [g for g in goals if g.level == GoalLevel.SHORT and g.is_active()]
        for g in short_goals[:2]:
            actions.append(PlannedAction(
                action_id    = str(uuid.uuid4())[:8],
                action_type  = ActionType.CUSTOM,
                title        = f"Goal 達成: {g.title}",
                description  = g.description,
                target       = "aios",
                priority     = g.priority / 10.0,
                workflow_hint= "dev.implement_plan",
                context_hint = {"instruction": g.title},
                goal_ids      = [g.goal_id],
                candidate_ids = [],
                reasoning     = f"短期 Goal priority={g.priority}",
            ))

        return actions

