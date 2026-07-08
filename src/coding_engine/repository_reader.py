from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT
from src.utils.path_safety import safe_resolve_path, workspace_relative_path


TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".ini",
    ".cfg",
    ".css",
    ".html",
    ".js",
    ".ts",
    ".tsx",
}


class RepositoryReader:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root).resolve(strict=False)

    def analyze(self, issue: str = "", target_files: list[str] | None = None) -> dict[str, Any]:
        files = self.list_files()
        selected = self.select_relevant_files(issue, target_files, files)
        return {
            "root": str(self.root),
            "file_count": len(files),
            "files": files[:500],
            "selected_files": selected,
            "snapshots": [self.read_file(path) for path in selected[:12]],
            "git_status": self.git_status(),
        }

    def list_files(self) -> list[str]:
        try:
            completed = subprocess.run(
                ["git", "ls-files"],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=15,
                shell=False,
            )
            if completed.returncode == 0:
                return [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        except Exception:
            pass
        return [
            str(workspace_relative_path(self.root, path)).replace("\\", "/")
            for path in self.root.rglob("*")
            if path.is_file() and ".git" not in path.parts
        ]

    def select_relevant_files(
        self,
        issue: str,
        target_files: list[str] | None,
        files: list[str] | None = None,
    ) -> list[str]:
        all_files = files or self.list_files()
        explicit = [path for path in target_files or [] if path in all_files or (self.root / path).exists()]
        if explicit:
            return explicit
        issue_lower = issue.lower()
        tokens = [token.strip(".,:/\\[]()").lower() for token in issue_lower.split() if len(token) >= 4]
        scored: list[tuple[int, str]] = []
        for file_path in all_files:
            path_lower = file_path.lower().replace("\\", "/")
            score = sum(3 for token in tokens if token in path_lower)
            if "coding" in issue_lower and "coding_engine" in path_lower:
                score += 10
            if "business" in issue_lower and "business_engine" in path_lower:
                score += 4
            if "mission" in issue_lower and ("self_builder" in path_lower or "autonomous" in path_lower):
                score += 4
            if score:
                scored.append((score, file_path))
        ranked = [path for _, path in sorted(scored, key=lambda item: (-item[0], item[1]))]
        return ranked[:20]

    def read_file(self, relative_path: str, max_chars: int = 12000) -> dict[str, Any]:
        path = safe_resolve_path(self.root, relative_path)
        if not path.exists() or not path.is_file():
            return {"path": relative_path, "exists": False, "content": ""}
        if path.suffix.lower() not in TEXT_SUFFIXES:
            return {"path": relative_path, "exists": True, "content": "", "skipped": "non_text"}
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="utf-8", errors="replace")
        return {
            "path": str(workspace_relative_path(self.root, path)).replace("\\", "/"),
            "exists": True,
            "content": content[:max_chars],
            "truncated": len(content) > max_chars,
        }

    def git_status(self) -> str:
        try:
            completed = subprocess.run(
                ["git", "status", "--short"],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=15,
                shell=False,
            )
            return completed.stdout.strip() if completed.returncode == 0 else completed.stderr.strip()
        except Exception as exc:
            return str(exc)
