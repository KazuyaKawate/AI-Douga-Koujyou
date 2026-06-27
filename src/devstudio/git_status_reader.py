"""git_status_reader — Read-only git status for Development Studio.

Safe commands only. No destructive operations.
"""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent


def _run(args: list[str]) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def get_git_status() -> dict:
    branch = _run(["git", "branch", "--show-current"])
    log_line = _run(["git", "log", "-1", "--format=%H|%s|%ai"])
    porcelain = _run(["git", "status", "--porcelain"])

    commit_hash = ""
    commit_subject = ""
    commit_date = ""
    if "|" in log_line:
        parts = log_line.split("|", 2)
        commit_hash    = parts[0][:12] if len(parts) > 0 else ""
        commit_subject = parts[1]      if len(parts) > 1 else ""
        commit_date    = parts[2][:19] if len(parts) > 2 else ""

    is_dirty = bool(porcelain)
    dirty_files = [line for line in porcelain.splitlines() if line.strip()] if porcelain else []

    in_git_repo = bool(branch or commit_hash)

    return {
        "in_git_repo": in_git_repo,
        "branch": branch or "(unknown)",
        "commit_hash": commit_hash,
        "commit_subject": commit_subject,
        "commit_date": commit_date,
        "is_dirty": is_dirty,
        "dirty_files": dirty_files,
        "dirty_count": len(dirty_files),
        "status_label": "dirty" if is_dirty else "clean",
    }
