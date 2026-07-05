"""AgentDefinition — AIOS Agent の静的定義モデル。

Agent は Factory・Kernel・Router と独立した存在です。
AgentRegistry に登録され、Workflow の ai_task ステップや
直接呼び出しから参照されます。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentConfig:
    """Agent の実行パラメータ。Router の設定を Agent 単位で上書きできる。"""

    provider_hint: str | None = None  # None = Router が自動選択
    max_tokens: int = 2048
    temperature: float = 0.7
    timeout_sec: int = 60
    retry_max: int = 1

    def to_dict(self) -> dict:
        return {
            "provider_hint": self.provider_hint,
            "max_tokens":    self.max_tokens,
            "temperature":   self.temperature,
            "timeout_sec":   self.timeout_sec,
            "retry_max":     self.retry_max,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AgentConfig":
        return cls(
            provider_hint=d.get("provider_hint"),
            max_tokens=int(d.get("max_tokens", 2048)),
            temperature=float(d.get("temperature", 0.7)),
            timeout_sec=int(d.get("timeout_sec", 60)),
            retry_max=int(d.get("retry_max", 1)),
        )


@dataclass
class AgentDefinition:
    """
    AIOS Agent の静的定義。

    - Factory とは独立（factory_id は所属情報のみ、依存ではない）
    - version_history で変更履歴を保持
    - JSON でシリアライズ可能（import/export 対応）
    - enabled フラグで無効化できる（削除せずに停止）

    Workflow の ai_task ステップで `agent_id` を指定すると、
    この Agent の system_prompt と config が適用される。
    """

    agent_id:        str
    name:            str
    version:         str                = "1.0.0"
    description:     str                = ""
    role:            str                = "general"
    capabilities:    list[str]          = field(default_factory=list)
    task_type:       str                = "default"
    system_prompt:   str                = ""
    config:          AgentConfig        = field(default_factory=AgentConfig)
    tags:            list[str]          = field(default_factory=list)
    enabled:         bool               = True
    factory_id:      str | None         = None
    created_at:      str                = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    updated_at:      str                = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    version_history: list[dict]         = field(default_factory=list)

    # ---- Serialization ----------------------------------------------

    def to_dict(self) -> dict:
        return {
            "agent_id":        self.agent_id,
            "name":            self.name,
            "version":         self.version,
            "description":     self.description,
            "role":            self.role,
            "capabilities":    list(self.capabilities),
            "task_type":       self.task_type,
            "system_prompt":   self.system_prompt,
            "config":          self.config.to_dict(),
            "tags":            list(self.tags),
            "enabled":         self.enabled,
            "factory_id":      self.factory_id,
            "created_at":      self.created_at,
            "updated_at":      self.updated_at,
            "version_history": list(self.version_history),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AgentDefinition":
        now = datetime.now().isoformat(timespec="seconds")
        return cls(
            agent_id=d["agent_id"],
            name=d.get("name", d["agent_id"]),
            version=d.get("version", "1.0.0"),
            description=d.get("description", ""),
            role=d.get("role", "general"),
            capabilities=list(d.get("capabilities", [])),
            task_type=d.get("task_type", "default"),
            system_prompt=d.get("system_prompt", ""),
            config=AgentConfig.from_dict(d.get("config", {})),
            tags=list(d.get("tags", [])),
            enabled=bool(d.get("enabled", True)),
            factory_id=d.get("factory_id"),
            created_at=d.get("created_at", now),
            updated_at=d.get("updated_at", now),
            version_history=list(d.get("version_history", [])),
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentDefinition":
        return cls.from_dict(json.loads(json_str))

    # ---- Helpers ----------------------------------------------------

    def bump_version(self, level: str = "patch") -> str:
        """バージョンを上げて新しいバージョン文字列を返す。"""
        parts = [int(x) for x in self.version.split(".")]
        while len(parts) < 3:
            parts.append(0)
        if level == "major":
            parts = [parts[0] + 1, 0, 0]
        elif level == "minor":
            parts = [parts[0], parts[1] + 1, 0]
        else:
            parts = [parts[0], parts[1], parts[2] + 1]
        return ".".join(str(p) for p in parts)
