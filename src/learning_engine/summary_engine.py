from __future__ import annotations

import re
from collections import Counter
from typing import Any

from src.learning_engine.learning_models import clamp_confidence, require_dry_run
from src.learning_engine.summary_models import KnowledgeSummary


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Affiliate": ("affiliate", "affiliates", "referral", "commission", "asp", "amazon", "rakuten", "affiliate marketing"),
    "SNS": ("sns", "threads", "x ", "twitter", "instagram", "tiktok", "social", "follower", "impression"),
    "Content": ("content", "article", "blog", "note", "newsletter", "writing", "video", "youtube"),
    "Website": ("website", "site", "landing", "lp", "seo", "domain", "homepage"),
    "Automation": ("automation", "workflow", "scheduler", "pipeline", "auto", "bot", "zapier"),
    "Programming": ("programming", "code", "github", "python", "api", "sdk", "repository", "software"),
    "AI": ("ai", "llm", "gpt", "claude", "gemini", "prompt", "model", "agent"),
    "Marketing": ("marketing", "campaign", "ads", "ad ", "cta", "conversion", "lead", "sales funnel"),
    "Business": ("business", "revenue", "profit", "pricing", "customer", "offer", "sales", "roi"),
}

RISK_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("広告依存", ("ad", "ads", "advertising", "広告", "impression", "cpc", "cpm")),
    ("API依存", ("api", "oauth", "token", "rate limit", "外部api", "connector")),
    ("法規制", ("legal", "law", "regulation", "compliance", "copyright", "薬機法", "景表法", "著作権")),
    ("再現性低", ("viral", "trend", "buzz", "属人", "再現性低", "運任せ")),
    ("情報不足", ("unknown", "unclear", "tbd", "未確認", "不明", "情報不足")),
)

ACTION_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("landing", "Create a local landing page draft."),
    ("lp", "Create a local landing page draft."),
    ("cta", "Define one safe CTA."),
    ("seo", "Prepare SEO keyword notes."),
    ("threads", "Draft a Threads post idea for review."),
    ("note", "Draft a note article outline for review."),
    ("automation", "Map manual steps before automation."),
    ("api", "List API dependencies and keep them disabled."),
    ("github", "Review local repository docs only."),
)

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "into",
    "only",
    "local",
    "first",
    "dryrun",
    "true",
    "false",
    "knowledge",
    "summary",
    "business",
}


class SummaryEngine:
    """Rule-based Knowledge Summary generator.

    This engine does not call LLMs, external APIs, production systems, or other
    AIOS engines. It only transforms one local knowledge record into summary_data.
    """

    def generate(self, knowledge: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        require_dry_run(dry_run)
        text = self._knowledge_text(knowledge)
        keywords = self.extract_keywords(knowledge)
        category = self.detect_category(knowledge, text, keywords)
        risks = self.extract_risks(text, knowledge)
        difficulty = self.estimate_difficulty(text, risks)
        reproducibility_score = self.score_reproducibility(text, category, difficulty, risks)
        estimated_value = self.score_estimated_value(text, category, reproducibility_score, knowledge)
        confidence = self.score_confidence(text, keywords, knowledge)
        action_items = self.build_action_items(text, category, risks)
        summary = self.build_summary(knowledge, category, difficulty, reproducibility_score)
        return KnowledgeSummary(
            summary=summary,
            keywords=keywords,
            category=category,  # type: ignore[arg-type]
            difficulty=difficulty,  # type: ignore[arg-type]
            reproducibility_score=reproducibility_score,
            estimated_value=estimated_value,
            action_items=action_items,
            risks=risks,
            confidence=confidence,
            dry_run=True,
        ).to_dict()

    def extract_keywords(self, knowledge: dict[str, Any], limit: int = 12) -> list[str]:
        text_parts = [
            str(knowledge.get("title", "")),
            str(knowledge.get("summary", "")),
            str(knowledge.get("business_category", "")),
            " ".join(str(tag) for tag in knowledge.get("tags", []) if str(tag).strip()),
        ]
        for doc in knowledge.get("docs", []) or []:
            if isinstance(doc, dict):
                text_parts.extend(str(value) for value in doc.values() if isinstance(value, str))
        text = " ".join(text_parts).lower()
        words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}|[ぁ-んァ-ヶ一-龠]{2,}", text)
        counter = Counter(word for word in words if word not in STOPWORDS)
        ordered: list[str] = []
        for tag in knowledge.get("tags", []) or []:
            cleaned = str(tag).strip().lower()
            if cleaned and cleaned not in ordered:
                ordered.append(cleaned)
        category = str(knowledge.get("business_category", "")).strip().lower()
        if category and category not in ordered and category != "uncategorized":
            ordered.append(category)
        for word, _count in counter.most_common(limit * 2):
            if word not in ordered:
                ordered.append(word)
            if len(ordered) >= limit:
                break
        return ordered[:limit]

    def detect_category(self, knowledge: dict[str, Any], text: str, keywords: list[str]) -> str:
        declared = str(knowledge.get("business_category", "") or "").strip()
        if declared:
            direct = self._category_from_text(declared)
            if direct != "Other":
                return direct
        combined = f"{text} {' '.join(keywords)}".lower()
        scores = {
            category: sum(1 for marker in markers if marker in combined)
            for category, markers in CATEGORY_KEYWORDS.items()
        }
        best_category, best_score = max(scores.items(), key=lambda item: item[1])
        return best_category if best_score > 0 else "Other"

    def extract_risks(self, text: str, knowledge: dict[str, Any]) -> list[str]:
        combined = f"{text} {knowledge.get('metadata', {})}".lower()
        risks = [label for label, markers in RISK_KEYWORDS if any(marker in combined for marker in markers)]
        if len(str(knowledge.get("summary", "") or "")) < 40:
            risks.append("情報不足")
        return list(dict.fromkeys(risks))

    def estimate_difficulty(self, text: str, risks: list[str]) -> str:
        lower = text.lower()
        hard_markers = ("api", "oauth", "programming", "deploy", "legal", "automation", "integration", "github")
        easy_markers = ("markdown", "note", "article", "checklist", "template", "manual")
        hard_score = sum(1 for marker in hard_markers if marker in lower) + len(risks)
        easy_score = sum(1 for marker in easy_markers if marker in lower)
        if hard_score >= 4:
            return "Hard"
        if hard_score <= 1 and easy_score >= 1:
            return "Easy"
        return "Medium"

    def score_reproducibility(self, text: str, category: str, difficulty: str, risks: list[str]) -> int:
        score = 62
        if category in {"Content", "Website", "AI", "Business"}:
            score += 10
        if category in {"Affiliate", "SNS", "Marketing"}:
            score += 4
        if difficulty == "Easy":
            score += 14
        elif difficulty == "Hard":
            score -= 18
        score -= min(30, len(risks) * 8)
        lower = text.lower()
        if "local" in lower or "markdown" in lower or "dryrun" in lower:
            score += 6
        if "api" in lower or "oauth" in lower:
            score -= 8
        return clamp_confidence(score)

    def score_estimated_value(
        self,
        text: str,
        category: str,
        reproducibility_score: int,
        knowledge: dict[str, Any],
    ) -> int:
        score = int(reproducibility_score * 0.55)
        lower = text.lower()
        value_markers = ("revenue", "roi", "profit", "conversion", "lead", "cta", "customer", "売上", "収益")
        score += sum(6 for marker in value_markers if marker in lower)
        if category in {"Business", "Marketing", "Affiliate", "Website"}:
            score += 8
        score += int(knowledge.get("confidence", 50) or 50) // 10
        return clamp_confidence(score)

    def score_confidence(self, text: str, keywords: list[str], knowledge: dict[str, Any]) -> int:
        score = int(knowledge.get("confidence", 50) or 50)
        if len(text) >= 160:
            score += 10
        if len(keywords) >= 5:
            score += 8
        if knowledge.get("docs"):
            score += 6
        if "情報不足" in self.extract_risks(text, knowledge):
            score -= 18
        return clamp_confidence(score)

    def build_action_items(self, text: str, category: str, risks: list[str]) -> list[str]:
        lower = text.lower()
        items: list[str] = []
        for marker, action in ACTION_KEYWORDS:
            if marker in lower and action not in items:
                items.append(action)
        if category != "Other":
            items.append(f"Review {category} fit before using this knowledge in AIOS.")
        if risks:
            items.append("Resolve listed risks before experiment planning.")
        if not items:
            items.append("Add more source details before experiment planning.")
        return items[:6]

    def build_summary(
        self,
        knowledge: dict[str, Any],
        category: str,
        difficulty: str,
        reproducibility_score: int,
    ) -> str:
        title = str(knowledge.get("title", "Untitled Knowledge")).strip()
        source_summary = str(knowledge.get("summary", "")).strip()
        if len(source_summary) > 160:
            source_summary = source_summary[:157].rstrip() + "..."
        return (
            f"{title}: categorized as {category}, difficulty {difficulty}, "
            f"reproducibility {reproducibility_score}/100. {source_summary}"
        ).strip()

    @staticmethod
    def _knowledge_text(knowledge: dict[str, Any]) -> str:
        parts = [
            str(knowledge.get("title", "")),
            str(knowledge.get("summary", "")),
            str(knowledge.get("business_category", "")),
            " ".join(str(tag) for tag in knowledge.get("tags", []) if str(tag).strip()),
        ]
        for doc in knowledge.get("docs", []) or []:
            if isinstance(doc, dict):
                parts.extend(str(value) for value in doc.values() if isinstance(value, str))
            else:
                parts.append(str(doc))
        return " ".join(parts)

    @staticmethod
    def _category_from_text(value: str) -> str:
        lower = value.lower()
        for category, markers in CATEGORY_KEYWORDS.items():
            if lower == category.lower() or any(marker in lower for marker in markers):
                return category
        return "Other"
