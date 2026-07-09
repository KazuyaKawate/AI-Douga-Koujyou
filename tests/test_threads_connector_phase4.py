from __future__ import annotations

from urllib import parse

from src.api_connectors.connectors import ThreadsConnector
from src.api_connectors.manager import APIConnectorManager


def test_threads_oauth_url_uses_official_threads_authorize_endpoint() -> None:
    url = ThreadsConnector.authorization_url(client_id="app-1", redirect_uri="https://example.com/callback", state="state-1")
    parsed = parse.urlparse(url)
    query = parse.parse_qs(parsed.query)

    assert url.startswith("https://threads.net/oauth/authorize?")
    assert query["client_id"] == ["app-1"]
    assert query["response_type"] == ["code"]
    assert query["scope"] == ["threads_basic,threads_content_publish"]


def test_threads_create_and_publish_dry_run() -> None:
    connector = ThreadsConnector({"credentials": {}, "dry_run_default": True})

    created = connector.create_post("hello", dry_run=True)
    published = connector.publish_post(created["body"]["id"], dry_run=True)

    assert created["status"] == "dry_run"
    assert created["dry_run"] is True
    assert published["status"] == "dry_run"
    assert published["dry_run"] is True


def test_threads_live_create_publish_success(monkeypatch) -> None:
    calls = []

    def fake_post(url, body):
        calls.append((url, body))
        if url.endswith("/threads"):
            return {"ok": True, "status_code": 200, "body": {"id": "creation-1"}}
        return {"ok": True, "status_code": 200, "body": {"id": "post-1"}}

    connector = ThreadsConnector({"plain_credentials": {"access_token": "token", "user_id": "user-1", "api_base": "https://graph.threads.net/v1.0"}})
    monkeypatch.setattr(connector, "_post_form", fake_post)

    created = connector.create_post("hello", dry_run=False)
    published = connector.publish_post(created["body"]["id"], dry_run=False)

    assert created["status"] == "created"
    assert published["status"] == "published"
    assert calls[0][0] == "https://graph.threads.net/v1.0/user-1/threads"
    assert calls[1][0] == "https://graph.threads.net/v1.0/user-1/threads_publish"


def test_complete_threads_oauth_saves_token_user_id_and_env(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("THREADS_ACCESS_TOKEN=old\nTHREADS_USER_ID=old\n", encoding="utf-8")
    monkeypatch.setattr("src.api_connectors.manager.DOTENV_PATH", env_path)

    def fake_exchange(self, **kwargs):
        return {"ok": True, "status_code": 200, "body": {"access_token": "token-new"}}

    def fake_profile(self):
        return {"ok": True, "status_code": 200, "body": {"id": "user-new", "username": "aios"}}

    monkeypatch.setattr(ThreadsConnector, "exchange_code_for_access_token", fake_exchange)
    monkeypatch.setattr(ThreadsConnector, "profile", fake_profile)

    manager = APIConnectorManager(path=tmp_path / "api_connectors.json")
    result = manager.complete_threads_oauth(code="code", client_id="app", client_secret="secret", redirect_uri="https://example.com/cb")

    saved = env_path.read_text(encoding="utf-8")
    assert result["ok"] is True
    assert "THREADS_ACCESS_TOKEN=token-new" in saved
    assert "THREADS_USER_ID=user-new" in saved
    assert "THREADS_API_BASE=https://graph.threads.net/v1.0" in saved
