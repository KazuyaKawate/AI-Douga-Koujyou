"""spreadsheet_exporter — CSV export for Development Studio ledger."""
from __future__ import annotations
import csv
import io
from datetime import datetime
from pathlib import Path

ROOT        = Path(__file__).parent.parent.parent
EXPORT_DIR  = ROOT / "reports" / "devstudio"


def _ensure_dir() -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    return EXPORT_DIR


def _write_csv(filename: str, fieldnames: list[str], rows: list[dict]) -> Path:
    out_dir = _ensure_dir()
    path = out_dir / filename
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    return path


def export_roadmap(items: list[dict]) -> Path:
    fields = ["roadmap_id", "version", "title", "type", "priority",
              "status", "planned_date", "completed_date", "notes"]
    return _write_csv("roadmap.csv", fields, items)


def export_releases(releases: list[dict]) -> Path:
    fields = ["release_id", "version", "title", "date",
              "commit_id", "health_status", "summary", "notes"]
    return _write_csv("releases.csv", fields, releases)


def export_decisions(decisions: list[dict]) -> Path:
    fields = ["decision_id", "date", "version", "theme", "decision",
              "reason", "expected_effect", "impact", "status"]
    return _write_csv("decisions.csv", fields, decisions)


def export_meetings(meetings: list[dict]) -> Path:
    fields = ["meeting_id", "date", "title", "agenda",
              "notes", "decisions", "next_actions"]
    return _write_csv("meetings.csv", fields, meetings)


def export_all(
    roadmap_items: list[dict],
    releases: list[dict],
    decisions: list[dict],
    meetings: list[dict],
) -> dict[str, Path]:
    return {
        "roadmap":   export_roadmap(roadmap_items),
        "releases":  export_releases(releases),
        "decisions": export_decisions(decisions),
        "meetings":  export_meetings(meetings),
    }


def get_export_history() -> list[dict]:
    _ensure_dir()
    files = sorted(EXPORT_DIR.glob("*.csv"), key=lambda f: f.stat().st_mtime, reverse=True)
    return [
        {
            "name": f.name,
            "path": str(f),
            "size_kb": round(f.stat().st_size / 1024, 1),
            "modified": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        }
        for f in files
    ]
