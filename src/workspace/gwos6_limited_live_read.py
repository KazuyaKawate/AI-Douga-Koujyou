"""GWOS-6 limited Google Sheets live-read boundary.

This module is inert until ``execute`` is called with the exact human approval
phrase.  Network access is injected; importing or constructing these classes
never accesses Google or reads credential contents.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


BLOCKED = "GWOS-6 LIVE READ BLOCKED / OWNER INPUT REQUIRED"
NO_GO = "GWOS-6 NO-GO"
PASS = "GWOS-6 LIMITED LIVE READ PASS / HUMAN REVIEW REQUIRED"
APPROVAL_PHRASE = "限定Live Readを承認します"

TASK_FIELDS = (
    "task_id", "title", "status", "priority", "due_date", "owner",
    "source_updated_at",
)
REVENUE_FIELDS = (
    "transaction_id", "status", "gross_amount", "fee_amount", "net_amount",
    "currency", "evidence_status", "recorded_at",
)
OWNER_REQUIRED_FIELDS = (
    "workspace_owner", "credential_file", "spreadsheet_id", "tasks_sheet",
    "tasks_range", "revenue_sheet", "revenue_range", "tasks_headers",
    "revenue_headers", "approval_id", "approved_by", "effective_from",
    "expires_at", "cache_ttl_seconds", "stop_owner",
)
READ_ONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"
_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE = re.compile(r"(?<!\d)(?:\+\d[\d ()-]{7,}\d|0\d{1,4}-\d{1,4}-\d{3,4})(?!\d)")
_SECRET = re.compile(
    r"(?i)(api[_-]?key|client[_-]?secret|private[_-]?key|password|"
    r"bearer\s+[a-z0-9._-]+|ya29\.[a-z0-9._-]+)"
)


class GWOS6Denied(ValueError):
    """Raised before or during a fail-closed limited read."""


@dataclass(frozen=True)
class OwnerActivation:
    workspace_owner: str
    credential_file: str
    spreadsheet_id: str
    tasks_sheet: str
    tasks_range: str
    revenue_sheet: str
    revenue_range: str
    tasks_headers: tuple[str, ...]
    revenue_headers: tuple[str, ...]
    approval_id: str
    approved_by: str
    effective_from: str
    expires_at: str
    cache_ttl_seconds: int
    stop_owner: str
    owner_allowlist: tuple[str, ...]
    oauth_scopes: tuple[str, ...] = (READ_ONLY_SCOPE,)
    max_records: int = 50
    approval_required: bool = True
    review_required: bool = True
    dry_run: bool = True
    workspace_write_allowed: bool = False
    knowledge_write_allowed: bool = False
    production_actions_enabled: bool = False

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "OwnerActivation":
        missing = [name for name in OWNER_REQUIRED_FIELDS if not _present(value.get(name))]
        if missing:
            raise GWOS6Denied(f"{BLOCKED}: {','.join(missing)}")
        try:
            return cls(
                workspace_owner=str(value["workspace_owner"]).strip(),
                credential_file=str(value["credential_file"]).strip(),
                spreadsheet_id=str(value["spreadsheet_id"]).strip(),
                tasks_sheet=str(value["tasks_sheet"]).strip(),
                tasks_range=str(value["tasks_range"]).strip(),
                revenue_sheet=str(value["revenue_sheet"]).strip(),
                revenue_range=str(value["revenue_range"]).strip(),
                tasks_headers=tuple(str(x).strip() for x in value["tasks_headers"]),
                revenue_headers=tuple(str(x).strip() for x in value["revenue_headers"]),
                approval_id=str(value["approval_id"]).strip(),
                approved_by=str(value["approved_by"]).strip(),
                effective_from=str(value["effective_from"]).strip(),
                expires_at=str(value["expires_at"]).strip(),
                cache_ttl_seconds=int(value["cache_ttl_seconds"]),
                stop_owner=str(value["stop_owner"]).strip(),
                owner_allowlist=tuple(str(x).strip() for x in value.get("owner_allowlist", ())),
                oauth_scopes=tuple(str(x).strip() for x in value.get("oauth_scopes", (READ_ONLY_SCOPE,))),
                max_records=int(value.get("max_records", 50)),
                approval_required=value.get("approval_required", True) is True,
                review_required=value.get("review_required", True) is True,
                dry_run=value.get("dry_run", True) is True,
                workspace_write_allowed=value.get("workspace_write_allowed", False) is True,
                knowledge_write_allowed=value.get("knowledge_write_allowed", False) is True,
                production_actions_enabled=value.get("production_actions_enabled", False) is True,
            )
        except (TypeError, ValueError) as exc:
            raise GWOS6Denied(f"{NO_GO}: owner_configuration_invalid") from exc


class ProjectionTTLCache:
    """Process-local cache for sanitized projections only."""

    def __init__(self, clock: Callable[[], datetime]) -> None:
        self._clock = clock
        self._item: tuple[datetime, dict[str, Any]] | None = None

    def put(self, projection: Mapping[str, Any], ttl_seconds: int) -> int:
        if ttl_seconds < 1 or ttl_seconds > 3600:
            return 0
        self._item = (self._clock() + timedelta(seconds=ttl_seconds), deepcopy(dict(projection)))
        return len(projection.get("tasks", [])) + len(projection.get("revenue", {}).get("records", []))

    def get(self) -> dict[str, Any] | None:
        if self._item is None:
            return None
        expires, value = self._item
        if expires <= self._clock():
            self._item = None
            return None
        return deepcopy(value)

    def clear(self) -> None:
        self._item = None


class GWOS6LimitedLiveRead:
    """One-shot Tasks/Revenue reader with a strict pre-network gate."""

    def __init__(
        self,
        *,
        activation: Mapping[str, Any],
        sheets_fetcher: Callable[[str, str, int], Sequence[Sequence[Any]]],
        clock: Callable[[], datetime] | None = None,
        credential_path_exists: Callable[[str], bool] | None = None,
    ) -> None:
        self._activation_input = deepcopy(dict(activation))
        self._fetch = sheets_fetcher
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._path_exists = credential_path_exists or (lambda value: Path(value).is_file())
        self._executed = False
        self._cache = ProjectionTTLCache(self._now)

    def gate_report(self, *, approval_statement: str = "") -> dict[str, Any]:
        missing = [name for name in OWNER_REQUIRED_FIELDS if not _present(self._activation_input.get(name))]
        if missing:
            return self._gate(BLOCKED, False, missing, ["owner_input_incomplete"])
        try:
            cfg = OwnerActivation.from_mapping(self._activation_input)
            errors = self._validate_gate(cfg, approval_statement)
        except GWOS6Denied as exc:
            return self._gate(NO_GO, False, [], [str(exc)])
        return self._gate(PASS if not errors else NO_GO, not errors, [], errors)

    def execute(self, *, approval_statement: str, executed_by: str) -> dict[str, Any]:
        """Run exactly two requests (Tasks and Revenue), never retrying here."""
        if self._executed:
            raise GWOS6Denied(f"{NO_GO}: one_shot_already_executed")
        gate = self.gate_report(approval_statement=approval_statement)
        if not gate["gate_passed"]:
            raise GWOS6Denied(gate["decision"])
        cfg = OwnerActivation.from_mapping(self._activation_input)
        self._executed = True
        fetched_count = projected_count = rejected_count = 0
        raw_tasks: list[list[Any]] = []
        raw_revenue: list[list[Any]] = []
        try:
            raw_tasks = [list(row) for row in self._fetch(cfg.spreadsheet_id, cfg.tasks_range, cfg.max_records + 1)]
            raw_revenue = [list(row) for row in self._fetch(cfg.spreadsheet_id, cfg.revenue_range, cfg.max_records + 1)]
            fetched_count = max(0, len(raw_tasks) - 1) + max(0, len(raw_revenue) - 1)
            tasks, task_rejected = self._project_tasks(raw_tasks, cfg)
            revenue, revenue_rejected = self._project_revenue(raw_revenue, cfg)
            projected_count = len(tasks) + len(revenue["records"])
            rejected_count = task_rejected + revenue_rejected
            projection = self._projection(cfg, tasks, revenue)
        except Exception:
            self._cache.clear()
            raise
        finally:
            raw_tasks.clear()
            raw_revenue.clear()
        cache_count = self._cache.put(projection, cfg.cache_ttl_seconds)
        audit = {
            "approval_id": cfg.approval_id,
            "executed_by": executed_by,
            "executed_at": self._now().isoformat(),
            "resource_type": "google_sheets",
            "sheet_name": [cfg.tasks_sheet, cfg.revenue_sheet],
            "range": [cfg.tasks_range, cfg.revenue_range],
            "fetched_count": fetched_count,
            "projected_count": projected_count,
            "rejected_count": rejected_count,
            "cache_count": cache_count,
            "network_request_observed": True,
            "workspace_read_observed": True,
            "workspace_write_observed": False,
            "knowledge_write_observed": False,
            "production_action_observed": False,
            "raw_response_retained": False,
            "request_count": 2,
            "retry_count": 0,
        }
        return {"decision": PASS, "gate": gate, "projection": projection, "audit": audit}

    def cached_projection(self) -> dict[str, Any] | None:
        return self._cache.get()

    def disable(self) -> dict[str, Any]:
        self._cache.clear()
        return {
            "status": "disabled", "cache_cleared": True, "execute_allowed": False,
            "workspace_write_allowed": False, "knowledge_write_allowed": False,
            "production_actions_enabled": False,
        }

    def _validate_gate(self, cfg: OwnerActivation, approval_statement: str) -> list[str]:
        errors: list[str] = []
        now = self._now()
        effective = _datetime(cfg.effective_from, "effective_from_invalid", errors)
        expiry = _datetime(cfg.expires_at, "expires_at_invalid", errors)
        checks = (
            (cfg.workspace_owner in cfg.owner_allowlist, "owner_allowlist_mismatch"),
            (approval_statement == APPROVAL_PHRASE, "explicit_human_approval_required"),
            (cfg.approved_by == cfg.workspace_owner, "approved_by_owner_mismatch"),
            (bool(cfg.approval_id), "approval_id_invalid"),
            (cfg.tasks_sheet == "Tasks", "tasks_sheet_mismatch"),
            (cfg.revenue_sheet == "Revenue", "revenue_sheet_mismatch"),
            (cfg.tasks_range.startswith(f"{cfg.tasks_sheet}!"), "tasks_range_mismatch"),
            (cfg.revenue_range.startswith(f"{cfg.revenue_sheet}!"), "revenue_range_mismatch"),
            (cfg.tasks_headers == TASK_FIELDS, "tasks_header_definition_mismatch"),
            (cfg.revenue_headers == REVENUE_FIELDS, "revenue_header_definition_mismatch"),
            (cfg.oauth_scopes == (READ_ONLY_SCOPE,), "read_only_scope_mismatch"),
            (1 <= cfg.max_records <= 100, "max_records_out_of_range"),
            (1 <= cfg.cache_ttl_seconds <= 3600, "cache_ttl_out_of_range"),
            (cfg.approval_required and cfg.review_required and cfg.dry_run, "fixed_safety_state_mismatch"),
            (not cfg.workspace_write_allowed, "workspace_write_permission_present"),
            (not cfg.knowledge_write_allowed, "knowledge_write_permission_present"),
            (not cfg.production_actions_enabled, "production_permission_present"),
            (self._path_exists(cfg.credential_file), "credential_reference_not_found"),
        )
        errors.extend(code for passed, code in checks if not passed)
        if effective is not None and now < effective:
            errors.append("approval_not_effective")
        if expiry is not None and now >= expiry:
            errors.append("approval_expired")
        if effective is not None and expiry is not None and effective >= expiry:
            errors.append("approval_window_invalid")
        return errors

    def _project_tasks(self, rows: list[list[Any]], cfg: OwnerActivation) -> tuple[list[dict[str, Any]], int]:
        records = self._rows(rows, cfg.tasks_headers)
        projected: list[dict[str, Any]] = []
        rejected = 0
        for row in records:
            safe = {field: row.get(field) for field in TASK_FIELDS}
            if _sensitive(safe):
                raise GWOS6Denied(f"{NO_GO}: pii_or_secret_detected")
            if not safe["task_id"] or not safe["title"]:
                rejected += 1
                continue
            projected.append(safe)
        return projected, rejected

    def _project_revenue(self, rows: list[list[Any]], cfg: OwnerActivation) -> tuple[dict[str, Any], int]:
        records = self._rows(rows, cfg.revenue_headers)
        projected: list[dict[str, Any]] = []
        rejected = 0
        verified_actuals: list[dict[str, Any]] = []
        for row in records:
            safe = {field: row.get(field) for field in REVENUE_FIELDS}
            if _sensitive(safe):
                raise GWOS6Denied(f"{NO_GO}: pii_or_secret_detected")
            if not safe["transaction_id"]:
                rejected += 1
                continue
            try:
                for field in ("gross_amount", "fee_amount", "net_amount"):
                    safe[field] = str(Decimal(str(safe[field])))
            except (InvalidOperation, TypeError, ValueError):
                rejected += 1
                continue
            projected.append(safe)
            status = str(safe["status"]).strip().lower()
            evidence = str(safe["evidence_status"]).strip().lower()
            if evidence == "verified" and status not in {"proposal", "estimated", "unverified"}:
                verified_actuals.append(safe)
        currencies = sorted({str(row["currency"]).upper() for row in verified_actuals if row["currency"]})
        if len(currencies) == 1:
            totals = {
                name: str(sum(Decimal(row[name]) for row in verified_actuals))
                for name in ("gross_amount", "fee_amount", "net_amount")
            }
            aggregate = {"status": "verified", "currency": currencies[0], **totals}
        elif len(currencies) > 1:
            aggregate = {"status": "currency_mismatch", "currencies": currencies, "gross_amount": None,
                         "fee_amount": None, "net_amount": None}
        else:
            aggregate = {"status": "no_verified_actuals", "currency": None, "gross_amount": "0",
                         "fee_amount": "0", "net_amount": "0"}
        return {"records": projected, "verified_actual_count": len(verified_actuals), "aggregate": aggregate}, rejected

    @staticmethod
    def _rows(rows: list[list[Any]], expected_headers: tuple[str, ...]) -> list[dict[str, Any]]:
        if not rows or tuple(str(value).strip() for value in rows[0]) != expected_headers:
            raise GWOS6Denied(f"{NO_GO}: live_header_mismatch")
        return [
            {header: row[index] if index < len(row) else None for index, header in enumerate(expected_headers)}
            for row in rows[1:]
        ]

    def _projection(self, cfg: OwnerActivation, tasks: list[dict[str, Any]], revenue: dict[str, Any]) -> dict[str, Any]:
        common = {
            "projection_only": True, "tasks": deepcopy(tasks), "revenue": deepcopy(revenue),
            "raw_data_retained": False,
        }
        return {
            "phase": "GWOS-6", "status": "human_review_required", "projected_at": self._now().isoformat(),
            "tasks": tasks, "revenue": revenue,
            "consumers": {
                "executive_dashboard": deepcopy(common), "daily_operation": deepcopy(common),
                "commander": {"proposal_only": True, "execute_allowed": False, "input": deepcopy(common)},
                "learning": {"proposal_only": True, "automatic_registration": False, "input": deepcopy(common)},
                "customer_workspace": {"raw_data_received": False},
                "knowledge": {"write_performed": False, "automatic_registration": False},
            },
            "approval_id": cfg.approval_id, "approval_required": True, "review_required": True,
            "dry_run": True, "execute_allowed": True, "workspace_read_only": True,
            "workspace_write_allowed": False, "mail_send_allowed": False,
            "knowledge_write_allowed": False, "production_actions_enabled": False,
            "raw_response_retained": False, "cache_ttl_seconds": cfg.cache_ttl_seconds,
        }

    @staticmethod
    def _gate(decision: str, passed: bool, missing: list[str], errors: list[str]) -> dict[str, Any]:
        return {
            "phase": "GWOS-6", "decision": decision, "gate_passed": passed,
            "missing_owner_inputs": missing, "errors": errors,
            "network_request_observed": False, "execute_allowed": passed,
            "workspace_read_only": passed, "workspace_write_allowed": False,
            "knowledge_write_allowed": False, "production_actions_enabled": False,
            "approval_required": True, "review_required": True, "dry_run": True,
        }

    def _now(self) -> datetime:
        value = self._clock()
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _present(value: Any) -> bool:
    return bool(value) and (not isinstance(value, (list, tuple)) or len(value) > 0)


def _datetime(value: str, code: str, errors: list[str]) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
        return parsed
    except (TypeError, ValueError):
        errors.append(code)
        return None


def _sensitive(value: Mapping[str, Any]) -> bool:
    encoded = json.dumps(value, ensure_ascii=False, default=str)
    return bool(_EMAIL.search(encoded) or _PHONE.search(encoded) or _SECRET.search(encoded))
