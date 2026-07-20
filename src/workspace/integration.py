"""Phase 10 Google Workspace integration with a mandatory local review gate."""
from __future__ import annotations

import base64
import json
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic
from src.workspace.google_workspace import GoogleWorkspaceManager


WRITE_BLOCKED = "Production禁止: 外部書込はReview Queueで停止します"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class WorkspaceActionStore:
    """Local-only review queue. It never shares the Commander Queue file."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or PROJECT_ROOT / "data" / "google_workspace_actions.json")

    def load(self) -> dict[str, Any]:
        data = load_json(self.path, default={"actions": []})
        return data if isinstance(data, dict) and isinstance(data.get("actions"), list) else {"actions": []}

    def stage(self, service: str, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        data = self.load()
        action = {
            "action_id": f"gwa-{uuid4().hex[:12]}", "service": service, "operation": operation,
            "payload": payload, "status": "review_required", "created_at": _now(),
            "dry_run": True, "review_required": True, "production_actions_enabled": False,
            "approval_required": True, "execute_allowed": False,
        }
        data["actions"].append(action)
        save_json_atomic(self.path, data)
        return action

    def review(self, action_id: str, *, approved: bool, reviewer: str) -> dict[str, Any] | None:
        data = self.load()
        for action in data["actions"]:
            if action.get("action_id") == action_id and action.get("status") == "review_required":
                action.update(status="send_waiting" if approved else "rejected", reviewed_by=reviewer, reviewed_at=_now())
                save_json_atomic(self.path, data)
                return action
        return None


class GoogleWorkspaceIntegration:
    """Read APIs plus local-only write previews for all Workspace services."""

    def __init__(self, *, root: str | Path = PROJECT_ROOT, manager: GoogleWorkspaceManager | None = None,
                 service_builder: Callable[..., Any] | None = None, action_store: WorkspaceActionStore | None = None) -> None:
        self.root = Path(root)
        self.manager = manager or GoogleWorkspaceManager(root=self.root)
        self._builder = service_builder
        self.actions = action_store or WorkspaceActionStore(self.root / "data" / "google_workspace_actions.json")

    def status(self) -> dict[str, Any]:
        base = self.manager.configuration_status()
        base["action_counts"] = self._counts()
        return base

    def refresh_oauth(self) -> dict[str, Any]:
        """Refresh an expired OAuth token and atomically persist it outside the repo."""
        config = self.manager.load_config()
        credentials = self.manager._build_credentials(config)
        if not getattr(credentials, "expired", False):
            return self._safe("token_valid", refreshed=False)
        if not getattr(credentials, "refresh_token", None):
            return self._safe("reconnect_required", refreshed=False)
        from google.auth.transport.requests import Request
        credentials.refresh(Request())
        token_path = self.manager._credential_path(config)
        if token_path is None:
            raise ValueError("OAuth token path is not configured")
        save_json_atomic(token_path, json.loads(credentials.to_json()))
        return self._safe("refreshed", refreshed=True)

    def disconnect(self, *, confirmed: bool = False) -> dict[str, Any]:
        if not confirmed:
            return self._safe("confirmation_required", disconnected=False)
        token = self.manager._credential_path(self.manager.load_config())
        if token and token.exists():
            token.unlink()
        return self._safe("disconnected", disconnected=True)

    def drive_list(self, *, folder_id: str = "root", page_size: int = 100) -> dict[str, Any]:
        service = self._service("drive", "v3")
        response = self.manager._execute(service.files().list(q=f"'{folder_id}' in parents and trashed=false", pageSize=min(page_size, 100),
                                        fields="files(id,name,mimeType,modifiedTime,size)"))
        return self._read("drive", response.get("files", []))

    def drive_download(self, file_id: str) -> dict[str, Any]:
        content = self.manager._execute(self._service("drive", "v3").files().get_media(fileId=file_id))
        encoded = base64.b64encode(content if isinstance(content, bytes) else bytes(content)).decode("ascii")
        return self._read("drive", {"file_id": file_id, "content_base64": encoded})

    def drive_create_folder(self, name: str, *, parent_id: str = "root") -> dict[str, Any]:
        return self._stage("drive", "create_folder", {"name": name, "parent_id": parent_id})

    def drive_upload(self, local_path: str, *, parent_id: str = "root") -> dict[str, Any]:
        path = (self.root / local_path).resolve()
        if not path.is_relative_to(self.root.resolve()) or not path.is_file():
            raise ValueError("アップロード元はAIOS内の既存ファイルに限定されます")
        return self._stage("drive", "upload", {"local_path": str(path.relative_to(self.root)), "parent_id": parent_id, "size": path.stat().st_size})

    def sheets_read(self, spreadsheet_id: str, range_name: str) -> dict[str, Any]:
        values = self.manager._execute(self._service("sheets", "v4").spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=range_name)).get("values", [])
        return self._read("sheets", values)

    def sheets_write(self, spreadsheet_id: str, range_name: str, values: list[list[Any]]) -> dict[str, Any]:
        return self._stage("sheets", "write", {"spreadsheet_id": spreadsheet_id, "range": range_name, "values": values})

    def stage_revenue_rows(self, rows: list[dict[str, Any]], *, spreadsheet_id: str, range_name: str = "Revenue!A1") -> dict[str, Any]:
        headers = sorted({key for row in rows for key in row})
        values = [headers] + [[row.get(key, "") for key in headers] for row in rows]
        return self._stage("sheets", "write", {"spreadsheet_id": spreadsheet_id, "range": range_name, "values": values, "source_engine": "revenue"})

    def docs_read(self, document_id: str) -> dict[str, Any]:
        return self._read("docs", self.manager._execute(self._service("docs", "v1").documents().get(documentId=document_id)))

    def docs_save(self, title: str, content: str, *, folder_id: str = "root") -> dict[str, Any]:
        return self._stage("docs", "save_article", {"title": title, "content": content, "folder_id": folder_id})

    def gmail_create_draft(self, *, to: str, subject: str, body: str) -> dict[str, Any]:
        message = EmailMessage(); message["To"] = to; message["Subject"] = subject; message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        return self._stage("gmail", "create_draft", {"to": to, "subject": subject, "raw": raw})

    def gmail_send(self, action_id: str) -> dict[str, Any]:
        return {"ok": False, "status": "production_blocked", "action_id": action_id, "message": WRITE_BLOCKED,
                "dry_run": True, "review_required": True, "approval_required": True,
                "execute_allowed": False, "production_actions_enabled": False}

    def calendar_list(self, *, calendar_id: str = "primary", time_min: str | None = None) -> dict[str, Any]:
        kwargs = {"calendarId": calendar_id, "singleEvents": True, "orderBy": "startTime", "maxResults": 100}
        if time_min: kwargs["timeMin"] = time_min
        events = self.manager._execute(self._service("calendar", "v3").events().list(**kwargs)).get("items", [])
        return self._read("calendar", events)

    def calendar_create(self, event: dict[str, Any], *, calendar_id: str = "primary") -> dict[str, Any]:
        return self._stage("calendar", "create_event", {"calendar_id": calendar_id, "event": event})

    def commander_save_article(self, *, title: str, content: str, folder_id: str = "root") -> dict[str, Any]:
        action = self.docs_save(title, content, folder_id=folder_id)
        action["route"] = ["commander", "review", "workspace"]
        return action

    def review(self, action_id: str, *, approved: bool, reviewer: str = "human") -> dict[str, Any]:
        action = self.actions.review(action_id, approved=approved, reviewer=reviewer)
        return {"ok": bool(action), "action": action, "production_actions_enabled": False}

    def _service(self, name: str, version: str) -> Any:
        config = self.manager.load_config()
        credentials = self.manager._build_credentials(config)
        build = self._builder
        if build is None:
            from googleapiclient.discovery import build
        return build(name, version, credentials=credentials, cache_discovery=False)

    def _stage(self, service: str, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.actions.stage(service, operation, payload)

    def _counts(self) -> dict[str, int]:
        rows = self.actions.load()["actions"]
        return {status: sum(row.get("status") == status for row in rows) for status in ("review_required", "send_waiting", "rejected")}

    @staticmethod
    def _read(service: str, data: Any) -> dict[str, Any]:
        return {"ok": True, "service": service, "data": data, "read_only": True, "write_performed": False}

    @staticmethod
    def _safe(status: str, **extra: Any) -> dict[str, Any]:
        return {"ok": status in {"token_valid", "refreshed", "disconnected"}, "status": status, "dry_run": True,
                "review_required": True, "approval_required": True, "execute_allowed": False,
                "production_actions_enabled": False, **extra}


class GoogleService(GoogleWorkspaceIntegration):
    """Unified AIOS gateway for Drive, Sheets and Gmail with mandatory safety gates."""

    CONNECTED_SERVICES = ("drive", "sheets", "gmail")

    def health_check(self, *, connect: bool = False, dry_run: bool = True) -> dict[str, Any]:
        if dry_run is not True:
            raise ValueError("GoogleService health check requires dry_run=True")
        if connect:
            return self.manager.check_connections(dry_run=True)
        return self.status()

    def phase102_health_check(self, *, spreadsheet_id: str = "", dry_run: bool = True) -> dict[str, Any]:
        """Run read checks and prove that every write check stops locally."""
        if dry_run is not True:
            raise ValueError("Phase 102 health check requires dry_run=True")
        connected = self.manager.check_connections(dry_run=True)
        write_checks = {
            "drive_write": self.drive_create_folder("AIOS Phase102 HealthCheck"),
            "sheets_write": self.sheets_write(spreadsheet_id or "configuration-required", "HealthCheck!A1", [["dry_run"]]),
            "gmail_draft": self.gmail_create_draft(to="local-review@example.invalid", subject="AIOS Phase102 DryRun", body="No external draft was created."),
        }
        return {
            "ok": connected.get("ok", False) and all(row["status"] == "review_required" for row in write_checks.values()),
            "read_checks": connected.get("services", {}),
            "write_checks": write_checks,
            "oauth_refresh": self.refresh_oauth(),
            "retry": {"configured_attempts": getattr(self.manager, "retry_attempts", 3), "status": "configured"},
            "timeout": {"configured_seconds": getattr(self.manager, "timeout_seconds", 10.0), "status": "configured"},
            "dry_run": True,
            "approval_required": True,
            "execute_allowed": False,
            "production_actions_enabled": False,
        }
