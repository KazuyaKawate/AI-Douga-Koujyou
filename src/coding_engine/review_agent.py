from __future__ import annotations

from typing import Any

from src.core.development_constitution import evaluate_constitution_compliance


class CodingReviewAgent:
    def review(self, issue: str, plan: dict[str, Any], diff: dict[str, Any]) -> dict[str, Any]:
        diff_text = diff.get("content", "")
        risks = []
        if "subprocess" in diff_text and "shell=True" in diff_text:
            risks.append("shell=True usage detected")
        if "api_key" in diff_text.lower() or "secret" in diff_text.lower():
            risks.append("Potential secret handling change")
        if len(diff.get("changed_files", [])) > 12:
            risks.append("Large change set")
        compliance = evaluate_constitution_compliance(
            {
                "instruction": issue,
                "development_review": plan.get("constitution_review", {}),
                "diff": diff_text[:2000],
            }
        )
        approved = not risks and compliance.get("status") == "compliant"
        return {
            "status": "approved" if approved else "needs_attention",
            "risks": risks,
            "constitution_compliance": compliance,
            "summary": "Diff is acceptable for automated validation." if approved else "Review found items to check.",
        }
