from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


ENV_KEYS = {
    "note": ("NOTE_ACCOUNT_ID", "NOTE_API_TOKEN"),
    "threads": ("THREADS_ACCOUNT_ID", "THREADS_ACCESS_TOKEN"),
    "website": ("WEBSITE_BASE_URL", "WEBSITE_DEPLOY_TOKEN"),
}
LAUNCH_CHECKLIST_PATH = PROJECT_ROOT / "config" / "launch_checklist.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}****{value[-2:]}"


class ProductionConnectionManager:
    def __init__(self, root: str | Path = PROJECT_ROOT, env_path: str | Path | None = None) -> None:
        self.root = Path(root)
        self.env_path = Path(env_path) if env_path else self.root / ".env"
        self.checklist_path = self.root / "config" / "launch_checklist.json"

    def save_connections(self, payload: dict[str, dict[str, str]]) -> dict[str, Any]:
        updates: dict[str, str] = {}
        for channel, keys in ENV_KEYS.items():
            values = payload.get(channel, {})
            for key in keys:
                value = str(values.get(key, "")).strip()
                if value:
                    updates[key] = value
        if updates:
            self._write_env(updates)
        health = self.run_health_check()
        connected = bool(health.get("production_connected"))
        checklist = self.update_launch_checklist(connected, health)
        return {
            "saved": sorted(updates),
            "masked": {key: mask_secret(value) for key, value in updates.items()},
            "health": health,
            "launch_checklist": checklist,
            "production_ready": connected,
        }

    def current_status(self) -> dict[str, Any]:
        env = self._read_env()
        connections = {}
        for channel, keys in ENV_KEYS.items():
            connections[channel] = {
                "connected": all(bool(env.get(key)) for key in keys),
                "fields": {key: mask_secret(env.get(key, "")) for key in keys},
            }
        health = self.run_health_check()
        checklist = load_json(self.checklist_path, default={}) or {}
        return {
            "connections": connections,
            "health": health,
            "launch_checklist": checklist,
            "production_ready": bool(health.get("production_connected")),
        }

    def run_health_check(self) -> dict[str, Any]:
        script = self.root / "scripts" / "health_check.py"
        if not script.exists():
            return {"ok": False, "production_connected": False, "error": "scripts/health_check.py not found"}
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=self.root,
            text=True,
            capture_output=True,
            timeout=30,
            env={**os.environ, "AIOS_ENV_PATH": str(self.env_path)},
        )
        output = f"{completed.stdout}\n{completed.stderr}"
        connected = completed.returncode == 0 and "Production Connected" in output
        return {
            "ok": completed.returncode == 0,
            "production_connected": connected,
            "status": "Production Connected" if connected else "Production Not Connected",
            "returncode": completed.returncode,
        }

    def update_launch_checklist(self, connected: bool, health: dict[str, Any]) -> dict[str, Any]:
        data = load_json(self.checklist_path, default={}) or {}
        data.setdefault("items", {})
        data["items"]["production_connections"] = {
            "status": "done" if connected else "pending",
            "label": "Production Connections",
            "detail": health.get("status", ""),
            "updated_at": _now(),
        }
        data["production_ready"] = connected
        data["updated_at"] = _now()
        save_json_atomic(self.checklist_path, data)
        return data

    def _read_env(self) -> dict[str, str]:
        values: dict[str, str] = {}
        if not self.env_path.exists():
            return values
        for line in self.env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
        return values

    def _write_env(self, updates: dict[str, str]) -> None:
        self.env_path.parent.mkdir(parents=True, exist_ok=True)
        lines = self.env_path.read_text(encoding="utf-8", errors="replace").splitlines() if self.env_path.exists() else []
        seen: set[str] = set()
        output = []
        for line in lines:
            key = line.split("=", 1)[0].strip() if "=" in line else ""
            if key in updates and not line.lstrip().startswith("#"):
                output.append(f"{key}={updates[key]}")
                seen.add(key)
            else:
                output.append(line)
        for key, value in updates.items():
            if key not in seen:
                output.append(f"{key}={value}")
        self.env_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
