"""GWOS-4 sanitized consumer projection layer."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Iterable, Mapping

from src.workspace.read_adapter import (
    CALENDAR_READ,
    DRIVE_METADATA_READ,
    GMAIL_METADATA_READ,
    SHEETS_READ,
)


PROJECTION_SAFETY: dict[str, Any] = {
    "approval_required": True,
    "review_required": True,
    "execute_allowed": True,
    "execution_scope": "operational_workspace_read_only",
    "dry_run": True,
    "workspace_read_only": True,
    "workspace_write_allowed": False,
    "mail_send_allowed": False,
    "knowledge_write_allowed": False,
    "production_change_allowed": False,
    "engine_changed": False,
    "schema_changed": False,
    "queue_changed": False,
}


class WorkspaceReadProjectionLayer:
    """Map validated adapter results to four non-mutating AIOS consumers."""

    def project(self, results: Iterable[Mapping[str, Any]], *, as_of: str) -> dict[str, Any]:
        sources = [deepcopy(dict(item)) for item in results]
        if not sources:
            return self._blocked(as_of, "SOURCE_NOT_FOUND")
        if any(item.get("validation_status") != "valid" or item.get("workspace_read_only") is not True for item in sources):
            return self._blocked(as_of, "SOURCE_INVALID")
        by_operation = {str(item.get("operation")): item for item in sources}
        counts = {operation: int(by_operation.get(operation, {}).get("record_count", 0) or 0) for operation in (
            SHEETS_READ, DRIVE_METADATA_READ, GMAIL_METADATA_READ, CALENDAR_READ
        )}
        network_observed = any(item.get("network_request_observed") is True for item in sources)
        approval_expiries = sorted(str(item.get("approval_expires_at", "")) for item in sources if item.get("approval_expires_at"))
        source_refs = [f"{item.get('operation')}:{item.get('resource_id')}:{item.get('approval_id')}" for item in sources]
        sheet_records = self._records(by_operation.get(SHEETS_READ))
        drive_records = self._records(by_operation.get(DRIVE_METADATA_READ))
        gmail_records = self._records(by_operation.get(GMAIL_METADATA_READ))
        calendar_records = self._records(by_operation.get(CALENDAR_READ))
        envelope = {
            "phase": "GWOS-4",
            "as_of": as_of,
            "status": "ready_for_review",
            "validation_status": "valid",
            "payload_sanitized": True,
            "network_request_observed": network_observed,
            "source_refs": source_refs,
            "source_counts": counts,
            "approval_expires_at": approval_expiries[0] if approval_expiries else None,
            "external_request_sent": False,
            **PROJECTION_SAFETY,
        }
        consumers = {
            "executive_dashboard": {
                "operational_metrics": sheet_records,
                "drive_metadata_count": counts[DRIVE_METADATA_READ],
                "gmail_metadata_count": counts[GMAIL_METADATA_READ],
                "calendar_event_count": counts[CALENDAR_READ],
            },
            "daily_operation": {
                "workspace_status": "read_projection_ready",
                "operational_rows": sheet_records,
                "drive_metadata": drive_records,
                "gmail_metadata": gmail_records,
                "calendar_events": calendar_records,
            },
            "commander": {
                "proposal_only": True,
                "command_execute_allowed": False,
                "context_counts": counts,
                "source_refs": source_refs,
            },
            "customer_workspace": {
                "mode": "read_projection",
                "operational_rows": [self._select(row, {"project_id", "customer_id", "status", "next_action", "due_at", "owner", "evidence_ref"}) for row in sheet_records],
                "drive_metadata_refs": drive_records,
                "gmail_metadata_count": counts[GMAIL_METADATA_READ],
                "raw_customer_content_exposed": False,
            },
            "learning": {
                "proposal_only": True,
                "automatic_implementation": False,
                "operational_data_ingested": False,
                "knowledge_ssot": "aios_local",
            },
            "knowledge": {
                "ssot": "aios_local",
                "automatic_registration": False,
                "write_performed": False,
            },
        }
        payload = {**envelope, "consumers": consumers}
        payload["projection_id"] = "gwos4-" + hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:16]
        return payload

    @staticmethod
    def _records(source: Mapping[str, Any] | None) -> list[dict[str, Any]]:
        if not source or not isinstance(source.get("records"), list):
            return []
        return [deepcopy(dict(item)) for item in source["records"] if isinstance(item, Mapping)]

    @staticmethod
    def _select(row: Mapping[str, Any], fields: set[str]) -> dict[str, Any]:
        return {key: deepcopy(value) for key, value in row.items() if key in fields}

    @staticmethod
    def _blocked(as_of: str, error: str) -> dict[str, Any]:
        return {
            "phase": "GWOS-4",
            "as_of": as_of,
            "status": "blocked",
            "validation_status": "invalid",
            "payload_sanitized": True,
            "error_codes": [error],
            "network_request_observed": False,
            "consumers": {},
            **PROJECTION_SAFETY,
        }
