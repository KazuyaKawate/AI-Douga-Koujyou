"""
Base primitives for AI動画工場 v4.0 multi-agent architecture.

Design principles:
  - Tasks are the ONLY communication channel between agents (no direct calls).
  - All state is serialised to project/tasks/*.json (survive restarts).
  - Agents are stateless workers; TaskQueue holds all mutable state.
  - NEXT_AGENTS is injectable at runtime via AgentRegistry (dependency injection).
  - To replace an agent: subclass BaseAgent with the same NAME, re-register.
  - To route differently: call registry.set_next_agents("A", ["B", "C"]).

Extension points (FUTURE):
  - Cloud execution: override _remote_run() + dispatch there from run().
  - Subscription gating: check context.can_use(agent.NAME) before dispatch.
  - Parallel fan-out: TaskQueue.create_many() for multi-branch pipelines.
  - Streaming progress: update task.progress incrementally inside run().
"""
from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from src.utils.config import PROJECT_ROOT

# ── Task status constants ──────────────────────────────────────────────────────

TASK_PENDING = "pending"
TASK_RUNNING = "running"
TASK_DONE    = "done"
TASK_FAILED  = "failed"
TASK_SKIPPED = "skipped"
TASK_WAITING = "waiting"

ALL_STATUSES = [TASK_PENDING, TASK_RUNNING, TASK_DONE, TASK_FAILED, TASK_SKIPPED, TASK_WAITING]

STATUS_LABELS = {
    TASK_PENDING: "⏳ 待機中",
    TASK_RUNNING: "🔄 実行中",
    TASK_DONE:    "✅ 完了",
    TASK_FAILED:  "❌ 失敗",
    TASK_SKIPPED: "⏭️ スキップ",
    TASK_WAITING: "⏸️ 依存待ち",
}

TASKS_DIR = PROJECT_ROOT / "project" / "tasks"


# ── Task ──────────────────────────────────────────────────────────────────────

class Task:
    """Immutable-in-spirit record that flows through the pipeline."""

    __slots__ = (
        "id", "agent", "status", "input", "output", "error",
        "created", "updated", "pipeline_id", "depends_on",
        "progress", "label",
    )

    def __init__(
        self,
        id: str,
        agent: str,
        status: str           = TASK_PENDING,
        input: dict           = None,
        output: dict          = None,
        error: str            = "",
        created: str          = "",
        updated: str          = "",
        pipeline_id: str      = "",
        depends_on: list[str] = None,
        progress: float       = 0.0,
        label: str            = "",
    ) -> None:
        self.id          = id
        self.agent       = agent
        self.status      = status
        self.input       = input  or {}
        self.output      = output or {}
        self.error       = error
        self.created     = created or datetime.now().isoformat()
        self.updated     = updated or self.created
        self.pipeline_id = pipeline_id
        self.depends_on  = depends_on or []
        self.progress    = progress
        self.label       = label

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "agent":       self.agent,
            "status":      self.status,
            "input":       self.input,
            "output":      self.output,
            "error":       self.error,
            "created":     self.created,
            "updated":     self.updated,
            "pipeline_id": self.pipeline_id,
            "depends_on":  self.depends_on,
            "progress":    self.progress,
            "label":       self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Task":
        return cls(
            id          = d.get("id", ""),
            agent       = d.get("agent", ""),
            status      = d.get("status", TASK_PENDING),
            input       = d.get("input",  {}),
            output      = d.get("output", {}),
            error       = d.get("error",  ""),
            created     = d.get("created", ""),
            updated     = d.get("updated", ""),
            pipeline_id = d.get("pipeline_id", ""),
            depends_on  = d.get("depends_on", []),
            progress    = d.get("progress", 0.0),
            label       = d.get("label", ""),
        )

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, agent={self.agent!r}, status={self.status!r})"


# ── TaskQueue ─────────────────────────────────────────────────────────────────

class TaskQueue:
    """File-backed task queue.  Each task = one JSON file in TASKS_DIR."""

    def __init__(self, tasks_dir: Path | None = None) -> None:
        self.tasks_dir = tasks_dir or TASKS_DIR
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(
        self,
        agent:       str,
        input_data:  dict,
        pipeline_id: str       = "",
        depends_on:  list[str] = None,
        label:       str       = "",
    ) -> Task:
        task = Task(
            id          = f"task_{uuid.uuid4().hex[:10]}",
            agent       = agent,
            input       = input_data,
            pipeline_id = pipeline_id,
            depends_on  = depends_on or [],
            label       = label or agent,
        )
        self._save(task)
        return task

    def get(self, task_id: str) -> Task | None:
        p = self.tasks_dir / f"{task_id}.json"
        if not p.exists():
            return None
        try:
            return Task.from_dict(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            return None

    def update(self, task_id: str, **kwargs) -> Task | None:
        task = self.get(task_id)
        if task is None:
            return None
        for k, v in kwargs.items():
            if hasattr(task, k):
                setattr(task, k, v)
        task.updated = datetime.now().isoformat()
        self._save(task)
        return task

    def complete(self, task_id: str, output: dict) -> Task | None:
        return self.update(task_id, status=TASK_DONE, output=output, progress=1.0)

    def fail(self, task_id: str, error: str) -> Task | None:
        return self.update(task_id, status=TASK_FAILED, error=error)

    def delete(self, task_id: str) -> bool:
        p = self.tasks_dir / f"{task_id}.json"
        try:
            p.unlink(missing_ok=True)
            return True
        except Exception:
            return False

    # ── Queries ───────────────────────────────────────────────────────────────

    def list_all(
        self,
        pipeline_id: str | None = None,
        agent:       str | None = None,
        status:      str | None = None,
    ) -> list[Task]:
        tasks: list[Task] = []
        for p in sorted(self.tasks_dir.glob("task_*.json")):
            try:
                t = Task.from_dict(json.loads(p.read_text(encoding="utf-8")))
                if pipeline_id and t.pipeline_id != pipeline_id:
                    continue
                if agent and t.agent != agent:
                    continue
                if status and t.status != status:
                    continue
                tasks.append(t)
            except Exception:
                pass
        tasks.sort(key=lambda t: t.created, reverse=True)
        return tasks

    def list_pending(self, agent: str | None = None) -> list[Task]:
        return self.list_all(agent=agent, status=TASK_PENDING)

    def clear_completed(self) -> int:
        count = 0
        for t in self.list_all(status=TASK_DONE):
            if self.delete(t.id):
                count += 1
        return count

    # ── Statistics ────────────────────────────────────────────────────────────

    def stats(self) -> dict:
        all_tasks = self.list_all()
        by_status = {s: 0 for s in ALL_STATUSES}
        total_ms  = 0.0
        counted   = 0
        for t in all_tasks:
            by_status[t.status] = by_status.get(t.status, 0) + 1
            if t.status == TASK_DONE and t.created and t.updated:
                try:
                    dt = (
                        datetime.fromisoformat(t.updated) - datetime.fromisoformat(t.created)
                    ).total_seconds()
                    total_ms += dt
                    counted  += 1
                except Exception:
                    pass
        return {
            "total":    len(all_tasks),
            "by_status": by_status,
            "avg_seconds": (total_ms / counted) if counted else 0.0,
        }

    def _save(self, task: Task) -> None:
        p = self.tasks_dir / f"{task.id}.json"
        p.write_text(json.dumps(task.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


# ── BaseAgent ─────────────────────────────────────────────────────────────────

class BaseAgent(ABC):
    """
    Abstract base for all production agents.

    Subclasses MUST define:
      NAME        — unique string identifier (used in task.agent)
      ROLE        — one-line Japanese description
      run()       — execute the task; call queue.complete() or queue.fail()

    Subclasses SHOULD define:
      ICON        — emoji for the UI
      NEXT_AGENTS — default downstream pipeline (injectable)
      DESCRIPTION — longer description shown in the studio UI
    """

    NAME:        str       = ""
    ROLE:        str       = ""
    ICON:        str       = "🤖"
    VERSION:     str       = "1.0"
    NEXT_AGENTS: list[str] = []
    DESCRIPTION: str       = ""

    def __init__(self, config: dict | None = None) -> None:
        self.config       = config or {}
        self._enabled     = True
        self._next_agents = list(self.NEXT_AGENTS)

    # ── DI hook ───────────────────────────────────────────────────────────────

    def set_next_agents(self, agents: list[str]) -> None:
        """Inject a different downstream routing at runtime."""
        self._next_agents = list(agents)

    def get_next_agents(self) -> list[str]:
        return list(self._next_agents)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def enable(self)  -> None: self._enabled = True
    def disable(self) -> None: self._enabled = False

    def is_enabled(self) -> bool:
        return self._enabled

    def can_handle(self, task: Task) -> bool:
        return task.agent == self.NAME

    # ── Abstract ──────────────────────────────────────────────────────────────

    @abstractmethod
    def run(self, task: Task, queue: TaskQueue) -> Task:
        """
        Execute the task.  Implementations MUST:
          1. Call queue.update(task.id, status=TASK_RUNNING) if not done externally.
          2. Call queue.complete(task.id, output) on success.
          3. Call queue.fail(task.id, error) on failure.
          4. Create next-stage tasks via queue.create(...) before returning.
          5. Return the updated Task object.
        """
        ...

    # ── Introspection ─────────────────────────────────────────────────────────

    def get_info(self) -> dict:
        return {
            "name":        self.NAME,
            "role":        self.ROLE,
            "icon":        self.ICON,
            "version":     self.VERSION,
            "enabled":     self._enabled,
            "next_agents": self._next_agents,
            "description": self.DESCRIPTION,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(enabled={self._enabled})"
