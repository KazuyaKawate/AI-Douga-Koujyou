"""src.autonomous — AIOS 自律改善パッケージ。

Components:
    ImprovementEngine  — 実行データ分析・改善候補生成
    GoalManager        — 長期/中期/短期目標管理
    Planner            — Goal + 候補 → 次アクション決定
    AutonomousQueue    — 改善タスクキュー
    SafeMode           — Branch/Patch/Review/Approve/Merge フロー
    run_improvement_cycle() — 一括実行ヘルパー
"""
from src.autonomous.improvement_engine import ImprovementEngine, ImprovementCandidate
from src.autonomous.goal_manager import GoalManager, GoalLevel, GoalStatus, get_goal_manager
from src.autonomous.planner import Planner, PlannedAction, ActionType
from src.autonomous.queue_manager import (
    AutonomousQueue, ImprovementTask, TaskStatus, get_autonomous_queue,
)
from src.autonomous.safe_mode import SafeMode, PatchResult, ReviewResult, MergeResult

__all__ = [
    "ImprovementEngine", "ImprovementCandidate",
    "GoalManager", "GoalLevel", "GoalStatus", "get_goal_manager",
    "Planner", "PlannedAction", "ActionType",
    "AutonomousQueue", "ImprovementTask", "TaskStatus", "get_autonomous_queue",
    "SafeMode", "PatchResult", "ReviewResult", "MergeResult",
    "run_improvement_cycle",
]


def run_improvement_cycle(
    period_days:   int  = 30,
    max_actions:   int  = 5,
    auto_approve:  bool = False,
    dry_run:       bool = True,
) -> dict:
    """
    AIOS 自律改善サイクルを1回実行する。

    Steps:
      1. ImprovementEngine で分析
      2. Planner で次アクションを決定
      3. AutonomousQueue に登録
      4. dry_run=False なら SafeMode で Patch 生成

    Args:
        period_days : 分析対象の日数
        max_actions : 生成するアクション数の上限
        auto_approve: AI スコアが AUTO_APPROVE_SCORE 以上なら自動承認
        dry_run     : True = キュー登録のみ (Patch 生成しない)

    Returns:
        cycle_result dict
    """
    from src.autonomous.safe_mode import AUTO_APPROVE_SCORE

    result: dict = {
        "started_at"  : __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "period_days" : period_days,
        "dry_run"     : dry_run,
    }

    # ── Step 1: 分析 ──────────────────────────────────────────────
    engine     = ImprovementEngine()
    candidates = engine.analyze(period_days)
    result["candidates"] = len(candidates)

    # ── Step 2: 計画 ──────────────────────────────────────────────
    gm      = get_goal_manager()
    goals   = gm.get_active()
    planner = Planner()
    actions = planner.plan_next_actions(candidates, goals, max_actions)
    result["planned_actions"] = len(actions)

    # ── Step 3: キュー登録 ────────────────────────────────────────
    queue    = get_autonomous_queue()
    task_ids = []
    for action in actions:
        task = queue.enqueue(
            title           = action.title,
            task_type       = action.action_type,
            workflow_to_run = action.workflow_hint,
            target          = action.target,
            description     = action.description,
            priority        = max(1, min(10, int(action.priority * 10))),
            context         = action.context_hint,
            source          = "planner",
        )
        task_ids.append(task.task_id)
    result["enqueued_tasks"] = task_ids

    # ── Step 4: Patch 生成 (dry_run=False のみ) ───────────────────
    if not dry_run and task_ids:
        sm            = SafeMode(queue)
        patch_results = []
        for tid in task_ids[:1]:   # 最初の1件だけ実行（過負荷防止）
            task    = queue.get(tid)
            cycle   = sm.run_full_cycle(task, auto_approve=auto_approve)
            patch_results.append(cycle)
        result["patch_results"] = patch_results

    result["finished_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    return result
