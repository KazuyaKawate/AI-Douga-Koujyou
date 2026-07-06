from __future__ import annotations

import pytest

from src.business_engine.adapters import AdapterRegistry
from src.business_engine.manager import BusinessEngineStore
from src.business_engine.scheduler_daemon import SchedulerDaemon


def test_phase4_adapters_are_disabled_by_default(tmp_path):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    registry = store.adapter_registry()

    assert registry.active_adapter() == "None"
    assert registry.api_status() == "disabled"
    assert len(registry.by_category("publishing")) == 7
    assert len(registry.by_category("affiliate")) == 5
    assert len(registry.by_category("seo")) == 3
    assert all(adapter.enabled is False for adapter in registry.all())
    registry.assert_disabled("note")


def test_phase4_adapter_execution_guard_blocks_enabled_adapter():
    registry = AdapterRegistry({"publishing": {"note": {"enabled": True, "configured": True}}})

    with pytest.raises(RuntimeError):
        registry.assert_disabled("note")


def test_scheduler_daemon_disabled_by_default_and_start_stop(tmp_path):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    scheduler = SchedulerDaemon(store)

    state = scheduler.state()
    assert state["enabled"] is False
    assert state["status"] == "stopped"

    started = scheduler.start()
    assert started["enabled"] is True
    assert started["status"] == "running"
    assert started["heartbeat_at"]

    configured = scheduler.configure(120)
    assert configured["interval_seconds"] == 120

    stopped = scheduler.stop()
    assert stopped["enabled"] is False
    assert stopped["status"] == "stopped"


def test_scheduler_tick_runs_only_when_enabled(tmp_path):
    store = BusinessEngineStore(tmp_path / "business_engine.json")
    scheduler = SchedulerDaemon(store)

    disabled_tick = scheduler.tick(force=True)
    assert disabled_tick["last_result"] == "Scheduler disabled; no job executed."

    scheduler.start()
    enabled_tick = scheduler.tick(force=True)
    assert enabled_tick["status"] == "running"
    assert enabled_tick["last_tick_at"]
    assert store.execution_monitor()["completed"] >= 1
