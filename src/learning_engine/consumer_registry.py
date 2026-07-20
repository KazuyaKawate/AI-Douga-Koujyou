from __future__ import annotations

from threading import RLock

from src.learning_engine.consumer_context import ConsumerContext


class ConsumerRegistry:
    SUPPORTED_CONSUMERS = frozenset({
        "content_engine", "website_generator", "sales_engine", "revenue_engine",
        "seo_engine", "blog_engine", "marketing_engine",
    })

    def __init__(self) -> None:
        self._contexts: dict[str, ConsumerContext] = {}
        self._lock = RLock()

    def register(self, context: ConsumerContext) -> None:
        if context.consumer_id not in self.SUPPORTED_CONSUMERS:
            raise ValueError(f"Unsupported knowledge consumer: {context.consumer_id}")
        with self._lock:
            if context.consumer_id in self._contexts:
                raise ValueError(f"Consumer already registered: {context.consumer_id}")
            self._contexts[context.consumer_id] = context

    def get(self, consumer_id: str) -> ConsumerContext:
        key = consumer_id.strip().lower()
        with self._lock:
            if key not in self._contexts:
                raise KeyError(f"Consumer is not registered: {key}")
            return self._contexts[key]

    def list_consumer_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._contexts))

