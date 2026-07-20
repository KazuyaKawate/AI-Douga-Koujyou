from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


def deterministic_id(prefix: str, payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{prefix}-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


class KnowledgeCategory(str, Enum):
    ECOMMERCE = "ecommerce"
    AFFILIATE = "affiliate"
    MARKETING = "marketing"
    BUSINESS = "business"
    TECHNOLOGY = "technology"
    UNCATEGORIZED = "uncategorized"


@dataclass(frozen=True)
class SafetyFields:
    execute_allowed: bool = False
    approval_required: bool = True
    review_required: bool = True
    dry_run: bool = True
    production_actions_enabled: bool = False
    external_request_sent: bool = False

    def _validate_safety(self) -> None:
        if (self.execute_allowed or not self.approval_required or not self.review_required
                or not self.dry_run or self.production_actions_enabled or self.external_request_sent):
            raise ValueError("Knowledge objects must retain the Phase 118 safety defaults.")

    def to_dict(self) -> dict[str, Any]:
        self._validate_safety()
        return asdict(self)


@dataclass(frozen=True)
class KnowledgeTag(SafetyFields):
    name: str = ""
    tag_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        name = self.name.strip().lower()
        if not name:
            raise ValueError("Knowledge tag name is required.")
        data["name"] = name
        data["tag_id"] = self.tag_id or deterministic_id("ktag", {"name": name})
        return data


@dataclass(frozen=True)
class KnowledgeSource(SafetyFields):
    name: str = ""
    source_type: str = "metadata"
    uri: str = ""
    publisher: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    source_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        payload = {"name": self.name.strip(), "source_type": self.source_type.strip().lower(),
                   "uri": self.uri.strip(), "publisher": self.publisher.strip(), "metadata": self.metadata}
        if not payload["name"]:
            raise ValueError("Knowledge source name is required.")
        data.update(payload)
        data["source_id"] = self.source_id or deterministic_id("ksrc", payload)
        return data


@dataclass(frozen=True)
class KnowledgeCitation(SafetyFields):
    source_id: str = ""
    locator: str = ""
    label: str = ""
    citation_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        payload = {"source_id": self.source_id.strip(), "locator": self.locator.strip(), "label": self.label.strip()}
        if not payload["source_id"]:
            raise ValueError("Citation source_id is required.")
        data.update(payload)
        data["citation_id"] = self.citation_id or deterministic_id("kcit", payload)
        return data


@dataclass(frozen=True)
class KnowledgeScore(SafetyFields):
    relevance: int = 0
    reliability: int = 0
    reproducibility: int = 0
    revenue_potential: int = 0
    score_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        payload = {key: max(0, min(100, int(value))) for key, value in {
            "relevance": self.relevance, "reliability": self.reliability,
            "reproducibility": self.reproducibility, "revenue_potential": self.revenue_potential}.items()}
        data.update(payload)
        data["score_id"] = self.score_id or deterministic_id("kscore", payload)
        return data


@dataclass(frozen=True)
class KnowledgeVersion(SafetyFields):
    document_id: str = ""
    version: int = 1
    checksum: str = ""
    version_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        payload = {"document_id": self.document_id.strip(), "version": max(1, int(self.version)),
                   "checksum": self.checksum.strip()}
        if not payload["document_id"]:
            raise ValueError("Version document_id is required.")
        data.update(payload)
        data["version_id"] = self.version_id or deterministic_id("kver", payload)
        return data


@dataclass(frozen=True)
class KnowledgeDocument(SafetyFields):
    title: str = ""
    source: KnowledgeSource | dict[str, Any] = field(default_factory=dict)
    category: KnowledgeCategory | str = KnowledgeCategory.UNCATEGORIZED
    tags: list[KnowledgeTag | dict[str, Any] | str] = field(default_factory=list)
    citations: list[KnowledgeCitation | dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    score: KnowledgeScore | dict[str, Any] | None = None
    document_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        title = self.title.strip()
        if not title:
            raise ValueError("Knowledge document title is required.")
        source = (self.source.to_dict() if isinstance(self.source, KnowledgeSource)
                  else KnowledgeSource(**dict(self.source)).to_dict())
        category = self.category.value if isinstance(self.category, KnowledgeCategory) else str(self.category)
        tags = [tag.to_dict() if isinstance(tag, KnowledgeTag) else
                KnowledgeTag(name=tag).to_dict() if isinstance(tag, str) else
                KnowledgeTag(**dict(tag)).to_dict() for tag in self.tags]
        citations = [item.to_dict() if isinstance(item, KnowledgeCitation) else
                     KnowledgeCitation(**dict(item)).to_dict() for item in self.citations]
        score = (self.score.to_dict() if isinstance(self.score, KnowledgeScore) else
                 KnowledgeScore(**dict(self.score)).to_dict() if self.score else {})
        payload = {"title": title, "source": source, "category": category, "tags": tags,
                   "citations": citations, "metadata": dict(self.metadata), "score": score}
        data.update(payload)
        data["document_id"] = self.document_id or deterministic_id("kdoc", payload)
        return data
