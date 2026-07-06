from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any


class JsonStoreError(RuntimeError):
    """Raised when JSON persistence cannot complete safely."""


def load_json(path: str | Path, default: Any = None) -> Any:
    """Load JSON from path, returning default when the file is missing."""
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json_atomic(
    path: str | Path,
    data: Any,
    *,
    ensure_ascii: bool = False,
    indent: int | None = 2,
    retries: int = 10,
    retry_delay: float = 0.05,
) -> Path:
    """Atomically persist JSON with a small cross-process lock.

    The write goes to a sibling temp file first, then os.replace() swaps it into
    place only after the JSON has been fully serialized and flushed.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lock_path = p.with_name(f"{p.name}.lock")
    tmp_path = p.with_name(f".{p.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")

    lock_fd: int | None = None
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(lock_fd, str(os.getpid()).encode("ascii", errors="ignore"))
            break
        except FileExistsError as exc:
            last_error = exc
            time.sleep(retry_delay * (attempt + 1))
    else:
        raise JsonStoreError(f"Could not acquire JSON write lock: {lock_path}") from last_error

    try:
        text = json.dumps(data, ensure_ascii=ensure_ascii, indent=indent)
        tmp_path.write_text(text, encoding="utf-8")
        for attempt in range(retries):
            try:
                os.replace(str(tmp_path), str(p))
                break
            except PermissionError as exc:
                last_error = exc
                time.sleep(retry_delay * (attempt + 1))
        else:
            raise JsonStoreError(f"Could not replace JSON file: {p}") from last_error
        return p
    finally:
        if lock_fd is not None:
            try:
                os.close(lock_fd)
            except OSError:
                pass
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
