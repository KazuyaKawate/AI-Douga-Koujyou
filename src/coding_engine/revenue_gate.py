from __future__ import annotations

from typing import Any


REVENUE_SIGNALS = {
    "real_post": ("実投稿", "投稿", "publish", "threads", "note公開", "公開"),
    "pv": ("pv", "pageview", "ページビュー", "閲覧", "analytics"),
    "click": ("click", "クリック", "cta", "affiliate", "アフィリエイトリンク"),
    "affiliate_revenue": ("affiliate", "アフィリエイト", "成果報酬", "asp"),
    "note_sales": ("note売上", "note収益", "有料note", "note"),
}


class CommanderRevenueGate:
    """Scores whether a coding instruction moves AIOS closer to first revenue."""

    def evaluate(self, instruction: str, target_files: list[str] | None = None) -> dict[str, Any]:
        text = f"{instruction} {' '.join(target_files or [])}".lower()
        signals = {}
        score = 0
        for key, tokens in REVENUE_SIGNALS.items():
            matched = [token for token in tokens if token.lower() in text]
            signals[key] = bool(matched)
            if matched:
                score += self._weight(key)

        if any(token in text for token in ("安全", "dryrun", "dry run", "レビュー", "承認", "保守", "再現")):
            score += 8
        if any(token in text for token in ("ui polish", "見た目", "大型", "新機能", "リファクタ")) and score < 40:
            score -= 15

        score = max(0, min(100, score))
        decision = "prioritize" if score >= 55 else "review" if score >= 35 else "defer"
        return {
            "score": score,
            "decision": decision,
            "signals": signals,
            "reason": self._reason(decision),
            "question": "この機能は初収益を近付けるか？",
        }

    @staticmethod
    def _weight(signal: str) -> int:
        return {
            "real_post": 30,
            "pv": 20,
            "click": 20,
            "affiliate_revenue": 18,
            "note_sales": 18,
        }.get(signal, 0)

    @staticmethod
    def _reason(decision: str) -> str:
        if decision == "prioritize":
            return "初収益への距離が近いため優先します。"
        if decision == "review":
            return "収益接続はありますが、安全性とROI確認後に実行します。"
        return "初収益への直接効果が弱いため延期候補です。"
