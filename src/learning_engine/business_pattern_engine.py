from __future__ import annotations

import re
from typing import Any

from src.learning_engine.business_pattern_models import BusinessPattern
from src.learning_engine.learning_models import clamp_confidence, require_dry_run
from src.learning_engine.summary_engine import SummaryEngine


CHANNEL_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("note", ("note", "article", "blog", "newsletter")),
    ("Threads", ("threads", "twitter", "x ", "sns", "social")),
    ("Website", ("website", "site", "landing", "lp", "seo")),
    ("YouTube", ("youtube", "video")),
    ("GitHub", ("github", "repository", "code")),
)

MODEL_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("affiliate", ("affiliate", "commission", "referral", "asp", "amazon", "rakuten")),
    ("lead_generation", ("lead", "inquiry", "consultation", "cta", "sales funnel")),
    ("content_product", ("template", "checklist", "ebook", "course", "paid content")),
    ("saas_or_tool", ("tool", "app", "automation", "workflow", "software", "api")),
    ("ads", ("ads", "advertising", "impression", "cpc", "cpm")),
)

ASSET_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Local outline", ("note", "article", "blog", "content")),
    ("CTA draft", ("cta", "conversion", "lead", "offer")),
    ("Landing page draft", ("landing", "lp", "website", "site")),
    ("Keyword memo", ("seo", "keyword", "search")),
    ("Manual workflow checklist", ("automation", "workflow", "pipeline")),
    ("Risk review memo", ("legal", "copyright", "compliance", "regulation")),
)

CURRENT_AIOS_CHANNELS = {"note", "Threads", "Website"}
LOW_COST_MODELS = {"affiliate", "lead_generation", "content_product"}


class BusinessPatternEngine:
    """Rule-based business pattern extraction for local Learning Engine data."""

    def __init__(self, *, summary_engine: SummaryEngine | None = None) -> None:
        self.summary_engine = summary_engine or SummaryEngine()

    def generate(self, knowledge: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        require_dry_run(dry_run)
        summary_data = knowledge.get("summary_data")
        if not isinstance(summary_data, dict):
            summary_data = self.summary_engine.generate(knowledge, dry_run=True)

        text = self._combined_text(knowledge, summary_data)
        category = str(summary_data.get("category", "Other") or "Other")
        channels = self.detect_channels(text, category)
        monetization_model = self.detect_monetization_model(text, category)
        required_assets = self.detect_required_assets(text, category, monetization_model)
        risks = self.merge_risks(knowledge, summary_data)
        validation_plan = self.build_validation_plan(channels, monetization_model, risks)
        action_items = self.build_action_items(summary_data, validation_plan)
        reproducibility_score = self.score_reproducibility(summary_data, risks, required_assets)
        estimated_value = self.score_estimated_value(summary_data, monetization_model, channels)
        compatible_with_current_aios = self.is_compatible_with_current_aios(channels, monetization_model, risks)
        manual_work_ratio = self.estimate_manual_work_ratio(channels, monetization_model, risks)
        automation_ratio = 100 - manual_work_ratio

        return BusinessPattern(
            name=self.build_name(knowledge, category, monetization_model),
            source_knowledge_id=str(knowledge.get("knowledge_id", "")),
            category=category,
            monetization_model=monetization_model,
            target_audience=self.detect_target_audience(text, category),
            channels=channels,
            required_assets=required_assets,
            revenue_hypothesis=self.build_revenue_hypothesis(category, monetization_model, channels),
            validation_plan=validation_plan,
            action_items=action_items,
            risks=risks,
            evidence=self.build_evidence(knowledge, summary_data),
            reproducibility_score=reproducibility_score,
            aios_priority=self.calculate_aios_priority(
                reproducibility_score=reproducibility_score,
                estimated_value=estimated_value,
                channels=channels,
                monetization_model=monetization_model,
                risks=risks,
                compatible_with_current_aios=compatible_with_current_aios,
            ),
            estimated_first_profit_days=self.estimate_first_profit_days(
                channels=channels,
                monetization_model=monetization_model,
                risks=risks,
                reproducibility_score=reproducibility_score,
            ),
            estimated_initial_cost=self.estimate_initial_cost(channels, monetization_model, risks),
            manual_work_ratio=manual_work_ratio,
            automation_ratio=automation_ratio,
            compatible_with_current_aios=compatible_with_current_aios,
            recommended_current_phase=self.recommend_current_phase(
                channels=channels,
                monetization_model=monetization_model,
                risks=risks,
                compatible_with_current_aios=compatible_with_current_aios,
            ),
            estimated_value=estimated_value,
            confidence=self.score_confidence(summary_data, validation_plan, knowledge),
            dry_run=True,
        ).to_dict()

    def detect_channels(self, text: str, category: str) -> list[str]:
        lower = text.lower()
        channels = [label for label, markers in CHANNEL_MARKERS if any(marker in lower for marker in markers)]
        if category == "SNS" and "Threads" not in channels:
            channels.append("Threads")
        if category in {"Website", "Affiliate"} and "Website" not in channels:
            channels.append("Website")
        if category == "Content" and "note" not in channels:
            channels.append("note")
        return channels[:4] or ["local_review"]

    def detect_monetization_model(self, text: str, category: str) -> str:
        lower = text.lower()
        scores = {
            label: sum(1 for marker in markers if marker in lower)
            for label, markers in MODEL_MARKERS
        }
        best_label, best_score = max(scores.items(), key=lambda item: item[1])
        if best_score > 0:
            return best_label
        if category == "Affiliate":
            return "affiliate"
        if category in {"Website", "Marketing", "Business"}:
            return "lead_generation"
        if category in {"Automation", "Programming", "AI"}:
            return "saas_or_tool"
        return "content_product"

    def detect_required_assets(self, text: str, category: str, monetization_model: str) -> list[str]:
        lower = text.lower()
        assets = [label for label, markers in ASSET_MARKERS if any(marker in lower for marker in markers)]
        if monetization_model == "affiliate":
            assets.extend(["Affiliate disclosure memo", "Product comparison draft"])
        if monetization_model == "lead_generation":
            assets.append("Lead capture CTA draft")
        if category == "SNS":
            assets.append("Short post draft")
        return list(dict.fromkeys(assets))[:6] or ["Local validation memo"]

    def merge_risks(self, knowledge: dict[str, Any], summary_data: dict[str, Any]) -> list[str]:
        risks: list[str] = []
        for source in (summary_data.get("risks", []), knowledge.get("risks", [])):
            if isinstance(source, list):
                risks.extend(str(item).strip() for item in source if str(item).strip())
        if not str(knowledge.get("summary", "")).strip():
            risks.append("情報不足")
        return list(dict.fromkeys(risks))

    def build_validation_plan(
        self,
        channels: list[str],
        monetization_model: str,
        risks: list[str],
    ) -> list[str]:
        plan = [
            "Write a local one-page pattern memo.",
            "Define one measurable success signal before any production use.",
        ]
        if "Website" in channels:
            plan.append("Prepare a local landing page outline only.")
        if "Threads" in channels:
            plan.append("Draft three local social post variants for review.")
        if monetization_model == "affiliate":
            plan.append("Check disclosure and product evidence before review.")
        if risks:
            plan.append("Resolve risk notes before connecting this to any workflow.")
        return plan[:6]

    def build_action_items(self, summary_data: dict[str, Any], validation_plan: list[str]) -> list[str]:
        items: list[str] = []
        source_items = summary_data.get("action_items", [])
        if isinstance(source_items, list):
            items.extend(str(item).strip() for item in source_items if str(item).strip())
        items.extend(validation_plan)
        return list(dict.fromkeys(items))[:8]

    def score_reproducibility(
        self,
        summary_data: dict[str, Any],
        risks: list[str],
        required_assets: list[str],
    ) -> int:
        score = int(summary_data.get("reproducibility_score", 50) or 50)
        score += min(12, len(required_assets) * 2)
        score -= min(30, len(risks) * 7)
        return clamp_confidence(score)

    def score_estimated_value(
        self,
        summary_data: dict[str, Any],
        monetization_model: str,
        channels: list[str],
    ) -> int:
        score = int(summary_data.get("estimated_value", 50) or 50)
        if monetization_model in {"affiliate", "lead_generation", "saas_or_tool"}:
            score += 10
        if "Website" in channels:
            score += 6
        if "Threads" in channels:
            score += 4
        return clamp_confidence(score)

    def calculate_aios_priority(
        self,
        *,
        reproducibility_score: int,
        estimated_value: int,
        channels: list[str],
        monetization_model: str,
        risks: list[str],
        compatible_with_current_aios: bool,
    ) -> str:
        score = int(reproducibility_score * 0.45) + int(estimated_value * 0.35)
        if any(channel in CURRENT_AIOS_CHANNELS for channel in channels):
            score += 14
        if monetization_model in LOW_COST_MODELS:
            score += 10
        if compatible_with_current_aios:
            score += 8
        score -= min(24, len(risks) * 6)
        if score >= 76:
            return "HIGH"
        if score >= 52:
            return "MEDIUM"
        return "LOW"

    def estimate_first_profit_days(
        self,
        *,
        channels: list[str],
        monetization_model: str,
        risks: list[str],
        reproducibility_score: int,
    ) -> int:
        days = 30
        if monetization_model in {"affiliate", "lead_generation"}:
            days -= 10
        if "Threads" in channels:
            days -= 4
        if "note" in channels:
            days -= 3
        if "Website" in channels:
            days += 4
        if monetization_model in {"saas_or_tool", "ads"}:
            days += 18
        if reproducibility_score >= 80:
            days -= 4
        elif reproducibility_score < 45:
            days += 10
        days += len(risks) * 5
        return max(7, min(90, days))

    def estimate_initial_cost(self, channels: list[str], monetization_model: str, risks: list[str]) -> int:
        cost = 0
        if "Website" in channels:
            cost += 1000
        if monetization_model == "affiliate":
            cost += 0
        elif monetization_model == "lead_generation":
            cost += 500
        elif monetization_model == "content_product":
            cost += 0
        elif monetization_model == "saas_or_tool":
            cost += 3000
        elif monetization_model == "ads":
            cost += 5000
        if risks:
            cost += 500
        return cost

    def estimate_manual_work_ratio(
        self,
        channels: list[str],
        monetization_model: str,
        risks: list[str],
    ) -> int:
        ratio = 72
        if "Threads" in channels:
            ratio += 8
        if "note" in channels:
            ratio += 6
        if "Website" in channels:
            ratio += 4
        if monetization_model == "saas_or_tool":
            ratio -= 18
        if monetization_model == "ads":
            ratio -= 10
        ratio += min(12, len(risks) * 4)
        return clamp_confidence(ratio)

    def is_compatible_with_current_aios(
        self,
        channels: list[str],
        monetization_model: str,
        risks: list[str],
    ) -> bool:
        channel_fit = any(channel in CURRENT_AIOS_CHANNELS for channel in channels)
        model_fit = monetization_model in LOW_COST_MODELS or monetization_model == "saas_or_tool"
        hard_blockers = {"API依存", "広告依存"}
        blocker_count = sum(1 for risk in risks if risk in hard_blockers)
        return channel_fit and model_fit and blocker_count < 2

    def recommend_current_phase(
        self,
        *,
        channels: list[str],
        monetization_model: str,
        risks: list[str],
        compatible_with_current_aios: bool,
    ) -> str:
        if not compatible_with_current_aios:
            return "Phase6-3 Risk Review"
        if "Threads" in channels:
            return "Phase7 Threads First Revenue Pilot"
        if "note" in channels:
            return "Phase7 note First Revenue Pilot"
        if "Website" in channels or monetization_model == "lead_generation":
            return "Phase7 Official Site Lead Pilot"
        if risks:
            return "Phase6-3 Manual Validation"
        return "Phase6-3 Business Pattern Review"

    def score_confidence(
        self,
        summary_data: dict[str, Any],
        validation_plan: list[str],
        knowledge: dict[str, Any],
    ) -> int:
        score = int(summary_data.get("confidence", knowledge.get("confidence", 50)) or 50)
        if len(validation_plan) >= 3:
            score += 8
        if knowledge.get("docs"):
            score += 4
        return clamp_confidence(score)

    def build_name(self, knowledge: dict[str, Any], category: str, monetization_model: str) -> str:
        title = re.sub(r"\s+", " ", str(knowledge.get("title", "Untitled Pattern")).strip())
        return f"{category} {monetization_model} pattern: {title}"[:120]

    def build_revenue_hypothesis(
        self,
        category: str,
        monetization_model: str,
        channels: list[str],
    ) -> str:
        channel_text = ", ".join(channels)
        return (
            f"If this {category} knowledge is validated locally, it may support "
            f"a {monetization_model} experiment through {channel_text}."
        )

    def detect_target_audience(self, text: str, category: str) -> str:
        lower = text.lower()
        if "beginner" in lower or "初心者" in lower:
            return "beginners"
        if "creator" in lower or "content" in lower:
            return "content creators"
        if "business" in lower or "revenue" in lower or "sales" in lower:
            return "small business operators"
        if category == "Programming":
            return "developers"
        return "local AIOS reviewers"

    def build_evidence(self, knowledge: dict[str, Any], summary_data: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "type": "knowledge",
                "knowledge_id": knowledge.get("knowledge_id", ""),
                "title": knowledge.get("title", ""),
            },
            {
                "type": "summary_data",
                "category": summary_data.get("category", "Other"),
                "confidence": summary_data.get("confidence", 0),
            },
        ]

    @staticmethod
    def _combined_text(knowledge: dict[str, Any], summary_data: dict[str, Any]) -> str:
        parts = [
            str(knowledge.get("title", "")),
            str(knowledge.get("summary", "")),
            " ".join(str(tag) for tag in knowledge.get("tags", []) if str(tag).strip()),
            str(summary_data.get("summary", "")),
            " ".join(str(item) for item in summary_data.get("keywords", []) if str(item).strip()),
            " ".join(str(item) for item in summary_data.get("action_items", []) if str(item).strip()),
        ]
        for doc in knowledge.get("docs", []) or []:
            if isinstance(doc, dict):
                parts.extend(str(value) for value in doc.values() if isinstance(value, str))
        return " ".join(parts)
