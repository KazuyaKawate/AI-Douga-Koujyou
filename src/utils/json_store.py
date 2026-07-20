from __future__ import annotations

import json
import os
import tempfile
import time
import uuid
import warnings
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


def _write_error_log(action: str, path: Path, error: BaseException, tmp_path: Path | None = None) -> None:
    """Write a best-effort diagnostic log when Windows file locks block saving."""
    try:
        root = Path(__file__).resolve().parents[2]
        log_dir = root / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "json_store_errors.log"
        message = (
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {action}\n"
            f"path={path}\n"
            f"tmp_path={tmp_path or ''}\n"
            f"error_type={type(error).__name__}\n"
            f"error={error}\n\n"
        )
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(message)
    except Exception:
        pass


def save_json_atomic(
    path: str | Path,
    data: Any,
    *,
    ensure_ascii: bool = False,
    indent: int | None = 2,
    retries: int = 5,
    retry_delay: float = 0.3,
) -> Path:
    """Atomically persist JSON with a small cross-process lock.

    The write goes to a sibling temp file first, then os.replace() swaps it into
    place only after the JSON has been fully serialized and flushed.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lock_path = p.with_name(f"{p.name}.lock")
    tmp_path: Path | None = None

    lock_fd: int | None = None
    last_error: Exception | None = None
    retry_count = max(1, min(int(retries), 5))
    for attempt in range(retry_count):
        try:
            lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(lock_fd, str(os.getpid()).encode("ascii", errors="ignore"))
            break
        except FileExistsError as exc:
            last_error = exc
            if attempt + 1 < retry_count:
                time.sleep(retry_delay * (2**attempt))
    else:
        error = JsonStoreError(f"Could not acquire JSON write lock: {lock_path}")
        _write_error_log("lock_failed", p, last_error or error)
        warnings.warn(
            f"JSON file is locked; previous data was preserved: {p}",
            RuntimeWarning,
            stacklevel=2,
        )
        return p

    try:
        text = json.dumps(data, ensure_ascii=ensure_ascii, indent=indent)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(p.parent),
            prefix=f".{p.name}.{os.getpid()}.{uuid.uuid4().hex}.",
            suffix=".tmp",
            delete=False,
        ) as tmp_file:
            tmp_file.write(text)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            tmp_path = Path(tmp_file.name)

        for attempt in range(retry_count):
            try:
                os.replace(str(tmp_path), str(p))
                tmp_path = None
                break
            except PermissionError as exc:
                last_error = exc
                if attempt + 1 < retry_count:
                    time.sleep(retry_delay * (2**attempt))
        else:
            error = JsonStoreError(f"Could not replace JSON file: {p}")
            _write_error_log("replace_failed", p, last_error or error, tmp_path)
            warnings.warn(
                f"JSON file is locked; previous data was preserved: {p}",
                RuntimeWarning,
                stacklevel=2,
            )
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
        if tmp_path is not None:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
