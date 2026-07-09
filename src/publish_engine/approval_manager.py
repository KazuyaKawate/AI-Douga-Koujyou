from __future__ import annotations

import re
from typing import Any

from src.approval.risk_analyzer import analyze_content_risk


SECRET_RE = re.compile(r"(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]+", re.IGNORECASE)
NG_WORDS = ("必ず儲かる", "絶対稼げる", "無断転載", "違法", "グレー")


class ApprovalManager:
    def review(self, item: dict[str, Any]) -> dict[str, Any]:
        content = item.get("content", {})
        text = "\n".join(str(content.get(key, "")) for key in ("title", "text", "body", "description", "cta"))
        risks = analyze_content_risk(text, str(content.get("type", "")))
        issues = []
        if SECRET_RE.search(text):
            issues.append({"code": "secret_leak", "severity": "critical", "label": "Secret-like value detected"})
        for word in NG_WORDS:
            if word in text:
                issues.append({"code": "ng_word", "severity": "critical", "label": f"NG word: {word}"})
        all_issues = risks + issues
        approved = not any(issue.get("severity") == "critical" for issue in all_issues)
        return {
            "status": "approved" if approved else "rejected",
            "requires_review": True,
            "issues": all_issues,
            "api_key_protected": True,
            "secret_publication_forbidden": True,
        }

    @staticmethod
    def approve(item: dict[str, Any], reviewer: str = "AIOS") -> dict[str, Any]:
        return {"status": "approved", "reviewer": reviewer, "approved_at": __import__("datetime").datetime.now().isoformat(timespec="seconds")}
