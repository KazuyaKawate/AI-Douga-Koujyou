from __future__ import annotations

from pathlib import Path

from src.rc.rc_manager import RCReadinessManager


def test_rc_readiness_collects_local_first_report(tmp_path: Path) -> None:
    manager = RCReadinessManager(tmp_path / "reports")

    report = manager.collect()

    assert report["local_first"] is True
    assert report["safety"]["router_default_virtual"] is True
    assert report["safety"]["external_apis_disabled"] is True
    assert report["safety"]["workspace_disabled"] is True
    assert report["safety"]["google_auth_disabled"] is True
    assert "automation_engine" in report["modules"]
    assert "production_pipeline" in report["modules"]


def test_rc_manifest_writes_locally(tmp_path: Path) -> None:
    manager = RCReadinessManager(tmp_path / "reports")

    path = manager.write_manifest()

    assert path.exists()
    assert path.name == "aios_v5_2_rc_readiness.json"
    assert str(path).startswith(str(tmp_path))
