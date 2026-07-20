"""GWOS-4 allowlisted Google Workspace operational read adapter.

Only Sheets values, Drive metadata, Gmail metadata, and Calendar event metadata
are supported.  Every operation requires an unexpired explicit grant.  The
adapter contains no create/update/delete/send methods.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping


SHEETS_READ = "google_sheets_read"
DRIVE_METADATA_READ = "google_drive_metadata_read"
GMAIL_METADATA_READ = "gmail_metadata_read"
CALENDAR_READ = "google_calendar_read"

ALLOWED_OPERATIONS = frozenset({SHEETS_READ, DRIVE_METADATA_READ, GMAIL_METADATA_READ, CALENDAR_READ})
ALLOWED_FIELDS: dict[str, frozenset[str]] = {
    SHEETS_READ: frozenset({"metric_id", "value", "unit", "project_id", "customer_id", "status", "next_action", "due_at", "owner", "evidence_ref"}),
    DRIVE_METADATA_READ: frozenset({"id", "mimeType", "modifiedTime", "parents"}),
    GMAIL_METADATA_READ: frozenset({"id", "threadId", "internalDate", "labelIds"}),
    CALENDAR_READ: frozenset({"id", "status", "start", "end", "updated"}),
}
GWOS5_ALLOWED_FIELDS: dict[str, frozenset[str]] = {
    SHEETS_READ: ALLOWED_FIELDS[SHEETS_READ],
    DRIVE_METADATA_READ: frozenset({"name", "id", "mimeType", "modifiedTime", "parents"}),
    GMAIL_METADATA_READ: frozenset({"subject", "from", "date"}),
    CALENDAR_READ: frozenset({"start", "end", "title"}),
}


class WorkspaceReadDenied(ValueError):
    """Raised when a read does not satisfy the Operational Access Policy."""


@dataclass(frozen=True)
class ReadGrant:
    operation: str
    resource_id: str
    purpose: str
    approval_id: str
    approval_expires_at: str
    allowed_fields: tuple[str, ...]
    max_records: int = 50
    dry_run: bool = True
    contract_version: str = "gwos4"
    owner_approved: bool = False


class GoogleWorkspaceReadAdapter:
    """Execute minimum-field Google Workspace reads through injected clients."""

    def __init__(
        self,
        *,
        service_provider: Callable[[str], Any],
        resource_allowlist: Mapping[str, set[str] | frozenset[str]],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not callable(service_provider):
            raise TypeError("service_provider must be callable")
        self._service_provider = service_provider
        self._allowlist = {key: frozenset(value) for key, value in resource_allowlist.items()}
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._request_count = 0

    def read(self, grant: ReadGrant, *, parameters: Mapping[str, Any] | None = None) -> dict[str, Any]:
        self._validate_grant(grant)
        params = dict(parameters or {})
        before = self._request_count
        if grant.operation == SHEETS_READ:
            records = self._read_sheets(grant, params)
        elif grant.operation == DRIVE_METADATA_READ:
            records = self._read_drive(grant, params)
        elif grant.operation == GMAIL_METADATA_READ:
            records = self._read_gmail(grant, params)
        elif grant.operation == CALENDAR_READ:
            records = self._read_calendar(grant, params)
        else:  # guarded above; retained as fail-closed defense
            raise WorkspaceReadDenied("operation_not_allowed")
        request_count = self._request_count - before
        return {
            "operation": grant.operation,
            "contract_version": grant.contract_version,
            "resource_id": grant.resource_id,
            "purpose": grant.purpose,
            "approval_id": grant.approval_id,
            "approval_expires_at": grant.approval_expires_at,
            "allowed_fields": list(grant.allowed_fields),
            "status": "ready_for_projection",
            "validation_status": "valid",
            "records": records[: grant.max_records],
            "record_count": min(len(records), grant.max_records),
            "network_request_count": request_count,
            "network_request_observed": request_count > 0,
            "workspace_request_sent": request_count > 0,
            "external_request_sent": False,
            "workspace_read_only": True,
            "approval_required": True,
            "review_required": True,
            "execute_allowed": True,
            "execution_scope": "operational_workspace_read_only",
            "dry_run": True,
            "workspace_write_allowed": False,
            "mail_send_allowed": False,
            "knowledge_write_allowed": False,
            "production_change_allowed": False,
            "decision_auto_registration_allowed": False,
            "raw_json_retained": False,
            "audit_event": {
                "operation": grant.operation,
                "resource_id": grant.resource_id,
                "approval_id": grant.approval_id,
                "request_count": request_count,
                "network_request_observed": request_count > 0,
                "workspace_read_only": True,
            },
        }

    def _validate_grant(self, grant: ReadGrant) -> None:
        if grant.operation not in ALLOWED_OPERATIONS:
            raise WorkspaceReadDenied("operation_not_allowed")
        if grant.dry_run is not True:
            raise WorkspaceReadDenied("dry_run_required")
        if not grant.resource_id.strip() or grant.resource_id not in self._allowlist.get(grant.operation, frozenset()):
            raise WorkspaceReadDenied("resource_not_allowlisted")
        if not grant.purpose.strip():
            raise WorkspaceReadDenied("purpose_required")
        if not grant.approval_id.strip():
            raise WorkspaceReadDenied("approval_required")
        expiry = self._parse_datetime(grant.approval_expires_at)
        now = self._clock()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        if expiry <= now:
            raise WorkspaceReadDenied("approval_expired")
        if grant.contract_version not in {"gwos4", "gwos5"}:
            raise WorkspaceReadDenied("contract_version_unknown")
        if grant.contract_version == "gwos5" and grant.owner_approved is not True:
            raise WorkspaceReadDenied("owner_approval_required")
        fields = tuple(dict.fromkeys(grant.allowed_fields))
        field_policy = GWOS5_ALLOWED_FIELDS if grant.contract_version == "gwos5" else ALLOWED_FIELDS
        if not fields or set(fields) - field_policy[grant.operation]:
            raise WorkspaceReadDenied("field_not_allowed")
        if grant.max_records < 1 or grant.max_records > 100:
            raise WorkspaceReadDenied("max_records_out_of_range")

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise WorkspaceReadDenied("approval_expiry_invalid") from exc
        if parsed.tzinfo is None:
            raise WorkspaceReadDenied("approval_expiry_timezone_required")
        return parsed

    def _read_sheets(self, grant: ReadGrant, params: dict[str, Any]) -> list[dict[str, Any]]:
        spreadsheet_id = self._required(params, "spreadsheet_id")
        range_name = self._required(params, "range")
        if grant.resource_id != f"{spreadsheet_id}:{range_name}":
            raise WorkspaceReadDenied("resource_parameter_mismatch")
        request = self._service_provider("sheets").spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            majorDimension="ROWS",
        )
        rows = self._execute(request).get("values", [])
        if not rows:
            return []
        headers = [str(value).strip() for value in rows[0]]
        if len(headers) != len(set(headers)):
            raise WorkspaceReadDenied("duplicate_sheet_header")
        if set(grant.allowed_fields) - set(headers):
            raise WorkspaceReadDenied("required_sheet_header_missing")
        selected = [(index, name) for index, name in enumerate(headers) if name in grant.allowed_fields]
        return [
            {name: row[index] if index < len(row) else None for index, name in selected}
            for row in rows[1 : grant.max_records + 1]
            if isinstance(row, list)
        ]

    def _read_drive(self, grant: ReadGrant, params: dict[str, Any]) -> list[dict[str, Any]]:
        folder_id = self._required(params, "folder_id")
        if grant.resource_id != folder_id:
            raise WorkspaceReadDenied("resource_parameter_mismatch")
        fields = ",".join(grant.allowed_fields)
        request = self._service_provider("drive").files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            pageSize=grant.max_records,
            fields=f"files({fields})",
        )
        items = self._execute(request).get("files", [])
        return self._sanitize(items, grant.allowed_fields)

    def _read_gmail(self, grant: ReadGrant, params: dict[str, Any]) -> list[dict[str, Any]]:
        user_id = self._required(params, "user_id")
        query = self._required(params, "query")
        if grant.resource_id != f"{user_id}:{query}":
            raise WorkspaceReadDenied("resource_parameter_mismatch")
        service = self._service_provider("gmail")
        listed = self._execute(service.users().messages().list(
            userId=user_id,
            q=query,
            maxResults=grant.max_records,
            fields="messages(id,threadId)",
        )).get("messages", [])
        records: list[dict[str, Any]] = []
        gwos5 = grant.contract_version == "gwos5"
        api_fields = "payload(headers)" if gwos5 else ",".join(grant.allowed_fields)
        for item in listed[: grant.max_records]:
            message_id = str(item.get("id", ""))
            if not message_id:
                continue
            metadata = self._execute(service.users().messages().get(
                userId=user_id,
                id=message_id,
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"] if gwos5 else [],
                fields=api_fields,
            ))
            if gwos5:
                headers = metadata.get("payload", {}).get("headers", []) if isinstance(metadata.get("payload"), Mapping) else []
                values = {str(header.get("name", "")).lower(): header.get("value") for header in headers if isinstance(header, Mapping)}
                records.append({field: values.get(field) for field in grant.allowed_fields})
            else:
                records.append({field: metadata.get(field) for field in grant.allowed_fields})
        return records

    def _read_calendar(self, grant: ReadGrant, params: dict[str, Any]) -> list[dict[str, Any]]:
        calendar_id = self._required(params, "calendar_id")
        if grant.resource_id != calendar_id:
            raise WorkspaceReadDenied("resource_parameter_mismatch")
        time_min = self._parse_datetime(self._required(params, "time_min"))
        time_max = self._parse_datetime(self._required(params, "time_max"))
        if time_max <= time_min or time_max - time_min > timedelta(days=31):
            raise WorkspaceReadDenied("calendar_window_not_allowed")
        api_fields = ["summary" if field == "title" else field for field in grant.allowed_fields]
        request = self._service_provider("calendar").events().list(
            calendarId=calendar_id,
            timeMin=time_min.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=grant.max_records,
            singleEvents=True,
            orderBy="startTime",
            fields=f"items({','.join(api_fields)})",
        )
        items = self._execute(request).get("items", [])
        if grant.contract_version == "gwos5":
            return [{field: item.get("summary" if field == "title" else field) for field in grant.allowed_fields} for item in items if isinstance(item, Mapping)]
        return self._sanitize(items, grant.allowed_fields)

    def _execute(self, request: Any) -> dict[str, Any]:
        if not hasattr(request, "execute"):
            raise TypeError("Google API request must expose execute()")
        self._request_count += 1
        result = request.execute()
        return dict(result) if isinstance(result, Mapping) else {}

    @staticmethod
    def _sanitize(items: Any, fields: tuple[str, ...]) -> list[dict[str, Any]]:
        if not isinstance(items, list):
            return []
        return [{field: item.get(field) for field in fields} for item in items if isinstance(item, Mapping)]

    @staticmethod
    def _required(params: Mapping[str, Any], key: str) -> str:
        value = str(params.get(key, "")).strip()
        if not value:
            raise WorkspaceReadDenied(f"{key}_required")
        return value
