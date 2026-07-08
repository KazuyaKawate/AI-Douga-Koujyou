from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT


class DiffManager:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root).resolve(strict=False)

    def diff(self, paths: list[str] | None = None, max_chars: int = 30000) -> dict[str, Any]:
        command = ["git", "diff", "--"] + (paths or [])
        try:
            completed = subprocess.run(
                command,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=30,
                shell=False,
            )
            text = completed.stdout if completed.returncode == 0 else completed.stderr
            return {
                "ok": completed.returncode == 0,
                "command": " ".join(command),
                "content": text[:max_chars],
                "truncated": len(text) > max_chars,
                "changed_files": self.changed_files(paths),
            }
        except Exception as exc:
            return {"ok": False, "command": " ".join(command), "content": "", "error": str(exc), "changed_files": []}

    def changed_files(self, paths: list[str] | None = None) -> list[str]:
        try:
            completed = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=15,
                shell=False,
            )
            if completed.returncode != 0:
                return []
            changed = [line[3:].strip().strip('"') for line in completed.stdout.splitlines() if line.strip()]
            if not paths:
                return changed
            normalized = {path.replace("\\", "/") for path in paths}
            return [path for path in changed if path.replace("\\", "/") in normalized]
        except Exception:
            return []
