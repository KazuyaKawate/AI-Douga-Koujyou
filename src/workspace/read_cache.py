"""In-memory cache for sanitized GWOS-4 projections only."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any, Callable


class ProjectionReadCache:
    """Process-local cache; never persists Google responses or Knowledge."""

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._items: dict[str, tuple[datetime, dict[str, Any]]] = {}

    def put(self, key: str, projection: dict[str, Any], *, ttl_seconds: int) -> bool:
        if ttl_seconds < 1 or ttl_seconds > 3600:
            return False
        if projection.get("validation_status") != "valid":
            return False
        if projection.get("payload_sanitized") is not True or projection.get("workspace_read_only") is not True:
            return False
        if projection.get("approval_required") is not True or projection.get("review_required") is not True:
            return False
        expires_at = self._now() + timedelta(seconds=ttl_seconds)
        approval_expiry = self._parse_expiry(projection.get("approval_expires_at"))
        if approval_expiry is None or expires_at > approval_expiry:
            return False
        self._items[key] = (expires_at, deepcopy(projection))
        return True

    def get(self, key: str) -> dict[str, Any] | None:
        item = self._items.get(key)
        if item is None:
            return None
        expires_at, projection = item
        if expires_at <= self._now():
            self._items.pop(key, None)
            return None
        return deepcopy(projection)

    def _now(self) -> datetime:
        value = self._clock()
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _parse_expiry(value: Any) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
        return parsed if parsed.tzinfo is not None else None
