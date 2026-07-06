from __future__ import annotations

import hashlib
import json
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from src.approval.approval_queue import get_content_reviews, load_queue
from src.utils.json_store import load_json, save_json_atomic

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = ROOT / "config" / "export_manager.json"
DEFAULT_OUTPUT_ROOT = ROOT / "output"

CONTENT_FOLDERS = {
    "note_article": "note",
    "sns_post": "sns",
    "seo_article": "seo",
    "affiliate_description": "affiliate",
    "business_report": "reports",
}


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _default_state() -> dict[str, Any]:
    return {
        "meta": {
            "version": "5.2-phase8",
            "created_at": _now(),
            "local_first": True,
            "external_publish_enabled": False,
        },
        "queue": [],
        "history": [],
        "logs": [],
        "packages": [],
    }


class ExportManager:
    """Local-only export manager for publish-ready approval content."""

    def __init__(
        self,
        state_path: str | Path = DEFAULT_STATE_PATH,
        output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    ) -> None:
        self.state_path = Path(state_path)
        self.output_root = Path(output_root)

    def load(self) -> dict[str, Any]:
        data = load_json(self.state_path, default=None)
        if not isinstance(data, dict):
            data = _default_state()
            self.save(data)
        defaults = _default_state()
        for key, value in defaults.items():
            data.setdefault(key, value)
        data.setdefault("meta", {})
        data["meta"].setdefault("local_first", True)
        data["meta"].setdefault("external_publish_enabled", False)
        return data

    def save(self, data: dict[str, Any]) -> Path:
        data.setdefault("meta", {})
        data["meta"]["updated_at"] = _now()
        return save_json_atomic(self.state_path, data)

    def publish_ready_items(self) -> list[dict[str, Any]]:
        return get_content_reviews("publish_ready")

    def queue_export(self, content_id: str, export_type: str = "local_export") -> dict[str, Any]:
        item = self._get_publish_ready_item(content_id)
        if item is None:
            raise ValueError("Only publish_ready Approval Center content can be queued for export.")
        data = self.load()
        existing = next(
            (
                row for row in data.get("queue", [])
                if row.get("content_id") == content_id and row.get("export_status") in ("queued", "failed")
            ),
            None,
        )
        if existing:
            return existing
        record = {
            "export_id": _new_id("exp"),
            "approval_id": item.get("id", ""),
            "content_id": item.get("id", ""),
            "title": item.get("title", ""),
            "content_type": item.get("content_type", ""),
            "export_path": "",
            "export_type": export_type,
            "exported_at": "",
            "checksum": "",
            "file_size": 0,
            "export_status": "queued",
            "attempts": 0,
            "last_error": "",
            "created_at": _now(),
            "updated_at": _now(),
        }
        data.setdefault("queue", []).insert(0, record)
        self._log(data, record["export_id"], "queued", f"Queued export for {item.get('title', '')}")
        self.save(data)
        return record

    def queue_all_publish_ready(self) -> list[dict[str, Any]]:
        return [self.queue_export(item["id"]) for item in self.publish_ready_items()]

    def export_one(self, export_id: str) -> dict[str, Any] | None:
        data = self.load()
        record = self._find_record(data, export_id)
        if record is None:
            return None
        record["attempts"] = int(record.get("attempts", 0)) + 1
        record["updated_at"] = _now()
        try:
            item = self._get_publish_ready_item(record.get("content_id", ""))
            if item is None:
                raise ValueError("Approval content is no longer publish_ready.")
            exported = self._write_export_files(item, record)
            record.update(exported)
            record["export_status"] = "completed"
            record["last_error"] = ""
            record["exported_at"] = _now()
            self._move_completed_to_history(data, record)
            self._log(data, record["export_id"], "completed", f"Exported to {record['export_path']}")
        except Exception as exc:
            record["export_status"] = "failed"
            record["last_error"] = str(exc)
            record["updated_at"] = _now()
            self._log(data, record["export_id"], "failed", str(exc))
        self.save(data)
        return record

    def export_batch(self, limit: int | None = None) -> list[dict[str, Any]]:
        data = self.load()
        queued = [
            row["export_id"] for row in data.get("queue", [])
            if row.get("export_status") in ("queued", "failed")
        ]
        if limit is not None:
            queued = queued[: max(int(limit), 0)]
        return [result for export_id in queued if (result := self.export_one(export_id)) is not None]

    def retry_export(self, export_id: str) -> dict[str, Any] | None:
        data = self.load()
        record = self._find_record(data, export_id)
        if record is None:
            return None
        record["export_status"] = "queued"
        record["updated_at"] = _now()
        self._log(data, export_id, "retry_queued", "Queued retry.")
        self.save(data)
        return self.export_one(export_id)

    def delete_export_record(self, export_id: str) -> bool:
        data = self.load()
        before_q = len(data.get("queue", []))
        before_h = len(data.get("history", []))
        data["queue"] = [row for row in data.get("queue", []) if row.get("export_id") != export_id]
        data["history"] = [row for row in data.get("history", []) if row.get("export_id") != export_id]
        changed = len(data["queue"]) != before_q or len(data["history"]) != before_h
        if changed:
            self._log(data, export_id, "deleted", "Deleted export record.")
            self.save(data)
        return changed

    def clear_completed_exports(self) -> int:
        data = self.load()
        completed = [row for row in data.get("history", []) if row.get("export_status") == "completed"]
        count = len(completed)
        data["history"] = [row for row in data.get("history", []) if row.get("export_status") != "completed"]
        if count:
            self._log(data, "bulk", "cleared_completed", f"Cleared {count} completed export records.")
            self.save(data)
        return count

    def build_package(self, content_ids: list[str] | None = None) -> dict[str, Any]:
        items = self.publish_ready_items()
        if content_ids:
            allowed = set(content_ids)
            items = [item for item in items if item.get("id") in allowed]
        if not items:
            raise ValueError("No publish_ready content available for package.")

        package_id = _new_id("pkg")
        package_dir = self.output_root / "packages" / package_id
        package_dir.mkdir(parents=True, exist_ok=True)

        manifest_items = []
        for item in items:
            folder = CONTENT_FOLDERS.get(item.get("content_type", ""), "reports")
            item_dir = package_dir / folder
            item_dir.mkdir(parents=True, exist_ok=True)
            base = _safe_filename(f"{item.get('content_type')}_{item.get('id')}")
            md_path = item_dir / f"{base}.md"
            json_path = item_dir / f"{base}.json"
            md_path.write_text(_markdown_for_item(item), encoding="utf-8")
            save_json_atomic(json_path, item)
            manifest_items.append(_manifest_item(item, md_path))

        metadata = {
            "package_id": package_id,
            "created_at": _now(),
            "item_count": len(items),
            "local_only": True,
            "external_publish_enabled": False,
        }
        manifest = {
            "package_id": package_id,
            "created_at": metadata["created_at"],
            "items": manifest_items,
        }
        metadata_path = package_dir / "metadata.json"
        manifest_path = package_dir / "manifest.json"
        save_json_atomic(metadata_path, metadata)
        save_json_atomic(manifest_path, manifest)

        zip_path = self.output_root / "packages" / f"{package_id}.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in package_dir.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(package_dir))

        package_record = {
            "package_id": package_id,
            "zip_path": str(zip_path),
            "metadata_path": str(metadata_path),
            "manifest_path": str(manifest_path),
            "item_count": len(items),
            "file_size": zip_path.stat().st_size,
            "checksum": checksum_file(zip_path),
            "created_at": metadata["created_at"],
        }
        data = self.load()
        data.setdefault("packages", []).insert(0, package_record)
        self._log(data, package_id, "package_created", f"Created package {zip_path}")
        self.save(data)
        return package_record

    def summary(self) -> dict[str, Any]:
        data = self.load()
        queue = data.get("queue", [])
        history = data.get("history", [])
        failed = [row for row in queue if row.get("export_status") == "failed"]
        completed = [row for row in history if row.get("export_status") == "completed"]
        latest = (history + queue)[0] if (history + queue) else {}
        total_size = sum(int(row.get("file_size", 0)) for row in completed)
        return {
            "pending_exports": sum(1 for row in queue if row.get("export_status") == "queued"),
            "completed_exports": len(completed),
            "failed_exports": len(failed),
            "latest_export": latest.get("title", "None"),
            "total_exported": len(completed),
            "export_size": total_size,
            "total_local_packages": len(data.get("packages", [])),
            "queue": queue,
            "history": history,
            "logs": data.get("logs", []),
            "packages": data.get("packages", []),
        }

    def _get_publish_ready_item(self, content_id: str) -> dict[str, Any] | None:
        return next((item for item in get_content_reviews("publish_ready") if item.get("id") == content_id), None)

    def _find_record(self, data: dict[str, Any], export_id: str) -> dict[str, Any] | None:
        for section in ("queue", "history"):
            found = next((row for row in data.get(section, []) if row.get("export_id") == export_id), None)
            if found:
                return found
        return None

    def _write_export_files(self, item: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
        folder = CONTENT_FOLDERS.get(item.get("content_type", ""), "reports")
        out_dir = self.output_root / "export" / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        base = _safe_filename(f"{item.get('content_type')}_{item.get('id')}_{record.get('export_id')}")
        md_path = out_dir / f"{base}.md"
        json_path = out_dir / f"{base}.json"
        txt_path = out_dir / f"{base}.txt"
        html_path = out_dir / f"{base}.html"

        md_path.write_text(_markdown_for_item(item), encoding="utf-8")
        save_json_atomic(json_path, _export_payload(item, record, md_path))
        txt_path.write_text(item.get("content", ""), encoding="utf-8")
        html_path.write_text(_html_for_item(item), encoding="utf-8")
        files = {
            "md": _file_metadata(md_path),
            "json": _file_metadata(json_path),
            "txt": _file_metadata(txt_path),
            "html": _file_metadata(html_path),
        }
        return {
            "export_path": str(md_path),
            "checksum": checksum_file(md_path),
            "file_size": sum(file_info["file_size"] for file_info in files.values()),
            "files": files,
        }

    def _move_completed_to_history(self, data: dict[str, Any], record: dict[str, Any]) -> None:
        data["queue"] = [row for row in data.get("queue", []) if row.get("export_id") != record.get("export_id")]
        data.setdefault("history", []).insert(0, dict(record))
        data["history"] = data["history"][:500]

    def _log(self, data: dict[str, Any], export_id: str, status: str, message: str) -> None:
        data.setdefault("logs", []).insert(0, {
            "log_id": _new_id("log"),
            "export_id": export_id,
            "status": status,
            "message": message,
            "created_at": _now(),
        })
        data["logs"] = data["logs"][:500]


def export_summary() -> dict[str, Any]:
    return ExportManager().summary()


def checksum_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_metadata(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "checksum": checksum_file(path),
        "file_size": path.stat().st_size,
    }


def _export_payload(item: dict[str, Any], record: dict[str, Any], md_path: Path) -> dict[str, Any]:
    return {
        "export_id": record.get("export_id", ""),
        "approval_id": item.get("id", ""),
        "content_id": item.get("id", ""),
        "export_path": str(md_path),
        "export_type": record.get("export_type", "local_export"),
        "exported_at": _now(),
        "checksum": checksum_file(md_path),
        "file_size": md_path.stat().st_size,
        "export_status": "completed",
        "title": item.get("title", ""),
        "content_type": item.get("content_type", ""),
        "approval_date": item.get("approved_at", ""),
        "reviewer_notes": item.get("reviewer_notes", ""),
        "risk_summary": _risk_summary(item),
    }


def _manifest_item(item: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "title": item.get("title", ""),
        "id": item.get("id", ""),
        "created_at": item.get("generated_at", ""),
        "content_type": item.get("content_type", ""),
        "approval_date": item.get("approved_at", ""),
        "reviewer_notes": item.get("reviewer_notes", ""),
        "risk_summary": _risk_summary(item),
        "export_time": _now(),
        "path": str(path),
        "checksum": checksum_file(path),
        "file_size": path.stat().st_size,
    }


def _risk_summary(item: dict[str, Any]) -> dict[str, Any]:
    flags = item.get("risk_flags", [])
    return {
        "count": len(flags),
        "critical": sum(1 for flag in flags if flag.get("severity") == "critical"),
        "warnings": [flag.get("label", "") for flag in flags],
    }


def _markdown_for_item(item: dict[str, Any]) -> str:
    flags = item.get("risk_flags", [])
    risk_text = "\n".join(f"- {flag.get('severity')}: {flag.get('label')}" for flag in flags) or "- none"
    return (
        f"# {item.get('title', '')}\n\n"
        f"- Content ID: {item.get('id', '')}\n"
        f"- Type: {item.get('content_type', '')}\n"
        f"- Status: {item.get('status', '')}\n"
        f"- Approved At: {item.get('approved_at', '')}\n"
        f"- Reviewer Notes: {item.get('reviewer_notes', '')}\n\n"
        "## Risk Summary\n\n"
        f"{risk_text}\n\n"
        "## Content\n\n"
        f"{item.get('content', '')}\n"
    )


def _html_for_item(item: dict[str, Any]) -> str:
    content = (
        item.get("content", "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    title = item.get("title", "Untitled")
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title></head><body><h1>{title}</h1><pre>{content}</pre></body></html>"


def _safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value).strip("_") or "export"
