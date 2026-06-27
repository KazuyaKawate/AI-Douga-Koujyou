"""module_loader — Discover and load module manifests for Creator Factory OS SDK v5.1.

Discovery strategy (in priority order):
1. Built-in manifests from module_manifest.BUILTIN_MANIFESTS.
2. Dynamic scan: for each known package path, try to import and look for
   MODULE_INFO or MODULE_MANIFEST in the package __init__.py.
   MODULE_INFO takes priority over MODULE_MANIFEST (new canonical name).
3. Falls back silently when a package is missing or broken.
4. Never imports unsafe external packages.
5. Returns validation errors, not crashes.
"""
from __future__ import annotations
import importlib
from src.sdk.module_manifest import BUILTIN_MANIFESTS
from src.sdk.module_validator import validate_manifest

# Known package paths to scan for self-registered manifests.
# Tuple: (dotted_import_path, fallback_display_name)
_DISCOVERY_PATHS: list[tuple[str, str]] = [
    ("src.factories.note",           "note投稿工場"),
    ("src.factories.sns",            "SNS投稿工場"),
    ("src.factories.sales",          "営業工場"),
    ("src.factories.accounting",     "会計監査工場"),
    ("src.factories.analytics",      "アナリティクス工場"),
    ("src.factories.automation",     "自動化工場"),
    ("src.devtools",                 "承認アシスタント"),
    ("src.devstudio",                "Development Studio"),
    ("src.aiceo",                    "AI CEO Core"),
    ("src.approval",                 "Approval Center"),
    ("src.sdk",                      "Module SDK"),
]

# Additional factory sub-packages to probe even if not in _DISCOVERY_PATHS
_FACTORY_ROOT = "src.factories"


def _try_import_manifest(dotted_path: str) -> dict | None:
    """Import a package and return MODULE_INFO or MODULE_MANIFEST if present.

    MODULE_INFO takes priority (new canonical name for v5.1+).
    Falls back to MODULE_MANIFEST for backward compatibility.
    Returns None on any import or attribute error — never raises.
    """
    try:
        mod = importlib.import_module(dotted_path)
        manifest = getattr(mod, "MODULE_INFO", None)
        if manifest is None:
            manifest = getattr(mod, "MODULE_MANIFEST", None)
        return manifest if isinstance(manifest, dict) else None
    except Exception:
        return None


def load_all_manifests(include_invalid: bool = False) -> list[dict]:
    """Return all valid manifests.

    Built-in manifests take priority over self-registered ones (same module_name wins).
    Set include_invalid=True to include manifests with validation errors (for debugging).
    """
    seen_names: set[str] = set()
    result: list[dict] = []

    # 1. Built-ins first
    for m in BUILTIN_MANIFESTS:
        is_valid, _ = validate_manifest(m)
        if is_valid or include_invalid:
            name = m.get("module_name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                result.append(m)

    # 2. Dynamic discovery (skips names already covered by built-ins)
    for dotted_path, fallback_name in _DISCOVERY_PATHS:
        if fallback_name in seen_names:
            continue
        discovered = _try_import_manifest(dotted_path)
        if discovered:
            is_valid, _ = validate_manifest(discovered)
            if is_valid or include_invalid:
                name = discovered.get("module_name", fallback_name)
                if name not in seen_names:
                    seen_names.add(name)
                    result.append(discovered)

    return result


def load_all_with_errors() -> list[tuple[dict, list[str]]]:
    """Return all manifests (valid and invalid) paired with their error lists.

    Useful for diagnostics/SDK tab display.
    """
    pairs: list[tuple[dict, list[str]]] = []
    seen_names: set[str] = set()

    for m in BUILTIN_MANIFESTS:
        _, errors = validate_manifest(m)
        name = m.get("module_name", "")
        if name and name not in seen_names:
            seen_names.add(name)
            pairs.append((m, errors))

    for dotted_path, fallback_name in _DISCOVERY_PATHS:
        if fallback_name in seen_names:
            continue
        discovered = _try_import_manifest(dotted_path)
        if discovered:
            _, errors = validate_manifest(discovered)
            name = discovered.get("module_name", fallback_name)
            if name not in seen_names:
                seen_names.add(name)
                pairs.append((discovered, errors))

    return pairs


def get_manifests_by_type(module_type: str) -> list[dict]:
    return [m for m in load_all_manifests() if m.get("module_type") == module_type]


def get_manifest(module_name: str) -> dict | None:
    return next(
        (m for m in load_all_manifests() if m.get("module_name") == module_name),
        None,
    )


def get_manifest_by_id(module_id: str) -> dict | None:
    return next(
        (m for m in load_all_manifests() if m.get("module_id") == module_id),
        None,
    )
