"""sheet_diff — Diff engine comparing local JSON records vs Google Sheet rows (v5.2 Phase 2).

Returns added, updated, removed, conflicts, unchanged.
Pure logic — no I/O, no API calls. Operates on plain dicts passed in.
"""
from __future__ import annotations


def diff_records(
    local_rows: list[dict],
    sheet_rows: list[dict],
    key_field: str = "id",
) -> dict:
    """Compare local JSON records against sheet records.

    Returns:
      added     — rows in local but not in sheet
      updated   — rows in both, one or more fields differ
      removed   — rows in sheet but not in local
      conflicts — rows in both where >= 2 fields differ (potential data conflict)
      unchanged — rows identical in both
    """
    local_idx = _index_by(local_rows, key_field)
    sheet_idx = _index_by(sheet_rows, key_field)
    all_keys  = set(local_idx) | set(sheet_idx)

    added:     list[dict] = []
    updated:   list[dict] = []
    removed:   list[dict] = []
    conflicts: list[dict] = []
    unchanged: list[dict] = []

    for key in sorted(all_keys):
        in_local = key in local_idx
        in_sheet = key in sheet_idx

        if in_local and not in_sheet:
            added.append({"key": key, "local": local_idx[key], "sheet": None})
        elif in_sheet and not in_local:
            removed.append({"key": key, "local": None, "sheet": sheet_idx[key]})
        else:
            diffs = _field_diff(local_idx[key], sheet_idx[key])
            if not diffs:
                unchanged.append({"key": key, "row": local_idx[key]})
            elif len(diffs) >= 2:
                conflicts.append({
                    "key":         key,
                    "local":       local_idx[key],
                    "sheet":       sheet_idx[key],
                    "diff_fields": diffs,
                    "diff_count":  len(diffs),
                })
            else:
                updated.append({
                    "key":         key,
                    "local":       local_idx[key],
                    "sheet":       sheet_idx[key],
                    "diff_fields": diffs,
                })

    return {
        "added":     added,
        "updated":   updated,
        "removed":   removed,
        "conflicts": conflicts,
        "unchanged": unchanged,
        "summary": {
            "added":       len(added),
            "updated":     len(updated),
            "removed":     len(removed),
            "conflicts":   len(conflicts),
            "unchanged":   len(unchanged),
            "total_local": len(local_rows),
            "total_sheet": len(sheet_rows),
        },
    }


def _index_by(rows: list[dict], key_field: str) -> dict[str, dict]:
    """Index rows by key_field. Rows without the key get a positional fallback key."""
    result: dict[str, dict] = {}
    for i, row in enumerate(rows):
        key = str(row.get(key_field, f"__row_{i}"))
        result[key] = row
    return result


def _field_diff(local: dict, sheet: dict) -> list[str]:
    """Return list of field names that differ between local and sheet row."""
    all_fields = set(local.keys()) | set(sheet.keys())
    return [
        f for f in sorted(all_fields)
        if str(local.get(f, "")).strip() != str(sheet.get(f, "")).strip()
    ]


def summarize_diff(diff: dict) -> str:
    """Return a human-readable one-line summary of the diff result."""
    s = diff["summary"]
    return (
        f"追加: {s['added']}件 / 更新: {s['updated']}件 / "
        f"削除: {s['removed']}件 / 競合: {s['conflicts']}件 / "
        f"変更なし: {s['unchanged']}件"
    )
