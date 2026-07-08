from __future__ import annotations

import json
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.business_engine.manager import BusinessEngineStore
from src.self_builder.knowledge_manager import load_knowledge, save_knowledge
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import save_json_atomic


TERMINAL_LOG_PATH = PROJECT_ROOT / "config" / "self_builder_terminal_logs.json"
DEFAULT_TIMEOUT_SECONDS = 120
ALLOWED_ROOT_COMMANDS = {"python", "pytest", "git", "npm", "uv", "docker"}
ALLOWED_GIT_SUBCOMMANDS = {"status", "diff", "log", "show", "branch", "commit"}
BLOCKED_TOKENS = {"rm", "del", "erase", "format", "reset", "checkout", "clean", "push", "force", "--force"}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _split_command(command: str) -> list[str]:
    return shlex.split(command.strip(), posix=False)


def load_terminal_logs(path: str | Path = TERMINAL_LOG_PATH) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def save_terminal_log(entry: dict[str, Any], path: str | Path = TERMINAL_LOG_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    logs = load_terminal_logs(p)
    logs.insert(0, entry)
    save_json_atomic(p, logs)


def command_policy(command: str) -> dict[str, Any]:
    parts = _split_command(command)
    root = Path(parts[0]).name.lower() if parts else ""
    if root.endswith(".exe"):
        root = root[:-4]
    blocked = sorted(token for token in BLOCKED_TOKENS if token in {part.lower() for part in parts})
    allowed = bool(parts) and root in ALLOWED_ROOT_COMMANDS and not blocked
    reason = "許可コマンドです。"
    if not parts:
        reason = "コマンドが空です。"
    elif root not in ALLOWED_ROOT_COMMANDS:
        reason = f"{root} は許可されていません。"
    elif blocked:
        reason = f"危険なトークンを含みます: {', '.join(blocked)}"
    elif root == "git":
        subcommand = parts[1].lower() if len(parts) > 1 else ""
        allowed = subcommand in ALLOWED_GIT_SUBCOMMANDS
        if not allowed:
            reason = f"git {subcommand} は許可されていません。"
    return {
        "allowed": allowed,
        "root": root,
        "parts": parts,
        "reason": reason,
    }


def terminal_plan(
    command: str,
    *,
    safe_mode: bool = True,
    confirmed: bool = False,
    agent: str = "",
    task_id: str = "",
) -> dict[str, Any]:
    command = command.strip()
    policy = command_policy(command)
    mode = "safe" if safe_mode else "execute"
    status = "safe_mode" if safe_mode else ("ready" if confirmed and policy["allowed"] else "needs_confirmation")
    return {
        "run_id": f"tr-{uuid4().hex[:10]}",
        "task_id": task_id,
        "agent": agent,
        "command": command,
        "mode": mode,
        "safe_mode": safe_mode,
        "confirmed": confirmed,
        "allowed": policy["allowed"],
        "policy": policy,
        "status": status,
        "stdout": "",
        "stderr": "",
        "exit_code": None,
        "created_at": _now(),
        "updated_at": _now(),
    }


def run_terminal(
    command: str,
    *,
    safe_mode: bool | None = None,
    dry_run: bool | None = None,
    confirmed: bool = False,
    agent: str = "",
    task_id: str = "",
    cwd: str | Path = PROJECT_ROOT,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    log_path: str | Path = TERMINAL_LOG_PATH,
    business_store: BusinessEngineStore | None = None,
) -> dict[str, Any]:
    if safe_mode is None:
        safe_mode = True if dry_run is None else bool(dry_run)
    entry = terminal_plan(command, safe_mode=safe_mode, confirmed=confirmed, agent=agent, task_id=task_id)
    if safe_mode:
        entry["status"] = "dry_run"
        entry["stdout"] = f"Safe Mode: {command}"
    elif not entry["allowed"] or not confirmed:
        entry["status"] = "blocked"
        entry["stderr"] = "安全確認または許可コマンド条件を満たしていません。"
    else:
        entry = _execute(entry, cwd=cwd, timeout_seconds=timeout_seconds)
    if entry["status"] == "completed":
        _save_terminal_success_to_knowledge(entry)
        _notify_business_engine(entry, business_store)
    save_terminal_log(entry, log_path)
    return entry


def retry_terminal_run(entry: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    safe_mode = bool(kwargs.pop("safe_mode", entry.get("safe_mode", True)))
    confirmed = bool(kwargs.pop("confirmed", entry.get("confirmed", False)))
    return run_terminal(
        str(entry.get("command", "")),
        safe_mode=safe_mode,
        confirmed=confirmed,
        agent=str(entry.get("agent", "")),
        task_id=str(entry.get("task_id", "")),
        **kwargs,
    )


def stop_terminal_run(run_id: str, path: str | Path = TERMINAL_LOG_PATH) -> dict[str, Any] | None:
    logs = load_terminal_logs(path)
    for entry in logs:
        if entry.get("run_id") == run_id:
            entry["status"] = "stopped"
            entry["stderr"] = "ユーザー操作で停止しました。"
            entry["updated_at"] = _now()
            save_json_atomic(Path(path), logs)
            return entry
    return None


def terminal_result_to_debug(entry: dict[str, Any]) -> dict[str, Any]:
    failed = entry.get("status") in {"failed", "blocked", "timeout"} or int(entry.get("exit_code") or 0) != 0
    return {
        "receiver": "Debug",
        "status": "Failed" if failed else "Completed",
        "run_id": entry.get("run_id", ""),
        "command": entry.get("command", ""),
        "log_analysis": (entry.get("stderr") or entry.get("stdout") or "")[:1000],
        "cause": "コマンドが失敗またはブロックされました。" if failed else "コマンドは成功しました。",
        "fix_candidates": ["Safe Modeで再確認", "許可コマンドへ分解", "Debug AgentへMission返却"],
        "created_at": _now(),
    }


def _execute(entry: dict[str, Any], *, cwd: str | Path, timeout_seconds: int) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            entry["policy"]["parts"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
        )
        entry["stdout"] = completed.stdout
        entry["stderr"] = completed.stderr
        entry["exit_code"] = completed.returncode
        entry["status"] = "completed" if completed.returncode == 0 else "failed"
    except subprocess.TimeoutExpired as exc:
        entry["stdout"] = exc.stdout or ""
        entry["stderr"] = exc.stderr or f"Timeout after {timeout_seconds}s"
        entry["exit_code"] = 124
        entry["status"] = "timeout"
    except Exception as exc:
        entry["stderr"] = str(exc)
        entry["exit_code"] = 1
        entry["status"] = "failed"
    entry["updated_at"] = _now()
    return entry


def _save_terminal_success_to_knowledge(entry: dict[str, Any]) -> None:
    knowledge = load_knowledge()
    knowledge.setdefault("history", []).insert(
        0,
        {
            "history_id": f"hist-{uuid4().hex[:10]}",
            "type": "terminal_success",
            "task_id": entry.get("task_id", ""),
            "agent": entry.get("agent", ""),
            "command": entry.get("command", ""),
            "exit_code": entry.get("exit_code"),
            "created_at": _now(),
        },
    )
    save_knowledge(knowledge)


def _notify_business_engine(entry: dict[str, Any], store: BusinessEngineStore | None) -> None:
    target = store or BusinessEngineStore()
    target.record_execution(
        entry.get("run_id", ""),
        "completed",
        f"Terminal Runner completed: {entry.get('command', '')}",
    )
