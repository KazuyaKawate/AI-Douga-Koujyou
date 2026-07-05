from __future__ import annotations

from pathlib import Path
from typing import Iterable


class UnsafePathError(ValueError):
    """Raised when user-supplied paths escape the allowed workspace scope."""


def safe_resolve_path(
    root: str | Path,
    user_path: str | Path,
    *,
    allowed_subdirs: Iterable[str | Path] | None = None,
) -> Path:
    """Resolve a user path safely inside root.

    Rules:
    - absolute user paths are rejected
    - ".." traversal is rejected before resolution
    - the final resolved path must remain inside root
    - optional allowed_subdirs restrict the result to selected root-relative folders
    """
    root_path = Path(root).resolve(strict=False)
    path = Path(user_path)

    if path.is_absolute():
        raise UnsafePathError(f"Absolute paths are not allowed: {user_path}")

    if any(part == ".." for part in path.parts):
        raise UnsafePathError(f"Directory traversal is not allowed: {user_path}")

    resolved = (root_path / path).resolve(strict=False)
    try:
        resolved.relative_to(root_path)
    except ValueError as exc:
        raise UnsafePathError(f"Path escapes workspace root: {user_path}") from exc

    if allowed_subdirs:
        allowed_roots = [
            safe_resolve_path(root_path, subdir)
            for subdir in allowed_subdirs
        ]
        for allowed_root in allowed_roots:
            try:
                resolved.relative_to(allowed_root)
                break
            except ValueError:
                continue
        else:
            allowed = ", ".join(str(p) for p in allowed_subdirs)
            raise UnsafePathError(f"Path is outside allowed directories ({allowed}): {user_path}")

    return resolved


def workspace_relative_path(root: str | Path, path: str | Path) -> Path:
    """Return a workspace-relative path for an already trusted internal path."""
    root_path = Path(root).resolve(strict=False)
    resolved = Path(path).resolve(strict=False)
    try:
        return resolved.relative_to(root_path)
    except ValueError as exc:
        raise UnsafePathError(f"Path escapes workspace root: {path}") from exc
