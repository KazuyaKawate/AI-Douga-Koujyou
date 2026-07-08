from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.core.development_constitution import prioritize_improvements
from src.coding_engine.dependency_checker import DependencyChecker
from src.coding_engine.git_safety import GitSafetyAnalyzer
from src.coding_engine.security_scanner import SecurityScanner
from src.utils.config import PROJECT_ROOT


ISSUE_PATTERNS = {
    "TODO": re.compile(r"\bTODO\b", re.IGNORECASE),
    "FIXME": re.compile(r"\bFIXME\b", re.IGNORECASE),
    "pass": re.compile(r"^\s*pass\s*(#.*)?$", re.MULTILINE),
    "未実装": re.compile(r"未実装|未対応"),
    "placeholder": re.compile(r"placeholder|stub|仮実装", re.IGNORECASE),
}
REVENUE_PATH_HINTS = ("business_engine", "factories/note", "threads", "official_site", "aiceo", "pages/29", "pages/18")
SCAN_SUFFIXES = {".py", ".md", ".txt", ".json", ".yml", ".yaml"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class AutoIssueDetector:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root).resolve(strict=False)
        self.git = GitSafetyAnalyzer(self.root)
        self.security = SecurityScanner(self.root)
        self.dependencies = DependencyChecker(self.root)

    def scan(
        self,
        *,
        pytest_log: str = "",
        compile_log: str = "",
        streamlit_log: str = "",
        run_dependency_check: bool = False,
    ) -> dict[str, Any]:
        candidates = []
        candidates.extend(self.scan_source_markers())
        candidates.extend(self.parse_pytest_log(pytest_log))
        candidates.extend(self.parse_compile_log(compile_log))
        candidates.extend(self.parse_streamlit_log(streamlit_log))

        git_status = self.git.status()
        security = self.security.scan(files=[item["path"] for item in git_status.get("entries", [])])
        dependency = self.dependencies.check(run_project_check=run_dependency_check)

        candidates.extend(self._issues_from_git(git_status))
        candidates.extend(self._issues_from_security(security))
        candidates.extend(self._issues_from_dependency(dependency))

        ranked = self.rank(candidates)
        return {
            "scan_id": f"ais-{uuid4().hex[:10]}",
            "created_at": _now(),
            "issues": ranked,
            "suggested_next_fix": ranked[0] if ranked else {},
            "git_status": git_status,
            "security": security,
            "dependency": dependency,
            "summary": {
                "issue_count": len(ranked),
                "high_risk": sum(1 for item in ranked if item.get("risk") == "high"),
                "revenue_candidates": sum(1 for item in ranked if item.get("revenue_impact") == "high"),
            },
        }

    def scan_source_markers(self, max_files: int = 600) -> list[dict[str, Any]]:
        issues = []
        count = 0
        for path in self.root.rglob("*"):
            if count >= max_files:
                break
            if not path.is_file() or ".git" in path.parts or "venv" in path.parts or path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            relative = str(path.relative_to(self.root)).replace("\\", "/")
            if not relative.startswith(("src/", "pages/", "tests/", "docs/")):
                continue
            count += 1
            text = path.read_text(encoding="utf-8", errors="replace")
            for line_no, line in enumerate(text.splitlines(), start=1):
                for kind, pattern in ISSUE_PATTERNS.items():
                    if pattern.search(line):
                        issues.append(self._issue(kind, relative, line_no, line.strip()))
        return issues

    def parse_pytest_log(self, log: str) -> list[dict[str, Any]]:
        issues = []
        for line in log.splitlines():
            if "FAILED " in line or "ERROR " in line:
                path = self._extract_path(line)
                issues.append(
                    self._issue(
                        "pytest_failure",
                        path or "tests",
                        0,
                        line.strip(),
                        risk="high",
                        effort=30,
                    )
                )
        return issues

    def parse_compile_log(self, log: str) -> list[dict[str, Any]]:
        issues = []
        for line in log.splitlines():
            if "SyntaxError" in line or "IndentationError" in line or "Error compiling" in line:
                path = self._extract_path(line) or "src"
                issues.append(self._issue("compile_failure", path, 0, line.strip(), risk="high", effort=25))
        return issues

    def parse_streamlit_log(self, log: str) -> list[dict[str, Any]]:
        issues = []
        for line in log.splitlines():
            if any(token in line for token in ("Traceback", "ModuleNotFoundError", "ImportError", "StreamlitAPIException")):
                path = self._extract_path(line) or "pages"
                issues.append(self._issue("streamlit_failure", path, 0, line.strip(), risk="high", effort=35))
        return issues

    def rank(self, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scored = []
        seen = set()
        for issue in issues:
            key = (issue.get("type"), issue.get("path"), issue.get("line"), issue.get("message"))
            if key in seen:
                continue
            seen.add(key)
            scored.append(
                {
                    **issue,
                    "instruction": issue.get("title", issue.get("message", "")),
                    "estimated_revenue": issue.get("estimated_revenue", self._estimated_revenue(issue)),
                    "estimated_effort": issue.get("effort", 20),
                    "risk": issue.get("risk", "medium"),
                    "autonomy_score": 80 if issue.get("type") in {"TODO", "FIXME", "pass", "placeholder"} else 60,
                }
            )
        return prioritize_improvements(scored)

    def _issues_from_git(self, status: dict[str, Any]) -> list[dict[str, Any]]:
        issues = []
        for item in status.get("production_changes", []):
            issues.append(
                self._issue(
                    "production_change_approval",
                    item.get("path", ""),
                    0,
                    "Production-sensitive file changed; approval required.",
                    risk="high",
                    effort=10,
                )
            )
        return issues

    def _issues_from_security(self, security: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            self._issue(
                f"security_{finding.get('type')}",
                finding.get("path", finding.get("command", "")),
                int(finding.get("line", 0) or 0),
                finding.get("message", "Security finding"),
                risk=finding.get("risk", "medium"),
                effort=15,
            )
            for finding in security.get("findings", [])
        ]

    def _issues_from_dependency(self, dependency: dict[str, Any]) -> list[dict[str, Any]]:
        issues = []
        for name in dependency.get("missing_imports", []):
            issues.append(self._issue("missing_import", "requirements.txt", 0, f"Missing import dependency: {name}", risk="high", effort=20))
        for item in dependency.get("outdated_candidates", []):
            issues.append(self._issue("dependency_candidate", "requirements.txt", 0, f"Dependency pin review: {item.get('package')}", risk=item.get("risk", "medium"), effort=15))
        if dependency.get("project_check", {}).get("ok") is False:
            issues.append(self._issue("health_check_failure", "scripts/check_project.py", 0, "check_project.py reported failure", risk="high", effort=30))
        return issues

    def _issue(
        self,
        kind: str,
        path: str,
        line: int,
        message: str,
        *,
        risk: str | None = None,
        effort: int = 20,
    ) -> dict[str, Any]:
        revenue = self._revenue_impact(path, message)
        return {
            "issue_id": f"ai-{uuid4().hex[:10]}",
            "type": kind,
            "title": f"{kind}: {path}:{line}" if line else f"{kind}: {path}",
            "path": path,
            "line": line,
            "message": message[:500],
            "risk": risk or self._risk(kind, path),
            "effort": effort,
            "revenue_impact": revenue,
            "estimated_revenue": 18000 if revenue == "high" else 6000,
            "created_at": _now(),
        }

    @staticmethod
    def _revenue_impact(path: str, message: str) -> str:
        text = f"{path} {message}".lower().replace("\\", "/")
        return "high" if any(hint in text for hint in REVENUE_PATH_HINTS) or any(token in text for token in ("revenue", "roi", "収益", "初収益")) else "medium"

    @staticmethod
    def _risk(kind: str, path: str) -> str:
        lowered = f"{kind} {path}".lower()
        if any(token in lowered for token in ("security", "secret", ".env", "production", "failure")):
            return "high"
        return "low" if kind in {"TODO", "placeholder", "pass"} else "medium"

    @staticmethod
    def _estimated_revenue(issue: dict[str, Any]) -> int:
        return 18000 if issue.get("revenue_impact") == "high" else 6000

    @staticmethod
    def _extract_path(line: str) -> str:
        match = re.search(r"([A-Za-z0-9_./\\-]+\.py)", line)
        return match.group(1).replace("\\", "/") if match else ""
