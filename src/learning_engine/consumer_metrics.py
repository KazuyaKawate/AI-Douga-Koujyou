from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class ConsumerMetricSnapshot:
    read_requests: int
    documents_considered: int
    documents_returned: int
    documents_rejected_by_policy: int


class KnowledgeMetrics:
    """Process-local observation only; no persistence or external transmission."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._values = [0, 0, 0, 0]

    def record(self, *, considered: int, returned: int, rejected_by_policy: int) -> None:
        with self._lock:
            self._values[0] += 1
            self._values[1] += considered
            self._values[2] += returned
            self._values[3] += rejected_by_policy

    def snapshot(self) -> ConsumerMetricSnapshot:
        with self._lock:
            return ConsumerMetricSnapshot(*self._values)

