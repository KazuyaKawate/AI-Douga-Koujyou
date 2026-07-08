from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4


SUPPORTED_BRIDGES = ["Codex", "Gemini CLI", "Claude Code"]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def bridge_prompt(provider: str, task: dict[str, Any], prompt: str) -> dict[str, Any]:
    if provider not in SUPPORTED_BRIDGES:
        raise ValueError(f"Unsupported AI Bridge: {provider}")
    payload = {
        "bridge_id": f"br-{uuid4().hex[:10]}",
        "provider": provider,
        "task_id": task.get("task_id", ""),
        "format": "aios_execution_prompt_v1",
        "prompt": prompt.strip(),
        "target_files": task.get("target_files", []),
        "created_at": _now(),
        "status": "queued",
        "result": "Execution Queueへ戻すための送信ペイロードを生成しました。",
    }
    return payload


def bridge_result_to_execution(execution: dict[str, Any], bridge_result: dict[str, Any]) -> dict[str, Any]:
    execution.setdefault("bridge_results", [])
    execution["bridge_results"].insert(0, bridge_result)
    execution["updated_at"] = _now()
    return execution

