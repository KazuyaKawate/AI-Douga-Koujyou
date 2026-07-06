"""risk_analyzer — Estimate risk level of pending approval items.

Rule-based only. No external APIs. No automatic execution.
"""
from __future__ import annotations

import re

RISK_FACTORS: list[tuple[str, str, str]] = [
    # (risk_level, keyword_in_summary_or_impact, label)
    ("high",   "削除",        "削除操作を含む"),
    ("high",   "drop",        "DROP操作を含む"),
    ("high",   "reset",       "リセット操作を含む"),
    ("high",   "push --force","強制プッシュを含む"),
    ("high",   "本番",        "本番環境への影響"),
    ("medium", "git push",    "リモートへのプッシュ"),
    ("medium", "git commit",  "コミット操作"),
    ("medium", "pip install", "パッケージインストール"),
    ("medium", "config",      "設定ファイルの変更"),
    ("medium", "有効化",      "自動化ワークフローの有効化"),
    ("low",    "git status",  "Git状態確認"),
    ("low",    "git log",     "Gitログ確認"),
    ("low",    "読み取り",     "読み取り専用操作"),
    ("low",    "ドライラン",   "ドライラン実行"),
]

_RISK_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}


def analyze_risk(item: dict) -> dict:
    """
    Analyze a pending approval item and return risk assessment.
    Returns: risk_level, factors (list of matched strings), confidence (0-100).
    """
    text = " ".join([
        item.get("command_summary", ""),
        item.get("expected_impact", ""),
        item.get("title", ""),
        " ".join(item.get("affected_files", [])),
    ]).lower()

    matched_factors: list[str] = []
    highest_risk = "none"

    for risk_level, keyword, label in RISK_FACTORS:
        if keyword.lower() in text:
            matched_factors.append(label)
            if _RISK_ORDER[risk_level] > _RISK_ORDER[highest_risk]:
                highest_risk = risk_level

    # Respect the item's declared risk if it's higher
    declared = item.get("estimated_risk", "none")
    if declared in _RISK_ORDER and _RISK_ORDER[declared] > _RISK_ORDER[highest_risk]:
        highest_risk = declared
        matched_factors.append(f"申告リスク: {declared}")

    # Source-based adjustment
    source = item.get("source", "")
    if source == "aiceo":
        matched_factors.append("AI CEOからの推奨アクション")
    elif source == "automation":
        if _RISK_ORDER[highest_risk] < _RISK_ORDER["medium"]:
            highest_risk = "low"
        matched_factors.append("自動化ワークフローの実行")

    confidence = min(80, 40 + len(matched_factors) * 15)

    return {
        "risk_level":    highest_risk,
        "factors":       matched_factors,
        "confidence":    confidence,
        "auto_approved": highest_risk == "none",
        "requires_review": highest_risk in ("medium", "high"),
        "block_execution": highest_risk == "high",
    }


def get_risk_color(risk_level: str) -> str:
    return {"none": "green", "low": "yellow", "medium": "orange", "high": "red"}.get(risk_level, "gray")


def analyze_content_risk(content: str, content_type: str = "") -> list[dict]:
    """Local rule-based content risk checks.

    Warnings are informational unless severity is critical. No external APIs and
    no automatic publishing decisions are made here.
    """
    text = content or ""
    lowered = text.lower()
    flags: list[dict] = []

    def add(code: str, label: str, severity: str = "warning") -> None:
        flags.append({"code": code, "label": label, "severity": severity})

    if not text.strip():
        add("empty_content", "Empty content", "critical")
    elif len(text.strip()) < 80:
        add("too_short", "Content may be too short", "warning")

    external_claim_words = ["guaranteed", "official", "certified", "no.1", "number one", "必ず", "公式", "認定", "世界一"]
    if any(word in lowered for word in external_claim_words):
        add("possible_external_claim", "Possible external or unverifiable claim", "warning")

    money_words = ["earn", "income", "profit", "revenue", "guarantee", "稼げ", "収益", "利益", "月収", "年収"]
    if any(word in lowered for word in money_words):
        add("money_earnings_claim", "Money or earnings claim", "warning")

    regulated_words = [
        "medical", "diagnosis", "medicine", "legal", "lawsuit", "investment", "financial advice",
        "医療", "診断", "薬", "法律", "訴訟", "投資", "金融助言",
    ]
    if any(word in lowered for word in regulated_words):
        add("regulated_claim", "Medical, legal, or financial claim", "warning")

    if re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text) or re.search(r"\b\d{3}[- ]?\d{3,4}[- ]?\d{4}\b", text):
        add("personal_information_pattern", "Possible personal information pattern", "critical")

    if re.search(r"https?://[^\s)]+", text):
        add("url_pattern", "URL pattern detected", "warning")

    if content_type == "affiliate_description":
        has_disclosure = (
            re.search(r"\b(affiliate|ad|sponsored|promotion|pr)\b", lowered) is not None
            or any(term in text for term in ["広告", "アフィリエイト", "プロモーション"])
        )
        if not has_disclosure:
            add("affiliate_disclosure_missing", "Affiliate disclosure may be missing", "warning")

    platform_terms = ["giveaway", "adult", "violence", "crypto", "ギャンブル", "成人向け", "暴力", "暗号資産"]
    if any(term in lowered for term in platform_terms):
        add("platform_policy_warning", "Platform policy warning", "warning")

    return flags
