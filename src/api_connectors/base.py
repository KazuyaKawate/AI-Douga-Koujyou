from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from urllib import error, request
from uuid import uuid4


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class BaseAPIConnector:
    connector_id = "base"
    required_credentials: tuple[str, ...] = ()

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state

    def status(self) -> dict[str, Any]:
        credentials = self.state.get("credentials", {})
        configured = all(credentials.get(name) for name in self.required_credentials)
        return {
            "connector": self.connector_id,
            "configured": configured,
            "auth_status": "configured" if configured else "missing",
            "dry_run_default": self.state.get("dry_run_default", True),
            "api_remaining": self.state.get("api_remaining", 0),
            "last_post": self.state.get("last_post", {}),
            "success_rate": self.success_rate(),
        }

    def publish(self, payload: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        review = payload.get("review", {})
        if review.get("status") != "approved":
            return self._result("review_required", payload, dry_run, message="Posting requires approved review.")
        if dry_run:
            return self._result("dry_run", payload, True, external_id=f"dry-{uuid4().hex[:10]}")
        if not self.status()["configured"]:
            return self._result("auth_missing", payload, True, message="Connector credentials are missing.")
        return self._live_publish(payload)

    def analytics(self, external_id: str) -> dict[str, Any]:
        return {
            "status": "prepared",
            "connector": self.connector_id,
            "external_id": external_id,
            "pv": 0,
            "clicks": 0,
            "ctr": 0,
            "cvr": 0,
            "revenue": 0,
            "prepared_at": now(),
        }

    def success_rate(self) -> float:
        history = self.state.get("history", [])
        if not history:
            return 0.0
        ok = sum(1 for item in history if item.get("status") in {"published", "dry_run"})
        return round(ok / len(history) * 100, 1)

    def _live_publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._result("not_implemented", payload, True, message="Live publish is not implemented for this connector.")

    def _post_json(self, url: str, body: dict[str, Any], headers: dict[str, str] | None = None, timeout: int = 30) -> dict[str, Any]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with request.urlopen(req, timeout=timeout) as response:
                text = response.read().decode("utf-8")
            return {"ok": True, "status_code": getattr(response, "status", 200), "body": json.loads(text or "{}")}
        except (error.URLError, json.JSONDecodeError) as exc:
            return {"ok": False, "error": str(exc)}

    def _result(
        self,
        status: str,
        payload: dict[str, Any],
        dry_run: bool,
        *,
        external_id: str = "",
        message: str = "",
        raw: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "connector": self.connector_id,
            "status": status,
            "dry_run": dry_run,
            "external_id": external_id,
            "title": payload.get("title", payload.get("content", {}).get("title", "")),
            "message": message,
            "raw": raw or {},
            "created_at": now(),
        }
