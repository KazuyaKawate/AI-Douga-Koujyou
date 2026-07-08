from __future__ import annotations

import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any

from src.ai.response import AIResponse
from src.ai.router import get_router
from src.ai.task import AITask, TaskType


PROVIDER_PRIORITY = ["ollama", "gemini_cli", "claude_cli", "openai", "ai_router"]


@dataclass
class ProviderResult:
    ok: bool
    content: str
    provider: str
    duration_ms: int = 0
    error: str = ""


class CodingProviderRouter:
    """Local-first coding LLM router with safe CLI fallbacks."""

    def __init__(self, providers: list[str] | None = None, timeout_seconds: int = 90) -> None:
        self.providers = providers or PROVIDER_PRIORITY
        self.timeout_seconds = max(int(timeout_seconds or 90), 5)

    def complete(self, prompt: str, *, system_prompt: str = "", retries: int = 1) -> ProviderResult:
        last_error = ""
        for provider in self.providers:
            for attempt in range(max(int(retries or 1), 1)):
                result = self._complete_once(provider, prompt, system_prompt)
                if result.ok:
                    return result
                last_error = result.error or f"{provider} failed on attempt {attempt + 1}"
        return ProviderResult(False, "", "none", error=last_error or "No provider returned a result.")

    def status(self) -> list[dict[str, Any]]:
        return [
            {"provider": provider, "available": self._is_available(provider)}
            for provider in self.providers
        ]

    def health_probe(self, timeout_seconds: int = 5) -> list[dict[str, Any]]:
        timeout = max(1, min(int(timeout_seconds or 5), 15))
        return [self._probe(provider, timeout) for provider in self.providers]

    def _complete_once(self, provider: str, prompt: str, system_prompt: str) -> ProviderResult:
        started = time.monotonic()
        if provider == "ollama":
            return self._run_cli(
                ["ollama", "run", "codellama"],
                self._join_prompt(prompt, system_prompt),
                provider,
                started,
            )
        if provider == "gemini_cli":
            return self._run_cli(["gemini", "-p", self._join_prompt(prompt, system_prompt)], "", provider, started)
        if provider == "claude_cli":
            return self._run_cli(["claude", "-p", self._join_prompt(prompt, system_prompt)], "", provider, started)
        if provider in {"openai", "ai_router"}:
            return self._run_ai_router(prompt, system_prompt, started)
        return ProviderResult(False, "", provider, error=f"Unsupported provider: {provider}")

    def _run_ai_router(self, prompt: str, system_prompt: str, started: float) -> ProviderResult:
        try:
            response: AIResponse = get_router().route(
                AITask(task_type=TaskType.CODING, prompt=prompt, system_prompt=system_prompt)
            )
            return ProviderResult(
                bool(response.ok),
                response.content,
                response.provider or "ai_router",
                int((time.monotonic() - started) * 1000),
                response.error or "",
            )
        except Exception as exc:
            return ProviderResult(False, "", "ai_router", int((time.monotonic() - started) * 1000), str(exc))

    def _run_cli(self, command: list[str], stdin: str, provider: str, started: float) -> ProviderResult:
        executable = command[0]
        resolved_command = self._resolved_command(command)
        if resolved_command is None:
            return ProviderResult(False, "", provider, error=f"{executable} is not installed.")
        try:
            completed = subprocess.run(
                resolved_command,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            return ProviderResult(False, "", provider, int((time.monotonic() - started) * 1000), "Provider timed out.")
        except Exception as exc:
            return ProviderResult(False, "", provider, int((time.monotonic() - started) * 1000), str(exc))
        return ProviderResult(
            completed.returncode == 0 and bool(completed.stdout.strip()),
            completed.stdout,
            provider,
            int((time.monotonic() - started) * 1000),
            completed.stderr.strip(),
        )

    def _is_available(self, provider: str) -> bool:
        if provider == "ollama":
            return shutil.which("ollama") is not None
        if provider == "gemini_cli":
            return shutil.which("gemini") is not None
        if provider == "claude_cli":
            return shutil.which("claude") is not None
        if provider in {"openai", "ai_router"}:
            try:
                return bool(get_router().list_providers())
            except Exception:
                return False
        return False

    def _probe(self, provider: str, timeout: int) -> dict[str, Any]:
        if provider == "ollama":
            return self._probe_cli(provider, ["ollama", "version"], timeout, list_command=["ollama", "list"])
        if provider == "gemini_cli":
            return self._probe_cli(provider, ["gemini", "--version"], timeout)
        if provider == "claude_cli":
            return self._probe_cli(provider, ["claude", "--version"], timeout)
        if provider in {"openai", "ai_router"}:
            started = time.monotonic()
            try:
                providers = get_router().list_providers()
                return {
                    "provider": provider,
                    "status": "ready" if providers else "missing",
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "detail": f"{len(providers)} providers configured" if providers else "No AI router providers configured.",
                }
            except Exception as exc:
                return {
                    "provider": provider,
                    "status": "error",
                    "duration_ms": int((time.monotonic() - started) * 1000),
                    "detail": str(exc)[:240],
                }
        return {"provider": provider, "status": "missing", "duration_ms": 0, "detail": "Unsupported provider."}

    def _probe_cli(
        self,
        provider: str,
        command: list[str],
        timeout: int,
        *,
        list_command: list[str] | None = None,
    ) -> dict[str, Any]:
        executable = command[0]
        resolved_command = self._resolved_command(command)
        if resolved_command is None:
            return {"provider": provider, "status": "missing", "duration_ms": 0, "detail": f"{executable} is not installed."}
        started = time.monotonic()
        try:
            completed = subprocess.run(resolved_command, capture_output=True, text=True, timeout=timeout, shell=False)
        except subprocess.TimeoutExpired:
            return {
                "provider": provider,
                "status": "timeout",
                "duration_ms": int((time.monotonic() - started) * 1000),
                "detail": f"{' '.join(command)} timed out.",
            }
        except Exception as exc:
            return {
                "provider": provider,
                "status": "error",
                "duration_ms": int((time.monotonic() - started) * 1000),
                "detail": str(exc)[:240],
            }

        detail = (completed.stdout or completed.stderr or "").strip()[:500]
        status = "ready" if completed.returncode == 0 else "error"
        result: dict[str, Any] = {
            "provider": provider,
            "status": status,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "detail": detail,
        }
        if list_command and status == "ready":
            result["models"] = self._probe_list(list_command, timeout)
        return result

    @staticmethod
    def _probe_list(command: list[str], timeout: int) -> dict[str, Any]:
        try:
            resolved = CodingProviderRouter._resolved_command(command)
            if resolved is None:
                return {"status": "missing", "detail": f"{command[0]} is not installed.", "items": []}
            completed = subprocess.run(resolved, capture_output=True, text=True, timeout=timeout, shell=False)
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "detail": f"{' '.join(command)} timed out.", "items": []}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)[:240], "items": []}
        lines = [line for line in completed.stdout.splitlines() if line.strip()]
        return {
            "status": "ready" if completed.returncode == 0 else "error",
            "detail": (completed.stdout or completed.stderr or "").strip()[:500],
            "items": lines[1:20] if len(lines) > 1 else [],
        }

    @staticmethod
    def _resolved_command(command: list[str]) -> list[str] | None:
        executable = shutil.which(command[0])
        if executable is None:
            return None
        if executable.lower().endswith(".ps1"):
            powershell = shutil.which("pwsh") or shutil.which("powershell")
            if powershell is None:
                return None
            return [powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", executable, *command[1:]]
        return [executable, *command[1:]]

    @staticmethod
    def _join_prompt(prompt: str, system_prompt: str) -> str:
        return f"{system_prompt.strip()}\n\n{prompt.strip()}".strip()
