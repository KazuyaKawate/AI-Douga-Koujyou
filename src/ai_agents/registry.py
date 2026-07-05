"""AgentRegistry — AIOS Agent の中央レジストリ。

from src.utils.json_store import save_json_atomic
- シングルトン (get_agent_registry())
- data/agents/*.json から自動ロード
- src/orchestrator/factories/*/agents/*.json からも自動ロード
- 1000+ Agent 対応（インメモリ dict インデックス）
- enable/disable / import/export / version 管理

Factory・Kernel・Router から独立したモジュール。
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from .definition import AgentDefinition

_DATA_DIR = Path("data/agents")
_FACTORY_BASE = Path("src/orchestrator/factories")

_lock: threading.Lock = threading.Lock()
_instance: Optional["AgentRegistry"] = None


class AgentRegistry:
    """
    Agent の中央レジストリ。

    auto_load() で以下を探索:
        1. data/agents/*.json          ← グローバル Agent
        2. src/orchestrator/factories/*/agents/*.json  ← Factory 付属 Agent
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}

    # ---- CRUD -------------------------------------------------------

    def register(self, agent: AgentDefinition, overwrite: bool = True) -> None:
        """Agent を登録する。overwrite=False で既存エントリを保護。"""
        if not overwrite and agent.agent_id in self._agents:
            return
        self._agents[agent.agent_id] = agent

    def get(self, agent_id: str) -> Optional[AgentDefinition]:
        return self._agents.get(agent_id)

    def delete(self, agent_id: str) -> bool:
        if agent_id not in self._agents:
            return False
        del self._agents[agent_id]
        _agent_file(agent_id).unlink(missing_ok=True)
        return True

    # ---- Query ------------------------------------------------------

    def list_all(
        self,
        enabled_only: bool = False,
        factory_id: Optional[str] = None,
        tag: Optional[str] = None,
        role: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> list[AgentDefinition]:
        """フィルタ条件を組み合わせて Agent リストを返す。"""
        results = list(self._agents.values())
        if enabled_only:
            results = [a for a in results if a.enabled]
        if factory_id is not None:
            results = [a for a in results if a.factory_id == factory_id]
        if tag is not None:
            results = [a for a in results if tag in a.tags]
        if role is not None:
            results = [a for a in results if a.role == role]
        if task_type is not None:
            results = [a for a in results if a.task_type == task_type]
        return sorted(results, key=lambda a: a.agent_id)

    def count(self, enabled_only: bool = False) -> int:
        if enabled_only:
            return sum(1 for a in self._agents.values() if a.enabled)
        return len(self._agents)

    def exists(self, agent_id: str) -> bool:
        return agent_id in self._agents

    # ---- Enable / Disable -------------------------------------------

    def enable(self, agent_id: str) -> None:
        agent = self._require(agent_id)
        agent.enabled = True
        agent.updated_at = _now()
        self.save(agent)

    def disable(self, agent_id: str) -> None:
        agent = self._require(agent_id)
        agent.enabled = False
        agent.updated_at = _now()
        self.save(agent)

    # ---- Version Management -----------------------------------------

    def update_version(
        self,
        agent_id: str,
        changes: dict,
        version_level: str = "patch",
    ) -> AgentDefinition:
        """
        Agent を更新し、変更前のバージョンを version_history に保存する。

        changes: to_dict() に渡すフィールド名 → 新しい値 の dict。
        version_level: "major" / "minor" / "patch"
        """
        agent = self._require(agent_id)

        # 現在の状態を history に保存
        agent.version_history.append({
            "version":    agent.version,
            "snapshot":   agent.to_dict(),
            "archived_at": _now(),
        })

        # フィールド更新
        for key, val in changes.items():
            if key == "config" and isinstance(val, dict):
                from .definition import AgentConfig
                agent.config = AgentConfig.from_dict(val)
            elif hasattr(agent, key) and key not in ("agent_id", "created_at", "version_history"):
                setattr(agent, key, val)

        agent.version    = agent.bump_version(version_level)
        agent.updated_at = _now()
        self.save(agent)
        return agent

    def rollback(self, agent_id: str, version: str) -> AgentDefinition:
        """指定バージョンにロールバックする。現在状態は history に保存される。"""
        agent = self._require(agent_id)
        snapshot = next(
            (h["snapshot"] for h in agent.version_history if h["version"] == version),
            None,
        )
        if snapshot is None:
            raise ValueError(f"Version {version!r} not found in history for {agent_id!r}")

        # 現在を history に退避してからロールバック
        agent.version_history.append({
            "version":    agent.version,
            "snapshot":   agent.to_dict(),
            "archived_at": _now(),
        })

        restored = AgentDefinition.from_dict(snapshot)
        restored.version_history = agent.version_history
        restored.updated_at      = _now()
        self._agents[agent_id]   = restored
        self.save(restored)
        return restored

    # ---- Import / Export --------------------------------------------

    def export_json(self, agent_id: str) -> str:
        return self._require(agent_id).to_json()

    def import_json(self, json_str: str, overwrite: bool = True) -> AgentDefinition:
        agent = AgentDefinition.from_json(json_str)
        self.register(agent, overwrite=overwrite)
        self.save(agent)
        return agent

    def export_all(self, enabled_only: bool = False) -> str:
        agents = self.list_all(enabled_only=enabled_only)
        return json.dumps([a.to_dict() for a in agents], ensure_ascii=False, indent=2)

    def import_all_json(self, json_str: str, overwrite: bool = True) -> int:
        items = json.loads(json_str)
        if isinstance(items, dict):
            items = [items]
        count = 0
        for item in items:
            agent = AgentDefinition.from_dict(item)
            self.register(agent, overwrite=overwrite)
            self.save(agent)
            count += 1
        return count

    # ---- Persistence ------------------------------------------------

    def save(self, agent: AgentDefinition) -> None:
        """Agent を data/agents/{agent_id}.json に保存する。"""
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        save_json_atomic(_agent_file(agent.agent_id), agent.to_dict())

    def auto_load(self) -> int:
        """data/agents/ と factories/*/agents/ から Agent を一括ロードする。"""
        count = 0
        count += self._load_from_dir(_DATA_DIR, overwrite=False)
        if _FACTORY_BASE.exists():
            for factory_dir in sorted(_FACTORY_BASE.iterdir()):
                if factory_dir.is_dir() and not factory_dir.name.startswith("_"):
                    agents_dir = factory_dir / "agents"
                    count += self._load_from_dir(agents_dir, overwrite=False)
        return count

    def _load_from_dir(self, directory: Path, overwrite: bool = False) -> int:
        if not directory.exists():
            return 0
        count = 0
        for f in sorted(directory.glob("*.json")):
            if f.name.startswith("_"):
                continue
            try:
                agent = AgentDefinition.from_dict(
                    json.loads(f.read_text(encoding="utf-8"))
                )
                self.register(agent, overwrite=overwrite)
                count += 1
            except Exception:
                continue
        return count

    # ---- Internal ---------------------------------------------------

    def _require(self, agent_id: str) -> AgentDefinition:
        agent = self._agents.get(agent_id)
        if agent is None:
            raise KeyError(f"Agent not found: {agent_id!r}")
        return agent


# ---- Module-level singleton helpers ---------------------------------

def get_agent_registry() -> AgentRegistry:
    """シングルトンの AgentRegistry を返す。初回呼び出し時に auto_load() を実行。"""
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = AgentRegistry()
                _instance.auto_load()
    return _instance


def reset_agent_registry() -> None:
    """テスト・再起動用。次回 get_agent_registry() で再初期化される。"""
    global _instance
    with _lock:
        _instance = None


# ---- Private helpers -----------------------------------------------

def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _agent_file(agent_id: str) -> Path:
    return _DATA_DIR / f"{agent_id}.json"
