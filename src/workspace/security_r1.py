"""SECURITY-R1 offline health and explicit operational-read gate.

This module performs validation only.  It does not import Google libraries,
read credentials, construct transports, retry, or execute a read.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

OFFLINE_NOT_CHECKED = "OFFLINE_NOT_CHECKED"
LIVE_READ_BLOCKED = "LIVE_READ_BLOCKED"
LIVE_READ_APPROVED_NOT_EXECUTED = "LIVE_READ_APPROVED_NOT_EXECUTED"
LIVE_READ_SUCCESS = "LIVE_READ_SUCCESS"
LIVE_READ_FAILED = "LIVE_READ_FAILED"


@dataclass(frozen=True)
class OperationalReadRequest:
    explicit_human_approval: bool
    approval_id: str
    approval_expires_at: str
    resource: str
    operation: str
    scopes: tuple[str, ...]
    offline: bool
    write_allowed: bool


def validate_operational_read(
    request: OperationalReadRequest,
    *,
    allowed_resources: Iterable[str],
    allowed_operation: str,
    now: datetime | None = None,
) -> dict[str, object]:
    """Fail closed before any credential, client, transport, or network work."""
    errors: list[str] = []
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if request.explicit_human_approval is not True:
        errors.append("explicit_human_approval_required")
    if not request.approval_id.strip():
        errors.append("approval_id_required")
    try:
        expiry = datetime.fromisoformat(request.approval_expires_at.replace("Z", "+00:00"))
        if expiry.tzinfo is None or expiry <= current:
            errors.append("approval_expired")
    except (AttributeError, TypeError, ValueError):
        errors.append("approval_expiry_invalid")
    if request.resource not in frozenset(allowed_resources):
        errors.append("resource_not_allowlisted")
    if request.operation != allowed_operation:
        errors.append("operation_mismatch")
    if not request.scopes or any(not scope.endswith(".readonly") for scope in request.scopes):
        errors.append("read_only_scope_required")
    if request.offline is not False:
        errors.append("offline_false_required")
    if request.write_allowed is not False:
        errors.append("write_must_be_disabled")
    return {
        "status": LIVE_READ_BLOCKED if errors else LIVE_READ_APPROVED_NOT_EXECUTED,
        "gate_passed": not errors,
        "errors": errors,
        "network_request_observed": False,
        "workspace_read_observed": False,
        "workspace_write_observed": False,
        "external_retry_count": 0,
    }
