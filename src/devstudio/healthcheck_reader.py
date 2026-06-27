"""healthcheck_reader — Run and parse health check for Development Studio.

Executes scripts/check_project.py only when explicitly invoked.
Never runs automatically.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

ROOT        = Path(__file__).parent.parent.parent
SCRIPT_PATH = ROOT / "scripts" / "check_project.py"


def run_healthcheck() -> dict:
    if not SCRIPT_PATH.exists():
        return {
            "available": False,
            "ok": False,
            "output": "scripts/check_project.py not found.",
            "status_label": "unavailable",
        }
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        output = result.stdout + (result.stderr if result.stderr else "")
        ok = result.returncode == 0
        return {
            "available": True,
            "ok": ok,
            "output": output,
            "status_label": "OK" if ok else "NG",
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "available": True,
            "ok": False,
            "output": "Health check timed out (30s).",
            "status_label": "timeout",
        }
    except Exception as exc:
        return {
            "available": True,
            "ok": False,
            "output": f"Error: {exc}",
            "status_label": "error",
        }


def get_script_exists() -> bool:
    return SCRIPT_PATH.exists()
