from __future__ import annotations

from typing import Any

from src.core.development_constitution import evaluate_constitution_compliance, development_review


class QualityReviewer:
    def review(self, content: dict[str, Any]) -> dict[str, Any]:
        text = " ".join(str(value) for value in content.values())
        issues = []
        if len(text) < 80:
            issues.append("content_too_short")
        if "転載" in text and "独自" not in text:
            issues.append("copyright_risk")
        if "必ず儲かる" in text:
            issues.append("false_profit_claim")
        compliance = evaluate_constitution_compliance(
            {
                "instruction": "収益コンテンツ生成 note Threads affiliate SEO ROI",
                "development_review": development_review({"instruction": "収益最大化 ROI Content Factory note Threads affiliate SEO"}),
                "content": content,
            }
        )
        return {
            "status": "approved" if not issues and compliance.get("status") == "compliant" else "needs_revision",
            "issues": issues,
            "constitution_compliance": compliance,
        }
