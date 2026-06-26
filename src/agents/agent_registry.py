"""
Agent registry for AI動画工場 v4.0.

Responsibilities:
  - Discover and hold all registered agents.
  - Persist enabled/next_agents state to config/agent_registry.json.
  - Dispatch a task to the correct agent (run_task).
  - Provide dependency-injection via set_next_agents().

Extension points (FUTURE):
  - Remote dispatch: if agent.config["remote"] is set, send task to cloud worker.
  - Hot-reload: watch for new agent modules and re-register without restart.
  - Subscription check: registry.run_task() calls context.can_use(agent.NAME).
"""
from __future__ import annotations

import json
from pathlib import Path

from src.utils.config import PROJECT_ROOT
from src.agents.base_agent import BaseAgent, Task, TaskQueue, TASK_RUNNING

REGISTRY_CONFIG_PATH = PROJECT_ROOT / "config" / "agent_registry.json"


class AgentRegistry:
    """Central registry for all agents.  One instance per application."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.NAME] = agent

    def get(self, name: str) -> BaseAgent | None:
        return self._agents.get(name)

    def list_all(self) -> list[BaseAgent]:
        return list(self._agents.values())

    def names(self) -> list[str]:
        return list(self._agents.keys())

    # ── Enable / Disable ──────────────────────────────────────────────────────

    def enable(self, name: str) -> None:
        if a := self._agents.get(name):
            a.enable()
            self.save_state()

    def disable(self, name: str) -> None:
        if a := self._agents.get(name):
            a.disable()
            self.save_state()

    # ── Dependency injection ───────────────────────────────────────────────────

    def set_next_agents(self, agent_name: str, next_agents: list[str]) -> None:
        if a := self._agents.get(agent_name):
            a.set_next_agents(next_agents)
            self.save_state()

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def run_task(self, task: Task, queue: TaskQueue) -> Task:
        """Find the responsible agent and execute the task."""
        agent = self._agents.get(task.agent)
        if not agent:
            return queue.fail(task.id, f"Unknown agent: {task.agent}")
        if not agent.is_enabled():
            return queue.fail(task.id, f"Agent {task.agent} is disabled")
        queue.update(task.id, status=TASK_RUNNING, progress=0.05)
        try:
            return agent.run(task, queue)
        except Exception as exc:
            return queue.fail(task.id, f"{type(exc).__name__}: {exc}")

    # ── Persistence ───────────────────────────────────────────────────────────

    def save_state(self) -> None:
        state = {
            name: {
                "enabled":     agent.is_enabled(),
                "next_agents": agent.get_next_agents(),
                "config":      agent.config,
            }
            for name, agent in self._agents.items()
        }
        REGISTRY_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        REGISTRY_CONFIG_PATH.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def load_state(self) -> None:
        if not REGISTRY_CONFIG_PATH.exists():
            return
        try:
            state = json.loads(REGISTRY_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return
        for name, cfg in state.items():
            if a := self._agents.get(name):
                if not cfg.get("enabled", True):
                    a.disable()
                if na := cfg.get("next_agents"):
                    a.set_next_agents(na)
                if co := cfg.get("config"):
                    a.config.update(co)

    # ── Stats ─────────────────────────────────────────────────────────────────

    def active_count(self) -> int:
        return sum(1 for a in self._agents.values() if a.is_enabled())

    def health(self) -> dict:
        return {
            "total_agents":  len(self._agents),
            "active_agents": self.active_count(),
            "agents": [a.get_info() for a in self._agents.values()],
        }


# ── Default registry factory ──────────────────────────────────────────────────

def create_default_registry() -> AgentRegistry:
    """Instantiate and register all built-in agents, then load persisted state."""
    from src.agents.producer_agent   import ProducerAgent
    from src.agents.director_agent   import DirectorAgent
    from src.agents.script_agent     import ScriptAgent
    from src.agents.prompt_agent     import PromptAgent
    from src.agents.editor_agent     import EditorAgent
    from src.agents.publisher_agent  import PublisherAgent

    registry = AgentRegistry()
    for cls in [ProducerAgent, DirectorAgent, ScriptAgent, PromptAgent, EditorAgent, PublisherAgent]:
        registry.register(cls())
    registry.load_state()
    return registry
