from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT


class CodingTestRunner:
    def __init__(self, root: str | Path = PROJECT_ROOT) -> None:
        self.root = Path(root).resolve(strict=False)

    def run(self, *, pytest_args: list[str] | None = None, compile: bool = True) -> dict[str, Any]:
        results = []
        results.append(self._run([sys.executable, "-m", "pytest", *(pytest_args or ["-q"])], timeout=180))
        if compile:
            results.append(self._run([sys.executable, "-m", "compileall", "src", "pages"], timeout=180))
        return {
            "ok": all(item.get("ok") for item in results),
            "results": results,
        }

    def dry_run_plan(self) -> dict[str, Any]:
        return {
            "ok": True,
            "results": [
                {"command": f"{sys.executable} -m pytest -q", "status": "planned"},
                {"command": f"{sys.executable} -m compileall src pages", "status": "planned"},
            ],
        }

    def _run(self, command: list[str], timeout: int) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                command,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )
            return {
                "command": " ".join(command),
                "ok": completed.returncode == 0,
                "exit_code": completed.returncode,
                "stdout": completed.stdout[-6000:],
                "stderr": completed.stderr[-6000:],
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "command": " ".join(command),
                "ok": False,
                "exit_code": 124,
                "stdout": (exc.stdout or "")[-6000:],
                "stderr": f"Timeout after {timeout}s",
            }
        except Exception as exc:
            return {"command": " ".join(command), "ok": False, "exit_code": 1, "stdout": "", "stderr": str(exc)}
