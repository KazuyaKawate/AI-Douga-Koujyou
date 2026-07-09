from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.api_connectors.connectors import CONNECTORS
from src.api_connectors.credential_vault import CredentialVault
from src.self_builder.knowledge_manager import load_knowledge, save_knowledge
from src.utils.config import DOTENV_PATH, PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


API_CONNECTORS_PATH = PROJECT_ROOT / "config" / "api_connectors.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_state() -> dict[str, Any]:
    return {
        "enabled": True,
        "dry_run_default": True,
        "review_required": True,
        "connectors": {
            name: {
                "enabled": False,
                "dry_run_default": True,
                "credentials": {},
                "oauth": {},
                "api_remaining": 0,
                "history": [],
                "retries": [],
                "analytics": [],
                "last_post": {},
            }
            for name in CONNECTORS
        },
        "callbacks": [],
        "updated_at": _now(),
    }


class APIConnectorManager:
    def __init__(self, path: str | Path = API_CONNECTORS_PATH, vault: CredentialVault | None = None) -> None:
        self.path = Path(path)
        self.vault = vault or CredentialVault()

    def load_state(self, *, include_plain: bool = False) -> dict[str, Any]:
        data = load_json(self.path, default=None)
        if not isinstance(data, dict):
            data = _default_state()
            self.save_state(data)
        defaults = _default_state()
        for key, value in defaults.items():
            data.setdefault(key, value)
        data.setdefault("connectors", {})
        for name, default in defaults["connectors"].items():
            data["connectors"].setdefault(name, default)
            for key, value in default.items():
                data["connectors"][name].setdefault(key, value)
            if include_plain:
                encrypted = data["connectors"][name].get("credentials", {})
                data["connectors"][name]["plain_credentials"] = {
                    key: self.vault.decrypt(value) for key, value in encrypted.items()
                }
        return data

    def save_state(self, state: dict[str, Any]) -> None:
        state["updated_at"] = _now()
        for connector in state.get("connectors", {}).values():
            connector.pop("plain_credentials", None)
        save_json_atomic(self.path, state)

    def configure_oauth(self, connector: str, credentials: dict[str, str], *, enabled: bool = True) -> dict[str, Any]:
        state = self.load_state()
        if connector not in CONNECTORS:
            raise ValueError(f"Unsupported connector: {connector}")
        item = state["connectors"][connector]
        item["enabled"] = bool(enabled)
        item.setdefault("credentials", {})
        for key, value in credentials.items():
            if value:
                item["credentials"][key] = self.vault.encrypt(value)
        item["oauth"] = {
            "configured": bool(item["credentials"]),
            "configured_at": _now(),
            "masked": {key: self.vault.masked(value) for key, value in item["credentials"].items()},
        }
        self.save_state(state)
        return self.connector_status(connector)

    def connector_status(self, connector: str) -> dict[str, Any]:
        state = self.load_state()
        item = state["connectors"].get(connector, {})
        connector_cls = CONNECTORS[connector]
        return {
            **connector_cls(item).status(),
            "enabled": bool(item.get("enabled", False)),
        }

    def all_status(self) -> list[dict[str, Any]]:
        return [self.connector_status(name) for name in CONNECTORS]

    def publish(
        self,
        connector: str,
        payload: dict[str, Any],
        *,
        dry_run: bool | None = None,
        approved: bool = False,
    ) -> dict[str, Any]:
        state = self.load_state(include_plain=True)
        if connector not in CONNECTORS:
            return {"status": "unsupported", "connector": connector}
        item = state["connectors"][connector]
        dry = bool(item.get("dry_run_default", True) if dry_run is None else dry_run)
        payload = dict(payload)
        payload.setdefault("review", {"status": "approved" if approved else "pending"})
        if state.get("review_required", True) and payload.get("review", {}).get("status") != "approved":
            result = CONNECTORS[connector](item).publish(payload, dry_run=True)
            self._record(state, connector, result)
            self.save_state(state)
            return result
        result = CONNECTORS[connector](item).publish(payload, dry_run=dry)
        if result.get("status") == "failed":
            self._retry(state, connector, payload, result)
        analytics = CONNECTORS[connector](item).analytics(result.get("external_id", ""))
        result["analytics"] = analytics
        self._record(state, connector, result)
        callback = self._callback(state, connector, result)
        result["callback"] = callback
        self._knowledge(connector, result)
        self.save_state(state)
        return result

    def threads_oauth_url(self, *, client_id: str, redirect_uri: str, state: str = "") -> str:
        connector_cls = CONNECTORS["threads"]
        return connector_cls.authorization_url(client_id=client_id, redirect_uri=redirect_uri, state=state)

    def complete_threads_oauth(
        self,
        *,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        save_env: bool = True,
    ) -> dict[str, Any]:
        connector = CONNECTORS["threads"]({})
        token_result = connector.exchange_code_for_access_token(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
        if not token_result.get("ok"):
            return {"ok": False, "stage": "access_token", "token_result": token_result}
        token = str(token_result.get("body", {}).get("access_token", ""))
        if not token:
            return {"ok": False, "stage": "access_token", "token_result": token_result, "message": "access_token was not returned."}
        profile_connector = CONNECTORS["threads"]({"plain_credentials": {"access_token": token}})
        profile = profile_connector.test_connection()
        user_id = str(profile.get("threads_user_id", ""))
        if not profile.get("ok") or not user_id:
            return {"ok": False, "stage": "profile", "token_result": token_result, "profile": profile}
        credentials = {"access_token": token, "user_id": user_id, "api_base": os.getenv("THREADS_API_BASE", "https://graph.threads.net/v1.0")}
        self.configure_oauth("threads", credentials, enabled=True)
        if save_env:
            self.save_threads_env(access_token=token, user_id=user_id, api_base=credentials["api_base"])
        return {"ok": True, "stage": "complete", "profile": profile, "threads_user_id": user_id, "username": profile.get("username", "")}

    def save_threads_env(self, *, access_token: str, user_id: str, api_base: str = "https://graph.threads.net/v1.0") -> None:
        self._save_env_values(
            {
                "THREADS_ACCESS_TOKEN": access_token,
                "THREADS_USER_ID": user_id,
                "THREADS_API_BASE": api_base,
            }
        )
        os.environ["THREADS_ACCESS_TOKEN"] = access_token
        os.environ["THREADS_USER_ID"] = user_id
        os.environ["THREADS_API_BASE"] = api_base

    def test_connection(self, connector: str = "threads") -> dict[str, Any]:
        state = self.load_state(include_plain=True)
        if connector not in CONNECTORS:
            return {"ok": False, "status": "unsupported", "connector": connector}
        instance = CONNECTORS[connector](state["connectors"][connector])
        if hasattr(instance, "test_connection"):
            return instance.test_connection()
        return {"ok": instance.status().get("configured", False), "status": instance.status()}

    def create_post(self, connector: str, text: str, *, dry_run: bool = True) -> dict[str, Any]:
        state = self.load_state(include_plain=True)
        if connector not in CONNECTORS:
            return {"ok": False, "status": "unsupported", "connector": connector}
        instance = CONNECTORS[connector](state["connectors"][connector])
        if not hasattr(instance, "create_post"):
            return {"ok": False, "status": "unsupported_action", "connector": connector}
        return instance.create_post(text, dry_run=dry_run)

    def publish_post(self, connector: str, creation_id: str, *, dry_run: bool = True) -> dict[str, Any]:
        state = self.load_state(include_plain=True)
        if connector not in CONNECTORS:
            return {"ok": False, "status": "unsupported", "connector": connector}
        instance = CONNECTORS[connector](state["connectors"][connector])
        if not hasattr(instance, "publish_post"):
            return {"ok": False, "status": "unsupported_action", "connector": connector}
        return instance.publish_post(creation_id, dry_run=dry_run)

    def _save_env_values(self, values: dict[str, str]) -> None:
        DOTENV_PATH.parent.mkdir(parents=True, exist_ok=True)
        lines = DOTENV_PATH.read_text(encoding="utf-8").splitlines() if DOTENV_PATH.exists() else []
        seen: set[str] = set()
        updated: list[str] = []
        for line in lines:
            stripped = line.strip()
            key = stripped.split("=", 1)[0].strip() if "=" in stripped and not stripped.startswith("#") else ""
            if key in values:
                updated.append(f"{key}={values[key]}")
                seen.add(key)
            else:
                updated.append(line)
        for key, value in values.items():
            if key not in seen:
                updated.append(f"{key}={value}")
        DOTENV_PATH.write_text("\n".join(updated).rstrip() + "\n", encoding="utf-8")
    def analytics_prepare(self, connector: str, external_id: str) -> dict[str, Any]:
        state = self.load_state(include_plain=True)
        if connector not in CONNECTORS:
            return {"status": "unsupported", "connector": connector}
        analytics = CONNECTORS[connector](state["connectors"][connector]).analytics(external_id)
        state["connectors"][connector].setdefault("analytics", []).insert(0, analytics)
        state["connectors"][connector]["analytics"] = state["connectors"][connector]["analytics"][:100]
        self.save_state(state)
        return analytics

    def dashboard_summary(self) -> dict[str, Any]:
        state = self.load_state()
        statuses = self.all_status()
        history = []
        for item in state.get("connectors", {}).values():
            history.extend(item.get("history", []))
        success = [row for row in history if row.get("status") in {"published", "dry_run"}]
        return {
            "connectors": statuses,
            "connected": sum(1 for row in statuses if row.get("configured")),
            "auth_ready": sum(1 for row in statuses if row.get("auth_status") == "configured"),
            "api_remaining": sum(int(row.get("api_remaining", 0) or 0) for row in statuses),
            "last_post": sorted(history, key=lambda row: row.get("created_at", ""), reverse=True)[:1],
            "success_rate": round(len(success) / max(len(history), 1) * 100, 1),
            "history_count": len(history),
        }

    def _record(self, state: dict[str, Any], connector: str, result: dict[str, Any]) -> None:
        item = state["connectors"][connector]
        item.setdefault("history", []).insert(0, result)
        item["history"] = item["history"][:300]
        item["last_post"] = result
        if result.get("analytics"):
            item.setdefault("analytics", []).insert(0, result["analytics"])
            item["analytics"] = item["analytics"][:100]

    def _retry(self, state: dict[str, Any], connector: str, payload: dict[str, Any], result: dict[str, Any]) -> None:
        retry = {
            "retry_id": f"apir-{uuid4().hex[:10]}",
            "connector": connector,
            "payload_title": payload.get("title", payload.get("content", {}).get("title", "")),
            "status": "retry_queued",
            "retry_count": 1,
            "last_error": result.get("message", ""),
            "created_at": _now(),
        }
        state["connectors"][connector].setdefault("retries", []).insert(0, retry)
        state["connectors"][connector]["retries"] = state["connectors"][connector]["retries"][:100]

    def _callback(self, state: dict[str, Any], connector: str, result: dict[str, Any]) -> dict[str, Any]:
        callback = {
            "callback_id": f"apicb-{uuid4().hex[:10]}",
            "source": "api_connector",
            "connector": connector,
            "status": result.get("status", ""),
            "external_id": result.get("external_id", ""),
            "analytics": result.get("analytics", {}),
            "created_at": _now(),
        }
        state.setdefault("callbacks", []).insert(0, callback)
        state["callbacks"] = state["callbacks"][:300]
        save_json_atomic(PROJECT_ROOT / "config" / "api_connector_callback.json", callback)
        return callback

    @staticmethod
    def _knowledge(connector: str, result: dict[str, Any]) -> None:
        knowledge = load_knowledge()
        record = {
            "id": f"apik-{uuid4().hex[:10]}",
            "type": "api_connector",
            "connector": connector,
            "status": result.get("status", ""),
            "analytics": result.get("analytics", {}),
            "created_at": _now(),
        }
        bucket = "success_examples" if result.get("status") in {"published", "dry_run"} else "failure_examples"
        knowledge.setdefault(bucket, []).insert(0, record)
        knowledge.setdefault("timeline", []).insert(0, record)
        knowledge.setdefault("categories", {}).setdefault("api_connector", 0)
        knowledge["categories"]["api_connector"] += 1
        save_knowledge(knowledge)

