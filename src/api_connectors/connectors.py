from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, parse, request
from uuid import uuid4

from src.api_connectors.base import BaseAPIConnector


THREADS_API_BASE = "https://graph.threads.net/v1.0"
THREADS_OAUTH_BASE = "https://threads.net/oauth/authorize"
THREADS_TOKEN_URL = "https://graph.threads.net/oauth/access_token"
THREADS_SCOPES = ("threads_basic", "threads_content_publish")


class NoteConnector(BaseAPIConnector):
    connector_id = "note"
    required_credentials = ("access_token",)

    def _live_publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._result("manual_required", payload, True, message="note live posting requires a confirmed API/webhook route.")


class ThreadsConnector(BaseAPIConnector):
    """Meta official Threads API connector. No browser automation."""

    connector_id = "threads"
    required_credentials = ("access_token", "user_id")

    def status(self) -> dict[str, Any]:
        status = super().status()
        env_configured = bool(self._access_token().strip() and self._user_id().strip())
        status["configured"] = status["configured"] or env_configured
        status["auth_status"] = "configured" if status["configured"] else "missing"
        status["api_base"] = self._api_base()
        return status

    @staticmethod
    def authorization_url(
        *,
        client_id: str,
        redirect_uri: str,
        state: str = "",
        scopes: tuple[str, ...] = THREADS_SCOPES,
    ) -> str:
        query = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": ",".join(scopes),
            "response_type": "code",
        }
        if state:
            query["state"] = state
        return THREADS_OAUTH_BASE + "?" + parse.urlencode(query)

    def exchange_code_for_access_token(
        self,
        *,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> dict[str, Any]:
        return self._post_form(
            THREADS_TOKEN_URL,
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )

    def test_connection(self) -> dict[str, Any]:
        profile = self.profile()
        body = profile.get("body", {})
        return {
            "ok": bool(profile.get("ok") and isinstance(body, dict) and body.get("id")),
            "status_code": profile.get("status_code"),
            "body": body,
            "threads_user_id": body.get("id", "") if isinstance(body, dict) else "",
            "username": body.get("username", "") if isinstance(body, dict) else "",
        }

    def profile(self) -> dict[str, Any]:
        token = self._access_token()
        if not token.strip():
            return {"ok": False, "status_code": None, "body": {"error": "THREADS_ACCESS_TOKEN is missing"}}
        url = f"{self._api_base().rstrip('/')}/me?" + parse.urlencode({"fields": "id,username", "access_token": token})
        return self._get_json(url)

    def create_post(self, text: str, *, dry_run: bool = True) -> dict[str, Any]:
        text = str(text or "")[:500]
        if dry_run:
            return {"ok": True, "status": "dry_run", "dry_run": True, "body": {"id": f"dry-create-{uuid4().hex[:10]}", "text": text}}
        token = self._access_token()
        user_id = self._user_id()
        if not token.strip() or not user_id.strip():
            return {"ok": False, "status": "auth_missing", "dry_run": False, "body": {"error": "THREADS_ACCESS_TOKEN or THREADS_USER_ID is missing"}}
        created = self._post_form(f"{self._api_base().rstrip('/')}/{user_id}/threads", {"media_type": "TEXT", "text": text, "access_token": token})
        created["dry_run"] = False
        created.setdefault("status", "created" if created.get("ok") else "failed")
        return created

    def publish_post(self, creation_id: str, *, dry_run: bool = True) -> dict[str, Any]:
        if dry_run:
            return {"ok": True, "status": "dry_run", "dry_run": True, "body": {"id": f"dry-publish-{uuid4().hex[:10]}", "creation_id": creation_id}}
        token = self._access_token()
        user_id = self._user_id()
        if not token.strip() or not user_id.strip():
            return {"ok": False, "status": "auth_missing", "dry_run": False, "body": {"error": "THREADS_ACCESS_TOKEN or THREADS_USER_ID is missing"}}
        published = self._post_form(f"{self._api_base().rstrip('/')}/{user_id}/threads_publish", {"creation_id": creation_id, "access_token": token})
        published["dry_run"] = False
        published.setdefault("status", "published" if published.get("ok") else "failed")
        return published

    def _live_publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text") or payload.get("content", {}).get("text") or payload.get("title", ""))[:500]
        create = self.create_post(text, dry_run=False)
        if not create.get("ok"):
            return self._result("failed", payload, False, message=self._error_message(create), raw={"create": create})
        creation_id = str(create.get("body", {}).get("id", ""))
        published = self.publish_post(creation_id, dry_run=False)
        status = "published" if published.get("ok") else "failed"
        external_id = str(published.get("body", {}).get("id") or creation_id)
        return self._result(status, payload, False, external_id=external_id, message=self._error_message(published), raw={"create": create, "publish": published})

    def _access_token(self) -> str:
        credentials = self.state.get("plain_credentials", {})
        return str(credentials.get("access_token") or os.getenv("THREADS_ACCESS_TOKEN", ""))

    def _user_id(self) -> str:
        credentials = self.state.get("plain_credentials", {})
        return str(credentials.get("user_id") or os.getenv("THREADS_USER_ID", ""))

    def _api_base(self) -> str:
        credentials = self.state.get("plain_credentials", {})
        return str(credentials.get("api_base") or os.getenv("THREADS_API_BASE", THREADS_API_BASE))

    @staticmethod
    def _error_message(result: dict[str, Any]) -> str:
        body = result.get("body", {})
        if isinstance(body, dict):
            err = body.get("error", "")
            if isinstance(err, dict):
                return str(err.get("message") or err.get("error") or "")
            return str(err or "")
        return str(result.get("error", ""))

    def _get_json(self, url: str) -> dict[str, Any]:
        req = request.Request(url, method="GET")
        try:
            with request.urlopen(req, timeout=30) as response:
                text = response.read().decode("utf-8")
                status_code = getattr(response, "status", 200)
            return {"ok": True, "status_code": status_code, "body": json.loads(text or "{}")}
        except error.HTTPError as exc:
            return self._http_error_result(exc)
        except (error.URLError, json.JSONDecodeError) as exc:
            return {"ok": False, "status_code": None, "body": {"error": str(exc)}}

    def _post_form(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        encoded = parse.urlencode(body).encode("utf-8")
        req = request.Request(url, data=encoded, method="POST")
        try:
            with request.urlopen(req, timeout=30) as response:
                text = response.read().decode("utf-8")
                status_code = getattr(response, "status", 200)
            return {"ok": True, "status_code": status_code, "body": json.loads(text or "{}")}
        except error.HTTPError as exc:
            return self._http_error_result(exc)
        except (error.URLError, json.JSONDecodeError) as exc:
            return {"ok": False, "status_code": None, "body": {"error": str(exc)}}

    @staticmethod
    def _http_error_result(exc: error.HTTPError) -> dict[str, Any]:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            parsed: Any = json.loads(body or "{}")
        except json.JSONDecodeError:
            parsed = {"error": body or str(exc)}
        return {"ok": False, "status_code": exc.code, "body": parsed}


class WordPressConnector(BaseAPIConnector):
    connector_id = "wordpress"
    required_credentials = ("api_url", "username", "app_password")

    def _live_publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        credentials = self.state.get("plain_credentials", {})
        url = str(credentials.get("api_url", "")).rstrip("/") + "/wp-json/wp/v2/posts"
        content = payload.get("content", {})
        body = {
            "title": payload.get("title") or content.get("title", ""),
            "content": payload.get("body") or content.get("body", ""),
            "status": "draft",
        }
        raw = self._post_json(url, body)
        status = "published" if raw.get("ok") else "failed"
        external_id = str(raw.get("body", {}).get("id", "")) if raw.get("ok") else ""
        return self._result(status, payload, False, external_id=external_id, raw=raw)


class WebhookConnector(BaseAPIConnector):
    connector_id = "webhook"
    required_credentials = ("url",)

    def _live_publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        credentials = self.state.get("plain_credentials", {})
        raw = self._post_json(str(credentials.get("url", "")), payload, headers={"X-AIOS-Connector": "webhook"})
        status = "published" if raw.get("ok") else "failed"
        return self._result(status, payload, False, external_id=f"wh-{uuid4().hex[:10]}", raw=raw)


CONNECTORS = {
    "note": NoteConnector,
    "threads": ThreadsConnector,
    "wordpress": WordPressConnector,
    "webhook": WebhookConnector,
}

