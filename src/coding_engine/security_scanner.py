from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT


SECRET_PATTERNS = {
    "env_file": re.compile(r"(^|/)\.env($|\.)", re.IGNORECASE),
    "token": re.compile(r"\b(token|access_token|refresh_token)\b\s*[:=]", re.IGNORECASE),
    "password": re.compile(r"\b(password|passwd|pwd)\b\s*[:=]", re.IGNORECASE),
    "secret": re.compile(r"\b(secret|client_secret)\b\s*[:=]", re.IGNORECASE),
    "api_key": re.compile(r"\b(api[_-]?key|apikey)\b\s*[:=]", re.IGNORECASE),
}
PUBLIC_PREFIXES = ("pages/", "src/official_site/", "docs/", "README")
BLOCKED_COMMAND_TOKENS = {"rm", "del", "erase", "format", "reset", "checkout", "clean", "push", "--force", "curl", "wget"}


class SecurityScanner:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root).resolve(strict=False)

    def scan(self, files: list[str] | None = None, commands: list[str] | None = None) -> dict[str, Any]:
        findings = []
        for relative in files or self._default_files():
            findings.extend(self.scan_file(relative))
        command_findings = [self.scan_command(command) for command in commands or []]
        command_findings = [item for item in command_findings if item.get("risk") != "low"]
        all_findings = findings + command_findings
        return {
            "ok": not any(item.get("risk") == "high" for item in all_findings),
            "findings": all_findings,
            "high_count": sum(1 for item in all_findings if item.get("risk") == "high"),
            "warning_count": sum(1 for item in all_findings if item.get("risk") in {"medium", "high"}),
        }

    def scan_file(self, relative_path: str) -> list[dict[str, Any]]:
        normalized = relative_path.replace("\\", "/")
        path = self.root / relative_path
        findings = []
        if SECRET_PATTERNS["env_file"].search(normalized):
            findings.append(self._finding("env_file", relative_path, 0, ".env file detected", "high"))
        if not path.exists() or not path.is_file() or path.stat().st_size > 500_000:
            return findings
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return findings
        for index, line in enumerate(text.splitlines(), start=1):
            for name, pattern in SECRET_PATTERNS.items():
                if name == "env_file":
                    continue
                if pattern.search(line):
                    risk = "high" if self._is_public_path(normalized) else "medium"
                    findings.append(self._finding(name, relative_path, index, "Potential secret-like assignment", risk))
        return findings

    def scan_command(self, command: str) -> dict[str, Any]:
        try:
            parts = [part.lower() for part in shlex.split(command, posix=False)]
        except ValueError:
            parts = command.lower().split()
        blocked = sorted(token for token in BLOCKED_COMMAND_TOKENS if token in parts)
        return {
            "type": "dangerous_command",
            "command": command,
            "blocked_tokens": blocked,
            "risk": "high" if blocked else "low",
            "message": "Dangerous command token detected." if blocked else "Command looks low risk.",
        }

    def _default_files(self) -> list[str]:
        files = []
        for path in self.root.rglob("*"):
            if not path.is_file() or ".git" in path.parts or "venv" in path.parts:
                continue
            relative = str(path.relative_to(self.root)).replace("\\", "/")
            if relative.startswith(("src/", "pages/", "config/", "docs/")) or relative in {".env", ".env.example", "README.md"}:
                files.append(relative)
            if len(files) >= 800:
                break
        return files

    @staticmethod
    def _is_public_path(path: str) -> bool:
        return path.startswith(PUBLIC_PREFIXES)

    @staticmethod
    def _finding(kind: str, path: str, line: int, message: str, risk: str) -> dict[str, Any]:
        return {"type": kind, "path": path, "line": line, "message": message, "risk": risk}
