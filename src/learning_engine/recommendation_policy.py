from __future__ import annotations

from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Mapping


CONSUMER_PROFILES: Mapping[str, Mapping[str, tuple[str, ...]]] = MappingProxyType({
    "content_engine": MappingProxyType({"tags": ("content", "note", "threads"), "categories": ("marketing", "business")}),
    "website_generator": MappingProxyType({"tags": ("website", "conversion", "seo"), "categories": ("marketing", "technology")}),
    "sales_engine": MappingProxyType({"tags": ("sales", "customer", "proposal"), "categories": ("business", "marketing")}),
    "revenue_engine": MappingProxyType({"tags": ("revenue", "monetization", "roi"), "categories": ("business", "affiliate", "ecommerce")}),
    "seo_engine": MappingProxyType({"tags": ("seo", "search", "keyword"), "categories": ("marketing", "technology")}),
    "blog_engine": MappingProxyType({"tags": ("blog", "content", "article"), "categories": ("marketing", "business")}),
    "marketing_engine": MappingProxyType({"tags": ("marketing", "campaign", "growth"), "categories": ("marketing", "business")}),
})


@dataclass(frozen=True)
class RecommendationPolicy:
    """Fixed non-executing policy and deterministic ranking weights."""

    tag_weight: int = 30
    category_weight: int = 20
    citation_weight: int = 15
    knowledge_score_weight: int = 25
    review_weight: int = 5
    source_type_weight: int = 5
    execute_allowed: bool = False
    approval_required: bool = True
    review_required: bool = True
    dry_run: bool = True
    production_actions_enabled: bool = False
    external_request_sent: bool = False

    def __post_init__(self) -> None:
        if any(weight < 0 for weight in self.weights.values()) or sum(self.weights.values()) != 100:
            raise ValueError("Recommendation weights must be non-negative and total 100.")
        if self.safety_flags != {
            "execute_allowed": False, "approval_required": True, "review_required": True,
            "dry_run": True, "production_actions_enabled": False, "external_request_sent": False,
        }:
            raise ValueError("Recommendation safety policy cannot be relaxed.")

    @property
    def weights(self) -> dict[str, int]:
        return {"tag": self.tag_weight, "category": self.category_weight,
                "citation": self.citation_weight, "knowledge_score": self.knowledge_score_weight,
                "review": self.review_weight, "source_type": self.source_type_weight}

    @property
    def safety_flags(self) -> dict[str, bool]:
        data = asdict(self)
        return {key: data[key] for key in ("execute_allowed", "approval_required", "review_required", "dry_run",
                                            "production_actions_enabled", "external_request_sent")}

    def profile(self, consumer_type: str) -> Mapping[str, tuple[str, ...]]:
        key = consumer_type.strip().lower()
        if key not in CONSUMER_PROFILES:
            raise ValueError(f"Unsupported recommendation consumer: {key}")
        return CONSUMER_PROFILES[key]

    def allows(self, document: Mapping[str, object]) -> bool:
        nested = document.get("safety_flags", {})
        if not isinstance(nested, Mapping):
            nested = {}
        return all(document.get(name, nested.get(name)) is expected
                   for name, expected in self.safety_flags.items())
