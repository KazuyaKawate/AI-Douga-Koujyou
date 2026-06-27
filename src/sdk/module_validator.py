"""module_validator — Validate MODULE_INFO manifests for Creator Factory OS SDK v5.1."""
from __future__ import annotations
from src.sdk.module_manifest import REQUIRED_FIELDS, MODULE_TYPES, MODULE_STATUSES


def validate_manifest(manifest: dict) -> tuple[bool, list[str]]:
    """Return (is_valid, list_of_errors). Empty error list means valid."""
    errors: list[str] = []

    # Required fields
    for field in REQUIRED_FIELDS:
        if field not in manifest or not manifest[field]:
            errors.append(f"Missing required field: '{field}'")

    # module_type enum
    mt = manifest.get("module_type", "")
    if mt and mt not in MODULE_TYPES:
        errors.append(f"Invalid module_type '{mt}'. Must be one of: {MODULE_TYPES}")

    # status enum
    status = manifest.get("status", "")
    if status and status not in MODULE_STATUSES:
        errors.append(f"Invalid status '{status}'. Must be one of: {MODULE_STATUSES}")

    # Boolean fields
    for bool_field in ("dashboard_widget", "mission_control_widget", "project_support"):
        val = manifest.get(bool_field)
        if val is not None and not isinstance(val, bool):
            errors.append(f"Field '{bool_field}' must be bool, got {type(val).__name__}")

    # List fields
    for list_field in ("dependencies", "config_files", "tags"):
        val = manifest.get(list_field)
        if val is not None and not isinstance(val, list):
            errors.append(f"Field '{list_field}' must be a list, got {type(val).__name__}")

    # String fields that must be str if present
    for str_field in ("version", "sdk_version", "minimum_os_version", "module_id"):
        val = manifest.get(str_field)
        if val is not None and not isinstance(val, str):
            errors.append(f"Field '{str_field}' must be a string, got {type(val).__name__}")

    # module_id format (simple check: non-empty, no spaces)
    mid = manifest.get("module_id", "")
    if mid and " " in mid:
        errors.append(f"Field 'module_id' must not contain spaces: '{mid}'")

    return (len(errors) == 0), errors


def validate_all(manifests: list[dict]) -> dict:
    """Validate a list of manifests. Returns summary dict with per-module results."""
    results = []
    ok_count = 0
    for m in manifests:
        is_valid, errors = validate_manifest(m)
        results.append({
            "module_name": m.get("module_name", "?"),
            "module_id":   m.get("module_id", ""),
            "module_type": m.get("module_type", ""),
            "version":     m.get("version", ""),
            "status":      m.get("status", ""),
            "valid":       is_valid,
            "errors":      errors,
        })
        if is_valid:
            ok_count += 1
    return {
        "total":   len(manifests),
        "valid":   ok_count,
        "invalid": len(manifests) - ok_count,
        "results": results,
    }
