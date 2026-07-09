from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import save_json_atomic


CONSTITUTION_VERSION = "1.0"
CONSTITUTION_PATH = PROJECT_ROOT / "config" / "development_constitution.json"

PRIORITY_ORDER = ["note", "threads", "official_site", "affiliate", "user", "saas"]

CONSTITUTION_TEXT = [
    "AIOSの最優先目的は持続的利益を生み出すこと。",
    "全改善は「初収益」「収益向上」への貢献度で優先順位決定。",
    "全Phase開始前にDevelopment Review（目的・KPI・ROI・完了条件・Risk・代替案・Knowledge重複・Business影響）実施。",
    "実装後は Test→Review→Knowledge更新→ROI評価→改善提案 を必須化。",
    "初収益達成までは大型新機能を抑制。優先順位は note→Threads→Official Site→Affiliate→User→SaaS。",
    "Business EngineはPV・CTR・CV・SEO・投稿数・収益・ROIを毎日集計しMission Plannerへ返却。",
    "Research Teamは検索需要・競合・市場・収益性を監視しOpportunity Report生成。",
    "Continuous Engineは改善案をROI・Risk・工数・収益性で最適化。",
    "自己改善目的はコード増加ではなくAIOS価値最大化。改善不要なら改善しない判断も正解。",
    "AIOSは収益・品質・保守性・安全性・ユーザー価値の5指標で総合評価し最適改善を選択。",
]

REQUIRED_REVIEW_FIELDS = [
    "purpose",
    "kpi",
    "roi",
    "completion_conditions",
    "risk",
    "alternatives",
    "knowledge_duplication",
    "business_impact",
]

REVENUE_TERMS = (
    "revenue",
    "profit",
    "roi",
    "business",
    "monet",
    "sales",
    "pv",
    "ctr",
    "cv",
    "seo",
    "note",
    "threads",
    "affiliate",
    "収益",
    "利益",
    "売上",
    "初収益",
    "事業",
    "投稿",
)

LARGE_FEATURE_TERMS = ("new feature", "large", "platform", "新機能", "大型", "基盤刷新", "全面")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_constitution() -> dict[str, Any]:
    return {
        "version": CONSTITUTION_VERSION,
        "last_update": _now(),
        "constitution": CONSTITUTION_TEXT,
        "priority_order": PRIORITY_ORDER,
        "required_review_fields": REQUIRED_REVIEW_FIELDS,
        "compliance": {
            "score": 100,
            "status": "active",
            "last_checked_at": _now(),
            "summary": "Development Constitution v1.0 active.",
        },
        "violation_history": [],
        "improvement_history": [],
        "roi_impact": {
            "estimated_revenue": 0,
            "estimated_cost": 0,
            "estimated_roi": 0,
            "last_evaluated_at": "",
        },
    }


def load_development_constitution(path: str | Path = CONSTITUTION_PATH) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        data = _default_constitution()
        save_development_constitution(data, p)
        return data
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        data = _default_constitution()
    if not isinstance(data, dict):
        data = _default_constitution()
    defaults = _default_constitution()
    for key, value in defaults.items():
        data.setdefault(key, value)
    data["version"] = CONSTITUTION_VERSION
    data["constitution"] = CONSTITUTION_TEXT
    data.setdefault("compliance", defaults["compliance"])
    data.setdefault("violation_history", [])
    data.setdefault("improvement_history", [])
    data.setdefault("roi_impact", defaults["roi_impact"])
    return data


def save_development_constitution(data: dict[str, Any], path: str | Path = CONSTITUTION_PATH) -> None:
    data["version"] = CONSTITUTION_VERSION
    data["last_update"] = _now()
    save_json_atomic(path, data)


def persist_constitution_to_knowledge(
    constitution: dict[str, Any] | None = None,
    *,
    knowledge_path: str | Path | None = None,
) -> dict[str, Any]:
    from src.self_builder.knowledge_manager import KNOWLEDGE_PATH, load_knowledge, save_knowledge

    path = Path(knowledge_path) if knowledge_path is not None else KNOWLEDGE_PATH
    data = constitution or load_development_constitution()
    knowledge = load_knowledge(path)
    record = {
        "type": "development_constitution",
        "version": data.get("version", CONSTITUTION_VERSION),
        "last_update": data.get("last_update", ""),
        "constitution": data.get("constitution", CONSTITUTION_TEXT),
        "compliance": data.get("compliance", {}),
        "roi_impact": data.get("roi_impact", {}),
        "updated_at": _now(),
    }
    knowledge["development_constitution"] = record
    history = knowledge.setdefault("history", [])
    if not history or history[0].get("type") != "development_constitution":
        history.insert(0, record)
    save_knowledge(knowledge, path)
    return record


def ensure_development_constitution(
    *,
    constitution_path: str | Path = CONSTITUTION_PATH,
    knowledge_path: str | Path | None = None,
) -> dict[str, Any]:
    constitution = load_development_constitution(constitution_path)
    save_development_constitution(constitution, constitution_path)
    persist_constitution_to_knowledge(constitution, knowledge_path=knowledge_path)
    return constitution


def development_review(subject: dict[str, Any] | str, *, context: dict[str, Any] | None = None) -> dict[str, Any]:
    data = _subject_dict(subject)
    text = _subject_text(data)
    revenue_aligned = _has_any(text, REVENUE_TERMS)
    large_feature = _has_any(text, LARGE_FEATURE_TERMS)
    estimated_revenue = int(data.get("estimated_revenue", 0) or (18000 if revenue_aligned else 3000))
    estimated_cost = int(data.get("estimated_cost", 0) or data.get("estimated_effort", 0) or 1000)
    roi = calculate_roi(estimated_revenue, estimated_cost)
    review = {
        "purpose": "収益最大化" if revenue_aligned else "AIOS価値維持",
        "kpi": ["PV", "CTR", "CV", "SEO", "投稿数", "収益", "ROI"],
        "roi": roi,
        "completion_conditions": ["Test", "Review", "Knowledge更新", "ROI評価", "改善提案"],
        "risk": data.get("risk_level", "low"),
        "alternatives": ["改善しない", "note/Threads/Official Site優先へ縮小", "手動運用で検証"],
        "knowledge_duplication": context.get("knowledge_duplication", "unknown") if context else "unknown",
        "business_impact": "high" if revenue_aligned else "medium",
        "priority_order": PRIORITY_ORDER,
        "large_feature_suppressed": bool(large_feature and not revenue_aligned),
        "reviewed_at": _now(),
    }
    compliance = evaluate_constitution_compliance({**data, "development_review": review})
    review["constitution_compliance"] = compliance
    return review


def evaluate_constitution_compliance(subject: dict[str, Any] | str) -> dict[str, Any]:
    data = _subject_dict(subject)
    text = _subject_text(data)
    review = data.get("development_review", {}) if isinstance(data.get("development_review"), dict) else {}
    checks = {
        "profit_priority": _has_any(text, REVENUE_TERMS) or review.get("purpose") in ("収益最大化", "AIOS価値維持"),
        "development_review": all(field in review for field in REQUIRED_REVIEW_FIELDS),
        "post_implementation_loop": all(
            token in " ".join(review.get("completion_conditions", []))
            for token in ("Test", "Review", "Knowledge更新", "ROI評価", "改善提案")
        ),
        "large_feature_suppression": not bool(review.get("large_feature_suppressed", False)),
        "five_factor_balance": True,
    }
    passed = sum(1 for ok in checks.values() if ok)
    score = int(round(passed / max(len(checks), 1) * 100))
    violations = [name for name, ok in checks.items() if not ok]
    return {
        "version": CONSTITUTION_VERSION,
        "score": score,
        "status": "compliant" if score >= 80 else "violation",
        "checks": checks,
        "violations": violations,
        "evaluated_at": _now(),
    }


def record_violation(
    subject: dict[str, Any] | str,
    *,
    reason: str,
    constitution_path: str | Path = CONSTITUTION_PATH,
) -> dict[str, Any]:
    constitution = load_development_constitution(constitution_path)
    record = {
        "reason": reason,
        "subject": _subject_text(_subject_dict(subject))[:300],
        "created_at": _now(),
    }
    constitution.setdefault("violation_history", []).insert(0, record)
    constitution["violation_history"] = constitution["violation_history"][:100]
    save_development_constitution(constitution, constitution_path)
    return record


def record_improvement(
    improvement: dict[str, Any],
    *,
    constitution_path: str | Path = CONSTITUTION_PATH,
) -> dict[str, Any]:
    constitution = load_development_constitution(constitution_path)
    scored = score_improvement(improvement)
    record = {**scored, "created_at": _now()}
    constitution.setdefault("improvement_history", []).insert(0, record)
    constitution["improvement_history"] = constitution["improvement_history"][:100]
    constitution["roi_impact"] = {
        "estimated_revenue": int(scored.get("estimated_revenue", 0)),
        "estimated_cost": int(scored.get("estimated_cost", 0)),
        "estimated_roi": int(scored.get("roi_score", 0)),
        "last_evaluated_at": _now(),
    }
    save_development_constitution(constitution, constitution_path)
    return record


def score_improvement(candidate: dict[str, Any]) -> dict[str, Any]:
    text = _subject_text(candidate)
    estimated_revenue = int(candidate.get("estimated_revenue", 0) or (18000 if _has_any(text, REVENUE_TERMS) else 3000))
    effort = int(candidate.get("effort", 0) or candidate.get("estimated_effort", 0) or candidate.get("estimated_minutes_saved", 0) or 10)
    risk = str(candidate.get("risk", candidate.get("risk_level", "medium"))).lower()
    cost = int(candidate.get("estimated_cost", 0) or max(effort * 120, 1000))
    risk_penalty = {"low": 0, "medium": 10, "normal": 10, "high": 35}.get(risk, 15)
    profitability = 40 if estimated_revenue > 0 else 10
    roi_score = calculate_roi(estimated_revenue, cost)
    total = max(0, roi_score + profitability - risk_penalty - min(effort, 60))
    return {
        **candidate,
        "estimated_revenue": estimated_revenue,
        "estimated_cost": cost,
        "effort": effort,
        "risk": risk,
        "profitability": profitability,
        "roi_score": roi_score,
        "constitution_priority_score": int(total),
    }


def prioritize_improvements(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = [score_improvement(candidate) for candidate in candidates]
    risk_rank = {"low": 0, "normal": 1, "medium": 1, "high": 2}
    return sorted(
        scored,
        key=lambda item: (
            -int(item.get("constitution_priority_score", 0)),
            risk_rank.get(str(item.get("risk", "medium")), 1),
            int(item.get("effort", 0)),
            -int(item.get("profitability", 0)),
        ),
    )


def calculate_roi(revenue: int, cost: int) -> int:
    safe_cost = max(int(cost or 0), 1)
    return int(round((int(revenue or 0) - safe_cost) / safe_cost * 100))


def _subject_dict(subject: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(subject, dict):
        return dict(subject)
    return {"instruction": str(subject)}


def _subject_text(data: dict[str, Any]) -> str:
    parts = []
    for value in data.values():
        if isinstance(value, (str, int, float)):
            parts.append(str(value))
        elif isinstance(value, list):
            parts.extend(str(item) for item in value[:20])
        elif isinstance(value, dict):
            parts.append(json.dumps(value, ensure_ascii=False))
    return " ".join(parts).lower()


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term.lower() in text for term in terms)
