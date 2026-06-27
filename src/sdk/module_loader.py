"""module_loader — Discover and load module manifests for Creator Factory OS SDK.

Discovery strategy:
1. Returns built-in manifests defined in module_manifest.py.
2. Attempts to import MODULE_MANIFEST from each known src sub-package __init__.py.
   If not found, skips silently (backward compatible).
3. Validates each discovered manifest before adding to results.
"""
from __future__ import annotations
from src.sdk.module_manifest import BUILTIN_MANIFESTS, make_manifest
from src.sdk.module_validator import validate_manifest

_DISCOVERY_PATHS = [
    ("src.factories.note",       "note投稿工場"),
    ("src.factories.sns",        "SNS投稿工場"),
    ("src.factories.sales",      "営業工場"),
    ("src.factories.accounting", "会計監査工場"),
    ("src.factories.analytics",  "アナリティクス工場"),
    ("src.factories.automation", "自動化工場"),
    ("src.devtools",             "承認アシスタント"),
    ("src.devstudio",            "Development Studio"),
    ("src.aiceo",                "AI CEO Core"),
    ("src.approval",             "Approval Center"),
]


def _try_import_manifest(module_path: str) -> dict | None:
    """Try to import MODULE_MANIFEST from a module's __init__.py. Returns None on failure."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        return getattr(mod, "MODULE_MANIFEST", None)
    except Exception:
        return None


def load_all_manifests(include_invalid: bool = False) -> list[dict]:
    """Return all valid manifests. Built-ins take priority over discovered ones."""
    seen: set[str] = set()
    result: list[dict] = []

    for m in BUILTIN_MANIFESTS:
        is_valid, _ = validate_manifest(m)
        if is_valid or include_invalid:
            name = m.get("module_name", "")
            if name not in seen:
                seen.add(name)
                result.append(m)

    for module_path, fallback_name in _DISCOVERY_PATHS:
        if fallback_name in seen:
            continue
        discovered = _try_import_manifest(module_path)
        if discovered and isinstance(discovered, dict):
            is_valid, _ = validate_manifest(discovered)
            if is_valid or include_invalid:
                name = discovered.get("module_name", fallback_name)
                if name not in seen:
                    seen.add(name)
                    result.append(discovered)

    return result


def get_manifests_by_type(module_type: str) -> list[dict]:
    return [m for m in load_all_manifests() if m.get("module_type") == module_type]


def get_manifest(module_name: str) -> dict | None:
    return next((m for m in load_all_manifests() if m.get("module_name") == module_name), None)
