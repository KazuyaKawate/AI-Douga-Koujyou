from __future__ import annotations

from src.api_connectors.connectors import ThreadsConnector
from src.utils import config


def test_official_workspace_uses_project_root_dotenv() -> None:
    assert config.OFFICIAL_WORKSPACE == config.PROJECT_ROOT
    assert config.DOTENV_PATH == config.PROJECT_ROOT / ".env"
    assert config.DOTENV_PATH.is_absolute()


def test_threads_connector_reads_threads_credentials_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("THREADS_ACCESS_TOKEN", "token-12345")
    monkeypatch.setenv("THREADS_USER_ID", "user-12345")

    status = ThreadsConnector({"credentials": {}, "dry_run_default": True}).status()

    assert status["configured"] is True
    assert status["auth_status"] == "configured"


def test_threads_profile_reports_missing_token(monkeypatch) -> None:
    monkeypatch.delenv("THREADS_ACCESS_TOKEN", raising=False)

    result = ThreadsConnector({"credentials": {}, "dry_run_default": True}).profile()

    assert result["ok"] is False
    assert result["status_code"] is None
    assert result["body"]["error"] == "THREADS_ACCESS_TOKEN is missing"
