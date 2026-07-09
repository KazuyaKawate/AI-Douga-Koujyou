from __future__ import annotations

import re
from pathlib import Path
from typing import Any


FORBIDDEN_PATH_PATTERNS = (
    re.compile(r"(^|/)\.env($|\.)", re.IGNORECASE),
    re.compile(r"(^|/)(credentials|secrets)(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)release/production(/|$)", re.IGNORECASE),
)
FORBIDDEN_TEXT = (
    "api key",
    "apikey",
    "secret",
    "credentials",
    "本番投稿",
    "live publish",
    "publish now",
    "動画自動作成",
    "動画生成",
    "大型リファクタ",
    "全面刷新",
    "git reset",
    "git push --force",
)


class CommanderGuard:
    def evaluate(self, *, instruction: str, plan: dict[str, Any], dry_run: bool, approved: bool) -> dict[str, Any]:
        findings = []
        lowered = instruction.lower()
        for token in FORBIDDEN_TEXT:
            if token.lower() in lowered:
                findings.append(self._finding("forbidden_instruction", token, "high"))
        for file_path in plan.get("impacted_files", []):
            normalized = str(file_path).replace("\\", "/")
            if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
                findings.append(self._finding("unsafe_path", normalized, "high"))
            for pattern in FORBIDDEN_PATH_PATTERNS:
                if pattern.search(normalized):
                    findings.append(self._finding("forbidden_path", normalized, "high"))
        if not dry_run and not approved:
            findings.append(self._finding("approval_required", "Execute requires approved=True.", "high"))
        blocked = any(item["risk"] == "high" for item in findings)
        return {
            "ok": not blocked,
            "blocked": blocked,
            "findings": findings,
            "default_dry_run": True,
            "execute_allowed": bool(approved and not blocked),
            "policy": [
                "DryRun first",
                "Apply only after approval",
                "No secrets/env/credentials",
                "No live publish",
                "No production direct changes",
                "No large refactor",
            ],
        }

    @staticmethod
    def _finding(kind: str, message: str, risk: str) -> dict[str, str]:
        return {"type": kind, "message": message, "risk": risk}
