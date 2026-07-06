from __future__ import annotations

import json
import os

from src.utils.json_store import save_json_atomic


def test_save_json_atomic_retries_permission_error_on_replace(tmp_path, monkeypatch):
    target = tmp_path / "store.json"
    calls = {"count": 0}
    real_replace = os.replace

    def flaky_replace(src, dst):
        calls["count"] += 1
        if calls["count"] == 1:
            raise PermissionError("temporary lock")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "replace", flaky_replace)

    save_json_atomic(target, {"ok": True}, retries=3, retry_delay=0)

    assert calls["count"] == 2
    assert json.loads(target.read_text(encoding="utf-8")) == {"ok": True}
