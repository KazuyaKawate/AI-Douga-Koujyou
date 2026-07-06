from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime
from typing import Any

from src.providers.base_provider import BaseProvider, ProviderResult, estimate_tokens


class AnthropicProvider(BaseProvider):
    provider_id = "anthropic"
    name = "Claude"
    env_key = "ANTHROPIC_API_KEY"
    model = "claude-sonnet-4"

    def complete(self, prompt: str, **kwargs: Any) -> ProviderResult:
        if not self.is_available():
            return super().complete(prompt, **kwargs)
        if self.test_mode:
            return self._test_response(prompt)

        model = kwargs.get("model") or self.model
        payload = {
            "model": model,
            "max_tokens": int(kwargs.get("max_tokens", 2048)),
            "messages": [{"role": "user", "content": prompt}],
        }
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": os.getenv(self.env_key, ""),
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=int(kwargs.get("timeout_seconds", 60))) as response:
                data = json.loads(response.read().decode("utf-8"))
            blocks = data.get("content", [])
            content = "\n".join(block.get("text", "") for block in blocks if isinstance(block, dict)).strip()
            usage = data.get("usage", {})
            self.last_call_at = datetime.now().isoformat(timespec="seconds")
            input_tokens = int(usage.get("input_tokens") or estimate_tokens(prompt))
            output_tokens = int(usage.get("output_tokens") or estimate_tokens(content))
            self.estimated_token_usage += input_tokens + output_tokens
            return ProviderResult(
                ok=bool(content),
                content=content,
                provider=self.provider_id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                external_request=True,
                metadata={"api": "anthropic_messages"},
            )
        except Exception as exc:
            return ProviderResult(
                ok=False,
                content="",
                provider=self.provider_id,
                model=model,
                input_tokens=estimate_tokens(prompt),
                error=str(exc),
                external_request=True,
            )
