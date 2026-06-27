"""risk_analyzer — Estimate risk level of pending approval items.

Rule-based only. No external APIs. No automatic execution.
"""
from __future__ import annotations

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
