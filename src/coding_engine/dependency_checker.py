from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT


STDLIB_MODULES = getattr(sys, "stdlib_module_names", set())
LOCAL_TOP_LEVEL = {"src", "pages", "tests", "dashboard", "scripts"}


class DependencyChecker:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root).resolve(strict=False)

    def check(self, *, run_project_check: bool = False) -> dict[str, Any]:
        requirements = self.read_requirements()
        imports = self.collect_imports()
        missing = self.missing_imports(imports, requirements)
        outdated_candidates = self.outdated_candidates(requirements)
        project_check = self.run_check_project() if run_project_check else {"status": "skipped"}
        return {
            "ok": not missing and project_check.get("ok", True) is not False,
            "requirements": requirements,
            "imports": sorted(imports),
            "missing_imports": missing,
            "outdated_candidates": outdated_candidates,
            "project_check": project_check,
        }

    def read_requirements(self) -> dict[str, str]:
        path = self.root / "requirements.txt"
        requirements: dict[str, str] = {}
        if not path.exists():
            return requirements
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            cleaned = line.strip()
            if not cleaned or cleaned.startswith("#"):
                continue
            name = cleaned
            version = ""
            for sep in ("==", ">=", "<=", "~=", ">"):
                if sep in cleaned:
                    name, version = cleaned.split(sep, 1)
                    break
            requirements[self._normalize_package(name)] = version.strip()
        return requirements

    def collect_imports(self) -> set[str]:
        imports: set[str] = set()
        for folder in ("src", "pages", "tests"):
            base = self.root / folder
            if not base.exists():
                continue
            for path in base.rglob("*.py"):
                if "venv" in path.parts:
                    continue
                try:
                    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        imports.add(node.module.split(".")[0])
        return imports

    def missing_imports(self, imports: set[str], requirements: dict[str, str]) -> list[str]:
        installed_names = set(requirements)
        missing = []
        for name in sorted(imports):
            normalized = self._normalize_package(name)
            if name in LOCAL_TOP_LEVEL or name in STDLIB_MODULES:
                continue
            if normalized in installed_names:
                continue
            if importlib.util.find_spec(name) is None:
                missing.append(name)
        return missing

    def outdated_candidates(self, requirements: dict[str, str]) -> list[dict[str, Any]]:
        candidates = []
        for package, version in requirements.items():
            if not version:
                candidates.append({"package": package, "reason": "unpinned", "risk": "medium"})
            elif any(token in version for token in ("*", "dev", "rc")):
                candidates.append({"package": package, "version": version, "reason": "unstable_pin", "risk": "medium"})
        return candidates

    def run_check_project(self) -> dict[str, Any]:
        script = self.root / "scripts" / "check_project.py"
        if not script.exists():
            return {"status": "missing", "ok": False, "stdout": "", "stderr": "scripts/check_project.py not found"}
        try:
            completed = subprocess.run(
                [sys.executable, str(script)],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=120,
                shell=False,
            )
            return {
                "status": "completed" if completed.returncode == 0 else "failed",
                "ok": completed.returncode == 0,
                "exit_code": completed.returncode,
                "stdout": completed.stdout[-8000:],
                "stderr": completed.stderr[-4000:],
            }
        except subprocess.TimeoutExpired as exc:
            return {"status": "timeout", "ok": False, "exit_code": 124, "stdout": exc.stdout or "", "stderr": "timeout"}
        except Exception as exc:
            return {"status": "failed", "ok": False, "exit_code": 1, "stdout": "", "stderr": str(exc)}

    @staticmethod
    def _normalize_package(name: str) -> str:
        aliases = {"PIL": "pillow", "cv2": "opencv-python", "sklearn": "scikit-learn", "yaml": "pyyaml"}
        return aliases.get(name, name).strip().lower().replace("_", "-")
