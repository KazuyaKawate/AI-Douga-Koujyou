from __future__ import annotations

import re
from typing import Any

from src.content_engine.content_models import ContentPlan, trim_text
from src.learning_engine.learning_models import require_dry_run


class ContentGenerator:
    """Rule-based content generation from local revenue_plan rows."""

    def generate(self, plan: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        require_dry_run(dry_run)
        title = self.build_title(plan)
        category = str(plan.get("business_category") or "Other")
        keywords = self.seo_keywords(plan, title, category)
        return ContentPlan(
            title=title,
            subtitle=self.subtitle(plan, category),
            summary=self.description(plan, title, category),
            note_outline=self.note_outline(plan, title),
            threads_outline=self.threads_outline(plan, title),
            website_outline=self.website_outline(plan, title),
            seo_keywords=keywords,
            hashtags=self.hashtags(keywords, category),
            category=category,
            target=self.target(plan, category),
            estimated_read_time=self.estimated_read_time(plan),
            cta=self.cta(plan, category),
            source={
                "engine": "revenue_engine",
                "source_type": "revenue_plan",
                "plan_id": plan.get("plan_id", ""),
                "task_id": plan.get("task_id", ""),
                "priority": plan.get("priority", ""),
                "confidence": plan.get("confidence", 50),
            },
            dry_run=True,
        ).to_dict()

    def build_title(self, plan: dict[str, Any]) -> str:
        raw = str(plan.get("title") or "AIOS first revenue plan")
        raw = re.sub(r"^Review first-revenue task:\s*", "", raw).strip()
        prefix = {
            "note": "noteで初収益を狙う",
            "Threads": "Threadsで初収益を狙う",
            "Website": "公式サイトで初収益を狙う",
            "Affiliate": "アフィリエイトで初収益を狙う",
            "Consulting": "相談導線で初収益を狙う",
        }.get(str(plan.get("business_category")), "AIOSで初収益を狙う")
        return trim_text(f"{prefix}: {raw}", 60)

    def subtitle(self, plan: dict[str, Any], category: str) -> str:
        days = int(plan.get("estimated_first_profit_days", 30) or 30)
        cost = int(plan.get("estimated_initial_cost", 0) or 0)
        return trim_text(f"{category}向けに{days}日以内・初期費用{cost}円で検証するLocal First案", 90)

    def description(self, plan: dict[str, Any], title: str, category: str) -> str:
        profit = int(plan.get("expected_profit", 0) or 0)
        return trim_text(f"{title}。{category}で初収益を優先し、想定利益{profit}円の仮説を手動レビュー前提で検証します。", 120)

    def note_outline(self, plan: dict[str, Any], title: str) -> list[str]:
        return [
            title,
            "なぜ今この収益候補を検証するのか",
            "想定読者と解決する悩み",
            "初収益までの最短ステップ",
            "費用・手作業・自動化のバランス",
            "リスクとレビュー観点",
            self.cta(plan, str(plan.get("business_category", "Other"))),
        ]

    def threads_outline(self, plan: dict[str, Any], title: str) -> list[str]:
        points = [
            f"1. {title}",
            "2. 初収益を最優先にする理由",
            f"3. 想定初収益日数: {plan.get('estimated_first_profit_days', 30)}日",
            f"4. 初期費用: {plan.get('estimated_initial_cost', 0)}円",
            f"5. 自動化率: {plan.get('automation_ratio', 0)}%",
            f"6. 手作業率: {plan.get('manual_ratio', 100)}%",
            "7. Local Firstで小さく検証",
            "8. 投稿・決済・外部APIはレビュー後",
            "9. 成功条件を1つに絞る",
            f"10. CTA: {self.cta(plan, str(plan.get('business_category', 'Other')))}",
        ]
        return points[:20]

    def website_outline(self, plan: dict[str, Any], title: str) -> list[str]:
        return [
            f"Hero: {title}",
            "Problem: 初収益までの迷いを減らす",
            "Offer: 小さく検証できる収益候補",
            "Proof: 想定利益・日数・費用を明示",
            "Process: note / Threads / Websiteで段階検証",
            "Risk: Review Requiredで安全確認",
            f"CTA: {self.cta(plan, str(plan.get('business_category', 'Other')))}",
        ]

    def seo_keywords(self, plan: dict[str, Any], title: str, category: str) -> list[str]:
        words = [
            "AIOS",
            "初収益",
            "Local First",
            category,
            str(plan.get("priority", "")),
            "note",
            "Threads",
            "公式サイト",
            "収益化",
            "DryRun",
        ]
        for token in re.findall(r"[A-Za-z0-9_一-龠ぁ-んァ-ヶ]{2,}", title):
            words.append(token)
        unique: list[str] = []
        for word in words:
            cleaned = str(word).strip()
            if cleaned and cleaned not in unique:
                unique.append(cleaned)
        return unique[:10]

    def hashtags(self, keywords: list[str], category: str) -> list[str]:
        return ["AIOS", "初収益", "LocalFirst", category, *keywords[:4]][:10]

    def target(self, plan: dict[str, Any], category: str) -> str:
        if category == "Consulting":
            return "相談導線から初収益を作りたい事業者"
        if category == "Affiliate":
            return "低コストでアフィリエイト検証したい個人事業者"
        return "AIOSで初収益候補を検証する運用者"

    def estimated_read_time(self, plan: dict[str, Any]) -> int:
        manual = int(plan.get("manual_ratio", 70) or 70)
        return 4 if manual < 60 else 5 if manual < 85 else 6

    def cta(self, plan: dict[str, Any], category: str) -> str:
        days = int(plan.get("estimated_first_profit_days", 30) or 30)
        if category == "Threads":
            return f"{days}日以内に試す投稿案を1つ選び、レビューしてからDryRunで検証する"
        if category == "Website":
            return "公式サイト用LP案をレビューし、問い合わせ導線だけをDryRunで確認する"
        if category == "Affiliate":
            return "紹介候補と開示文を確認し、note下書きとしてレビューに回す"
        return "この収益候補をレビューし、最小手順でDryRun検証する"
