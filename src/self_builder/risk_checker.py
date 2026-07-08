from __future__ import annotations

from typing import Any


RISK_KEYWORDS = {
    "high": ["delete", "remove", "deploy", "release", "本番", "削除", "破壊", "認証", "token", "secret"],
    "medium": ["api", "settings", "設定", "保存", "database", "db", "ファイル", "テスト"],
}


def assess_risk(instruction: str, target_files: list[str] | None = None) -> dict[str, Any]:
    text = instruction.lower()
    targets = target_files or []
    level = "low"
    reasons: list[str] = []

    for word in RISK_KEYWORDS["high"]:
        if word.lower() in text:
            level = "high"
            reasons.append(f"高リスク語: {word}")

    if level != "high":
        for word in RISK_KEYWORDS["medium"]:
            if word.lower() in text:
                level = "medium"
                reasons.append(f"注意語: {word}")

    if any(path.startswith(("src/business_engine", "pages/29_", "src/official_site")) for path in targets):
        level = "high"
        reasons.append("保護対象に近いファイル")

    return {
        "risk_level": level,
        "reasons": reasons or ["小さな確認または画面内タスク"],
    }


def risk_label(level: str) -> str:
    return {
        "low": "低",
        "medium": "中",
        "high": "高",
    }.get(level, "不明")

