"""PackageManifest — .apagent パッケージのメタデータ定義。"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PackageManifest:
    """
    .apagent パッケージのマニフェスト。

    manifest.json として .apagent ZIP の中に同梱される。
    """

    package_id:       str
    name:             str
    version:          str             = "1.0.0"
    author:           str             = "unknown"
    description:      str             = ""
    agent_id:         str             = ""
    workflow_name:    str | None      = None
    has_template:     bool            = False
    has_icon:         bool            = False
    tags:             list[str]       = field(default_factory=list)
    aios_min_version: str             = "1.0.0"
    created_at:       str             = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    checksum:         str | None      = None   # SHA256 of agent.json

    # ---- Serialization ----------------------------------------------

    def to_dict(self) -> dict:
        return {
            "package_id":       self.package_id,
            "name":             self.name,
            "version":          self.version,
            "author":           self.author,
            "description":      self.description,
            "agent_id":         self.agent_id,
            "workflow_name":    self.workflow_name,
            "has_template":     self.has_template,
            "has_icon":         self.has_icon,
            "tags":             list(self.tags),
            "aios_min_version": self.aios_min_version,
            "created_at":       self.created_at,
            "checksum":         self.checksum,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def from_dict(cls, d: dict) -> "PackageManifest":
        return cls(
            package_id=d["package_id"],
            name=d.get("name", d["package_id"]),
            version=d.get("version", "1.0.0"),
            author=d.get("author", "unknown"),
            description=d.get("description", ""),
            agent_id=d.get("agent_id", ""),
            workflow_name=d.get("workflow_name"),
            has_template=bool(d.get("has_template", False)),
            has_icon=bool(d.get("has_icon", False)),
            tags=list(d.get("tags", [])),
            aios_min_version=d.get("aios_min_version", "1.0.0"),
            created_at=d.get("created_at", datetime.now().isoformat(timespec="seconds")),
            checksum=d.get("checksum"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "PackageManifest":
        return cls.from_dict(json.loads(json_str))

    # ---- Helpers ----------------------------------------------------

    @staticmethod
    def compute_checksum(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def verify_checksum(self, agent_json: str) -> bool:
        if self.checksum is None:
            return True
        return self.compute_checksum(agent_json) == self.checksum

    def package_filename(self) -> str:
        safe_id = self.package_id.replace("/", "_").replace(" ", "_")
        safe_ver = self.version.replace(".", "_")
        return f"{safe_id}_v{safe_ver}.apagent"
