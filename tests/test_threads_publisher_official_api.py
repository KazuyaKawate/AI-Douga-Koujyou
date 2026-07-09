from __future__ import annotations

from src.publish_engine.threads_publisher import ThreadsPublisher


class FakeManager:
    def __init__(self) -> None:
        self.calls = []

    def create_post(self, connector: str, text: str, *, dry_run: bool = True):
        self.calls.append(("create", connector, text, dry_run))
        return {"ok": True, "status": "dry_run" if dry_run else "created", "dry_run": dry_run, "body": {"id": "creation-1"}}

    def publish_post(self, connector: str, creation_id: str, *, dry_run: bool = True):
        self.calls.append(("publish", connector, creation_id, dry_run))
        return {"ok": True, "status": "dry_run" if dry_run else "published", "dry_run": dry_run, "body": {"id": "post-1"}}


def test_threads_publisher_dry_run_uses_meta_official_api_adapter() -> None:
    manager = FakeManager()

    result = ThreadsPublisher(manager=manager).publish({"content": {"text": "hello", "image_prompt": "image", "thread": ["reply"]}}, dry_run=True)

    assert result["status"] == "dry_run"
    assert result["api"] == "meta_official_threads_api"
    assert result["image_attached"] is True
    assert result["thread_post"] is True
    assert manager.calls == [("create", "threads", "hello", True), ("publish", "threads", "creation-1", True)]


def test_threads_publisher_live_flow_uses_create_then_publish() -> None:
    manager = FakeManager()

    result = ThreadsPublisher(manager=manager).publish({"content": {"text": "real post"}}, dry_run=False)

    assert result["status"] == "published"
    assert result["dry_run"] is False
    assert result["external_id"] == "post-1"
    assert manager.calls == [("create", "threads", "real post", False), ("publish", "threads", "creation-1", False)]
