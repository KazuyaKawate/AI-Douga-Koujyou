from __future__ import annotations

import os
import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterator

from src.providers.base_provider import BaseProvider, ProviderResult


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_DIR = ROOT / "logs" / "ai_runtime"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class GeminiCLIResult:
    ok: bool
    prompt: str
    response: str = ""
    error: str = ""
    command: list[str] = field(default_factory=list)
    duration_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_yen: int = 0
    attempts: int = 0
    timed_out: bool = False
    created_at: str = field(default_factory=_now)


class GeminiCLIProvider(BaseProvider):
    """Local Gemini CLI runtime provider.

    This provider shells out only to the locally installed Gemini CLI. It does
    not use OpenAI, Anthropic, Gemini SDKs, Google Workspace, or publishing APIs.
    """

    provider_id = "gemini_cli"
    name = "Gemini CLI"
    env_key = ""
    model = "gemini-cli-local"
    external = False

    def __init__(
        self,
        *,
        enabled: bool = True,
        test_mode: bool | None = None,
        command_path: str | None = None,
        timeout_seconds: int = 60,
        retries: int = 1,
        log_dir: str | Path = DEFAULT_LOG_DIR,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        super().__init__(enabled=enabled, test_mode=test_mode)
        self.command_path = command_path or self.detect_installation()
        self.timeout_seconds = max(int(timeout_seconds or 60), 1)
        self.retries = max(int(retries or 1), 1)
        self.log_dir = Path(log_dir)
        self.runner = runner
        self.last_result: GeminiCLIResult | None = None

    def detect_installation(self) -> str:
        found = shutil.which("gemini") or shutil.which("gemini.cmd") or shutil.which("gemini.ps1")
        if found:
            return found
        for path_dir in os.getenv("PATH", "").split(os.pathsep):
            candidate = Path(path_dir) / "gemini.ps1"
            if candidate.exists():
                return str(candidate)
        return ""

    def is_installed(self) -> bool:
        return bool(self.command_path)

    def is_available(self) -> bool:
        return bool(self.enabled and self.is_installed())

    def command(self, *args: str) -> list[str]:
        if not self.command_path:
            return []
        if self.command_path.lower().endswith(".ps1"):
            return [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                self.command_path,
                *args,
            ]
        return [self.command_path, *args]

    def version(self, timeout_seconds: int = 10) -> str:
        if not self.is_installed():
            return ""
        try:
            completed = self._run(self.command("--version"), timeout_seconds)
        except subprocess.TimeoutExpired:
            return "timeout"
        except OSError:
            return ""
        output = (completed.stdout or completed.stderr or "").strip()
        return output.splitlines()[0] if output else ""

    def health(self) -> dict[str, Any]:
        version = self.version(timeout_seconds=5) if self.is_installed() else ""
        if not self.enabled:
            status = "disabled"
        elif self.is_installed() and version != "timeout":
            status = "available"
        elif version == "timeout":
            status = "timeout"
        else:
            status = "missing"
        return {
            "provider_id": self.provider_id,
            "name": self.name,
            "enabled": self.enabled,
            "available": self.is_available(),
            "installed": self.is_installed(),
            "status": status,
            "command_path": self.command_path,
            "version": version,
            "last_call_at": self.last_result.created_at if self.last_result else "",
            "last_duration_ms": self.last_result.duration_ms if self.last_result else 0,
            "last_tokens": (
                self.last_result.input_tokens + self.last_result.output_tokens
                if self.last_result else 0
            ),
            "estimated_cost_yen": 0,
            "external": self.external,
        }

    def complete(self, prompt: str, **kwargs: Any) -> ProviderResult:
        if not self.is_available():
            return ProviderResult(
                ok=False,
                content="",
                provider=self.provider_id,
                model=self.model,
                input_tokens=estimate_tokens(prompt),
                error="Gemini CLI is disabled or not installed.",
            )
        result = self.execute_prompt(
            prompt,
            timeout_seconds=int(kwargs.get("timeout_seconds", self.timeout_seconds)),
            retries=int(kwargs.get("retries", self.retries)),
        )
        self.last_call_at = result.created_at
        total_tokens = result.input_tokens + result.output_tokens
        self.estimated_token_usage += total_tokens
        return ProviderResult(
            ok=result.ok,
            content=result.response,
            provider=self.provider_id,
            model=self.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            external_request=False,
            error=result.error,
            metadata={
                "duration_ms": result.duration_ms,
                "attempts": result.attempts,
                "estimated_cost_yen": 0,
                "command": result.command,
            },
        )

    def execute_prompt(
        self,
        prompt: str,
        *,
        timeout_seconds: int | None = None,
        retries: int | None = None,
    ) -> GeminiCLIResult:
        timeout = max(int(timeout_seconds or self.timeout_seconds), 1)
        attempts = max(int(retries or self.retries), 1)
        input_tokens = estimate_tokens(prompt)
        if not self.is_installed():
            result = GeminiCLIResult(
                ok=False,
                prompt=prompt,
                error="Gemini CLI is not installed or not on PATH.",
                input_tokens=input_tokens,
                attempts=0,
            )
            self._record(result)
            return result

        command = self.command("-p", prompt)
        last_error = ""
        timed_out = False
        started = time.monotonic()
        response = ""
        used_attempts = 0
        for attempt in range(1, attempts + 1):
            used_attempts = attempt
            try:
                completed = self._run(command, timeout)
                response = (completed.stdout or "").strip()
                last_error = (completed.stderr or "").strip()
                if completed.returncode == 0 and response:
                    result = GeminiCLIResult(
                        ok=True,
                        prompt=prompt,
                        response=response,
                        command=command,
                        duration_ms=int((time.monotonic() - started) * 1000),
                        input_tokens=input_tokens,
                        output_tokens=estimate_tokens(response),
                        attempts=used_attempts,
                    )
                    self._record(result)
                    return result
                if not last_error:
                    last_error = f"Gemini CLI exited with code {completed.returncode}."
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                last_error = f"Gemini CLI timed out after {timeout}s."
                response = (exc.stdout or "").strip() if isinstance(exc.stdout, str) else ""
            except OSError as exc:
                last_error = str(exc)

        result = GeminiCLIResult(
            ok=False,
            prompt=prompt,
            response=response,
            error=last_error,
            command=command,
            duration_ms=int((time.monotonic() - started) * 1000),
            input_tokens=input_tokens,
            output_tokens=estimate_tokens(response),
            attempts=used_attempts,
            timed_out=timed_out,
        )
        self._record(result)
        return result

    def _run(self, command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
        if self.runner is not None:
            return self.runner(
                command,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                encoding="utf-8",
                errors="replace",
            )

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            _kill_process_tree(process.pid)
            try:
                stdout, stderr = process.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                stdout, stderr = "", ""
            exc.stdout = stdout
            exc.stderr = stderr
            raise exc
        return subprocess.CompletedProcess(command, process.returncode, stdout=stdout, stderr=stderr)

    def stream_response(self, prompt: str, **kwargs: Any) -> Iterator[str]:
        result = self.execute_prompt(prompt, **kwargs)
        text = result.response if result.ok else result.error
        for line in text.splitlines():
            yield line

    def _record(self, result: GeminiCLIResult) -> None:
        self.last_result = result
        self.log_dir.mkdir(parents=True, exist_ok=True)
        path = self.log_dir / f"gemini_cli_{datetime.now().strftime('%Y%m%d')}.jsonl"
        payload = {
            "created_at": result.created_at,
            "ok": result.ok,
            "duration_ms": result.duration_ms,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "estimated_cost_yen": 0,
            "attempts": result.attempts,
            "timed_out": result.timed_out,
            "error": result.error,
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text or "") / 4))


def _kill_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return
    try:
        os.kill(pid, 9)
    except OSError:
        pass
