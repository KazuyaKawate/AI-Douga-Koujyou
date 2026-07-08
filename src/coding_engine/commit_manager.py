from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT


class CommitManager:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root).resolve(strict=False)

    def candidate(self, issue: str, diff: dict[str, Any], review: dict[str, Any], tests: dict[str, Any]) -> dict[str, Any]:
        changed = diff.get("changed_files", [])
        prefix = "feat(coding-engine)"
        if "fix" in issue.lower() or "bug" in issue.lower():
            prefix = "fix(coding-engine)"
        subject = f"{prefix}: automate AIOS coding loop"
        body = [
            issue.strip()[:400],
            "",
            f"Review: {review.get('status')}",
            f"Tests: {'passed' if tests.get('ok') else 'failed'}",
            f"Files: {', '.join(changed[:12])}",
        ]
        return {
            "ready": review.get("status") == "approved" and tests.get("ok", False),
            "subject": subject,
            "body": "\n".join(body).strip(),
            "changed_files": changed,
            "commands": [
                "git add " + " ".join(changed) if changed else "git add <files>",
                f'git commit -m "{subject}"',
            ],
            "status": self.status(),
        }

    def status(self) -> str:
        try:
            completed = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=15,
                shell=False,
            )
            return completed.stdout.strip()
        except Exception as exc:
            return str(exc)
