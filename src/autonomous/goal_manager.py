"""GoalManager — 長期・中期・短期目標を階層管理する。

Goals は data/autonomous/goals.json に永続化される。
Planner が GoalManager から現在の目標を読み取り、次のアクションを決定する。
"""
from __future__ import annotations

import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from src.utils.json_store import save_json_atomic

_GOALS_FILE = Path("data/autonomous/goals.json")
_lock       = threading.Lock()


class GoalLevel:
    LONG  = "long"   # 1ヶ月以上の大方針
    MID   = "mid"    # 1〜4週間の具体目標
    SHORT = "short"  # 1週間以内のタスク

class GoalStatus:
    ACTIVE    = "active"
    COMPLETED = "completed"
    PAUSED    = "paused"
    CANCELLED = "cancelled"


@dataclass
class Goal:
    goal_id:          str
    level:            str            # GoalLevel.*
    title:            str
    description:      str
    status:           str            # GoalStatus.*
    priority:         int            # 1〜10
    parent_id:        Optional[str]  # 親 Goal ID (mid→long, short→mid)
    success_criteria: list[str]
    created_at:       str
    target_date:      Optional[str]  # ISO date
    completion_pct:   float          # 0〜100
    tags:             list[str] = field(default_factory=list)
    notes:            str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Goal":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})

    def is_active(self) -> bool:
        return self.status == GoalStatus.ACTIVE


class GoalManager:
    """
    Goal の CRUD + 階層管理。Singleton ではないが軽量。

    使い方:
        gm = GoalManager()
        g  = gm.add("AIOS を完全自律化する", GoalLevel.LONG, priority=10)
        gm.update_progress(g.goal_id, pct=20)
        active = gm.get_active(level=GoalLevel.SHORT)
    """

    def __init__(self) -> None:
        self._goals: dict[str, Goal] = {}
        self._load()
        if not self._goals:
            self._seed_defaults()

    # ── CRUD ──────────────────────────────────────────────────────

    def add(
        self,
        title:            str,
        level:            str = GoalLevel.SHORT,
        description:      str = "",
        priority:         int = 5,
        parent_id:        Optional[str] = None,
        success_criteria: list[str] | None = None,
        target_date:      Optional[str] = None,
        tags:             list[str] | None = None,
    ) -> Goal:
        g = Goal(
            goal_id          = str(uuid.uuid4())[:8],
            level            = level,
            title            = title,
            description      = description,
            status           = GoalStatus.ACTIVE,
            priority         = priority,
            parent_id        = parent_id,
            success_criteria = success_criteria or [],
            created_at       = datetime.now().isoformat(timespec="seconds"),
            target_date      = target_date,
            completion_pct   = 0.0,
            tags             = tags or [],
        )
        with _lock:
            self._goals[g.goal_id] = g
        self._save()
        return g

    def get(self, goal_id: str) -> Optional[Goal]:
        return self._goals.get(goal_id)

    def list_all(self) -> list[Goal]:
        return sorted(self._goals.values(), key=lambda g: (-g.priority, g.created_at))

    def get_active(self, level: Optional[str] = None) -> list[Goal]:
        goals = [g for g in self._goals.values() if g.is_active()]
        if level:
            goals = [g for g in goals if g.level == level]
        return sorted(goals, key=lambda g: -g.priority)

    def update_progress(self, goal_id: str, pct: float, notes: str = "") -> bool:
        g = self._goals.get(goal_id)
        if not g:
            return False
        g.completion_pct = max(0.0, min(100.0, pct))
        if notes:
            g.notes = notes
        if g.completion_pct >= 100.0:
            g.status = GoalStatus.COMPLETED
        self._save()
        return True

    def complete(self, goal_id: str) -> bool:
        return self.update_progress(goal_id, 100.0)

    def pause(self, goal_id: str) -> bool:
        g = self._goals.get(goal_id)
        if not g:
            return False
        g.status = GoalStatus.PAUSED
        self._save()
        return True

    def cancel(self, goal_id: str) -> bool:
        g = self._goals.get(goal_id)
        if not g:
            return False
        g.status = GoalStatus.CANCELLED
        self._save()
        return True

    def delete(self, goal_id: str) -> bool:
        with _lock:
            if goal_id not in self._goals:
                return False
            del self._goals[goal_id]
        self._save()
        return True

    def update(self, goal_id: str, **kwargs) -> bool:
        """任意フィールドを更新する。"""
        g = self._goals.get(goal_id)
        if not g:
            return False
        allowed = {f for f in Goal.__dataclass_fields__ if f not in ("goal_id", "created_at")}
        for k, v in kwargs.items():
            if k in allowed:
                setattr(g, k, v)
        self._save()
        return True

    def get_children(self, parent_id: str) -> list[Goal]:
        return [g for g in self._goals.values() if g.parent_id == parent_id]

    def hierarchy_summary(self) -> str:
        """人間が読みやすいツリー形式のサマリー。"""
        lines = ["# AIOS Goal Hierarchy\n"]
        for level, label in [(GoalLevel.LONG, "長期"), (GoalLevel.MID, "中期"), (GoalLevel.SHORT, "短期")]:
            goals = self.get_active(level)
            if not goals:
                continue
            lines.append(f"## {label}目標")
            for g in goals:
                lines.append(
                    f"- [{g.completion_pct:.0f}%] **{g.title}** (priority={g.priority})"
                )
                if g.notes:
                    lines.append(f"  > {g.notes}")
            lines.append("")
        return "\n".join(lines)

    # ── Persistence ────────────────────────────────────────────────

    def _save(self) -> None:
        _GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {gid: g.to_dict() for gid, g in self._goals.items()}
        with _lock:
            save_json_atomic(_GOALS_FILE, data)

    def _load(self) -> None:
        if not _GOALS_FILE.exists():
            return
        try:
            data = json.loads(_GOALS_FILE.read_text(encoding="utf-8"))
            self._goals = {gid: Goal.from_dict(gdata) for gid, gdata in data.items()}
        except Exception:
            self._goals = {}

    def _seed_defaults(self) -> None:
        """初回起動時のデフォルト目標を設定する。"""
        long_g = self.add(
            title            = "AIOS を完全自律 AI OS にする",
            level            = GoalLevel.LONG,
            description      = "人間の介入なしに自己改善・自己成長できる AI OS を実現する",
            priority         = 10,
            success_criteria = [
                "自律改善サイクルが1日1回以上自動実行される",
                "成功率 95% 以上の Workflow が全体の 80% 以上",
                "未使用 Factory がゼロになる",
            ],
            tags             = ["core", "autonomous"],
        )
        mid_g = self.add(
            title            = "全 Factory の成功率を 90% 以上にする",
            level            = GoalLevel.MID,
            description      = "低成功率 Workflow を特定し改善パッチを生成・適用する",
            priority         = 8,
            parent_id        = long_g.goal_id,
            success_criteria = ["成功率 < 90% の Workflow がゼロ"],
            tags             = ["quality"],
        )
        self.add(
            title     = "Improvement Engine を毎日自動実行する",
            level     = GoalLevel.SHORT,
            priority  = 7,
            parent_id = mid_g.goal_id,
            tags      = ["automation"],
        )
        self.add(
            title     = "未使用 Factory のデモ Workflow を作成する",
            level     = GoalLevel.SHORT,
            priority  = 5,
            parent_id = mid_g.goal_id,
            tags      = ["coverage"],
        )


# Singleton-like helper
_gm_instance: Optional[GoalManager] = None
_gm_lock = threading.Lock()

def get_goal_manager() -> GoalManager:
    global _gm_instance
    if _gm_instance is None:
        with _gm_lock:
            if _gm_instance is None:
                _gm_instance = GoalManager()
    return _gm_instance

