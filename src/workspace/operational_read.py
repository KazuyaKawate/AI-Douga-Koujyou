"""GWOS-5 Operational Workspace Read activation layer."""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping

from src.workspace.read_adapter import (
    CALENDAR_READ, DRIVE_METADATA_READ, GMAIL_METADATA_READ, SHEETS_READ,
    GoogleWorkspaceReadAdapter, ReadGrant, WorkspaceReadDenied,
)
from src.workspace.read_cache import ProjectionReadCache

BUS2_OPERATIONAL_SHEETS = frozenset({
    "Leads", "Projects", "Revenue", "Knowledge", "Learning", "Tasks",
    "Dashboard", "Customer Success",
})
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_SECRET = re.compile(r"(?i)(api[_-]?key|secret|token|password|bearer\s+[a-z0-9._-]+)")


@dataclass(frozen=True)
class OperationalSource:
    source_id: str
    operation: str
    resource_id: str
    owner_approved: bool
    approval_id: str
    approval_expires_at: str
    purpose: str
    allowed_fields: tuple[str, ...]
    parameters: Mapping[str, Any]
    sheet_name: str | None = None
    max_records: int = 50
    cache_ttl_seconds: int = 300


class GWOS5ProjectionLayer:
    """GWOS-3-compatible, deterministic, fail-closed sanitized projection."""
    CONTRACT_VERSION = "gwos5-operational-read-v1"

    def project(self, results: Iterable[Mapping[str, Any]], *, as_of: str) -> dict[str, Any]:
        sources = [dict(item) for item in results]
        if not sources:
            return self._blocked(as_of, "SOURCE_NOT_FOUND")
        if any(item.get("validation_status") != "valid" or item.get("contract_version") != "gwos5" for item in sources):
            return self._blocked(as_of, "SOURCE_INVALID")
        records = {SHEETS_READ: [], DRIVE_METADATA_READ: [], GMAIL_METADATA_READ: [], CALENDAR_READ: []}
        try:
            for source in sources:
                operation = str(source.get("operation"))
                for row in source.get("records", []):
                    if isinstance(row, Mapping):
                        records.setdefault(operation, []).append(self._sanitize(operation, row))
        except WorkspaceReadDenied as exc:
            return self._blocked(as_of, str(exc).upper())
        encoded = json.dumps(records, ensure_ascii=False, default=str)
        if _EMAIL.search(encoded) or _SECRET.search(encoded):
            return self._blocked(as_of, "PII_OR_SECRET_DETECTED")
        counts = {key: len(value) for key, value in records.items()}
        expiries = sorted(str(item["approval_expires_at"]) for item in sources if item.get("approval_expires_at"))
        refs = [f"{item['operation']}:{self._opaque(str(item['resource_id']))}:{item['approval_id']}" for item in sources]
        payload: dict[str, Any] = {
            "phase": "GWOS-5", "contract_version": self.CONTRACT_VERSION, "as_of": as_of,
            "status": "ready_for_review", "validation_status": "valid", "freshness_state": "fresh",
            "redaction_applied": True, "payload_sanitized": True, "raw_json_retained": False,
            "source_refs": refs, "source_counts": counts,
            "approval_expires_at": expiries[0] if expiries else None,
            "consumers": {
                "dashboard": {"projection_only": True, "source_counts": counts, "operational_metrics": records[SHEETS_READ]},
                "daily_operation": {"projection_only": True, "drive": records[DRIVE_METADATA_READ], "gmail": records[GMAIL_METADATA_READ], "calendar": records[CALENDAR_READ]},
                "commander": {"proposal_only": True, "execute_allowed": False, "source_counts": counts},
                "learning": {"proposal_only": True, "automatic_learning": False, "automatic_implementation": False},
                "knowledge": {"ssot": "aios_local", "automatic_promotion": False, "write_performed": False},
            },
            "approval_required": True, "review_required": True, "execute_allowed": True,
            "execution_scope": "operational_workspace_read_only", "dry_run": True,
            "workspace_read_only": True, "workspace_write_allowed": False, "mail_send_allowed": False,
            "calendar_update_allowed": False, "sns_post_allowed": False,
            "decision_auto_registration_allowed": False, "production_change_allowed": False,
            "knowledge_write_allowed": False,
        }
        payload["lineage_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
        payload["projection_id"] = "gwos5-" + payload["lineage_hash"][:16]
        return payload

    def _sanitize(self, operation: str, row: Mapping[str, Any]) -> dict[str, Any]:
        if operation == DRIVE_METADATA_READ:
            return {"file_ref": self._opaque(str(row.get("id", ""))), "name_redacted": True,
                    "mime_type": row.get("mimeType"), "modified_time": row.get("modifiedTime"),
                    "parent_refs": [self._opaque(str(value)) for value in row.get("parents", []) if value]}
        if operation == GMAIL_METADATA_READ:
            return {"subject_redacted": True, "from_redacted": True, "date": row.get("date")}
        if operation == CALENDAR_READ:
            return {"start": deepcopy(row.get("start")), "end": deepcopy(row.get("end")), "title_redacted": True}
        allowed = {"metric_id", "value", "unit", "project_id", "customer_id", "status", "next_action", "due_at", "owner", "evidence_ref"}
        safe = {key: deepcopy(value) for key, value in row.items() if key in allowed}
        text = json.dumps(safe, ensure_ascii=False, default=str)
        if _EMAIL.search(text) or _SECRET.search(text):
            raise WorkspaceReadDenied("pii_or_secret_detected")
        return safe

    @staticmethod
    def _opaque(value: str) -> str:
        return "ref-" + hashlib.sha256(value.encode()).hexdigest()[:12] if value else "ref-missing"

    def _blocked(self, as_of: str, code: str) -> dict[str, Any]:
        return {"phase": "GWOS-5", "contract_version": self.CONTRACT_VERSION, "as_of": as_of,
                "status": "blocked", "validation_status": "invalid", "freshness_state": "unknown",
                "payload_sanitized": True, "raw_json_retained": False, "error_codes": [code],
                "consumers": {}, "execute_allowed": True, "execution_scope": "operational_workspace_read_only",
                "workspace_write_allowed": False, "production_change_allowed": False}


class OperationalWorkspaceReadLayer:
    """Read approved sources and return/cache only sanitized projections."""
    def __init__(self, *, adapter: GoogleWorkspaceReadAdapter, sources: Iterable[OperationalSource],
                 cache: ProjectionReadCache | None = None, clock: Callable[[], datetime] | None = None,
                 credential_mode: str = "mock", live_connection_approved: bool = False) -> None:
        if credential_mode != "mock" and live_connection_approved is not True:
            raise WorkspaceReadDenied("live_google_owner_approval_required")
        self._adapter = adapter
        self._sources = {source.source_id: source for source in sources}
        self._cache = cache or ProjectionReadCache(clock=clock)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._credential_mode = credential_mode
        self._projector = GWOS5ProjectionLayer()

    def read_projection(self, source_ids: Iterable[str], *, as_of: str) -> dict[str, Any]:
        selected: list[OperationalSource] = []
        for source_id in source_ids:
            source = self._sources.get(source_id)
            if source is None:
                raise WorkspaceReadDenied("source_not_allowlisted")
            if source.owner_approved is not True:
                raise WorkspaceReadDenied("owner_approval_required")
            if source.operation == SHEETS_READ and source.sheet_name not in BUS2_OPERATIONAL_SHEETS:
                raise WorkspaceReadDenied("sheet_not_bus2_operational_ssot")
            selected.append(source)
        raw_results = []
        for source in selected:
            grant = ReadGrant(operation=source.operation, resource_id=source.resource_id, purpose=source.purpose,
                              approval_id=source.approval_id, approval_expires_at=source.approval_expires_at,
                              allowed_fields=source.allowed_fields, max_records=source.max_records, dry_run=True,
                              contract_version="gwos5", owner_approved=True)
            raw_results.append(self._adapter.read(grant, parameters=source.parameters))
        projection = self._projector.project(raw_results, as_of=as_of)
        raw_results.clear()
        ttl = min((source.cache_ttl_seconds for source in selected), default=300)
        key = self._cache_key(selected)
        projection["cache_key"] = key
        projection["cache_ttl_seconds"] = ttl
        projection["cached"] = self._cache.put(key, projection, ttl_seconds=ttl)
        projection["credential_mode"] = self._credential_mode
        projection["google_live_connection"] = self._credential_mode != "mock"
        return deepcopy(projection)

    def cached_projection(self, source_ids: Iterable[str]) -> dict[str, Any]:
        selected = [self._sources[source_id] for source_id in source_ids if source_id in self._sources]
        value = self._cache.get(self._cache_key(selected))
        if value is None:
            return {"cache_state": "stale_or_miss", "freshness_state": "stale", "projection": None}
        return {"cache_state": "fresh", "freshness_state": "fresh", "projection": value}

    @staticmethod
    def _cache_key(sources: Iterable[OperationalSource]) -> str:
        joined = "|".join(sorted(source.source_id for source in sources))
        return "gwos5:" + hashlib.sha256(joined.encode()).hexdigest()[:16]
