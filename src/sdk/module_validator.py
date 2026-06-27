"""module_validator — Validate MODULE_INFO manifests for Creator Factory OS SDK."""
from __future__ import annotations
from src.sdk.module_manifest import REQUIRED_FIELDS, MODULE_TYPES, _DEFAULTS


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

    # version string
    version = manifest.get("version", "")
    if version and not isinstance(version, str):
        errors.append(f"Field 'version' must be a string")

    return (len(errors) == 0), errors


def validate_all(manifests: list[dict]) -> dict:
    """Validate a list of manifests. Returns summary dict."""
    results = []
    ok_count = 0
    for m in manifests:
        is_valid, errors = validate_manifest(m)
        results.append({
            "module_name": m.get("module_name", "?"),
            "valid": is_valid,
            "errors": errors,
        })
        if is_valid:
            ok_count += 1
    return {
        "total": len(manifests),
        "valid": ok_count,
        "invalid": len(manifests) - ok_count,
        "results": results,
    }
