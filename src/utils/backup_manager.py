"""Backup, restore, and project-package management for AI動画工場.

Extension points (FUTURE):
  - cloud_upload(zip_path, context) → upload to cloud storage
  - cloud_list(context) → list remote backups
  - license_validate(manifest) → check subscription tier
"""
from __future__ import annotations

import json
import shutil
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from src.utils.config import PROJECT_ROOT

APP_VERSION = "3.1"
BACKUP_DIR  = PROJECT_ROOT / "backups"
MANIFEST_NAME = "MANIFEST.json"

# ── File selection ─────────────────────────────────────────────────────────────

_CONFIG_GLOBS: list[str] = ["*.json"]
_PROJECT_JSON_NAMES: list[str] = [
    "episode.json",
    "director_plan.json",
    "production_state.json",
    "asset_manifest.json",
]
_PROJECT_TEXT_GLOBS: list[str] = [
    "*_image_prompts.txt",
    "*_video_prompts.txt",
    "*_voice_script.txt",
    "*.srt",
]
_PROJECT_EXPORT_NAMES: list[str] = ["export/production_report.json"]
_EXTRA_DOCS: list[str] = ["README.md", "RELEASE_NOTES.md"]


def _iter_backup_files(include_project: bool = True) -> Iterator[tuple[Path, str]]:
    """Yield (abs_path, archive_path) for every file to include."""
    config_dir = PROJECT_ROOT / "config"
    if config_dir.exists():
        for pattern in _CONFIG_GLOBS:
            for f in config_dir.glob(pattern):
                yield f, f.relative_to(PROJECT_ROOT).as_posix()

    if not include_project:
        return

    project_dir = PROJECT_ROOT / "project"
    if not project_dir.exists():
        return
    for ep_dir in sorted(d for d in project_dir.iterdir() if d.is_dir()):
        for name in _PROJECT_JSON_NAMES:
            p = ep_dir / name
            if p.exists():
                yield p, p.relative_to(PROJECT_ROOT).as_posix()
        for glob in _PROJECT_TEXT_GLOBS:
            for p in ep_dir.glob(glob):
                yield p, p.relative_to(PROJECT_ROOT).as_posix()
        for rel in _PROJECT_EXPORT_NAMES:
            p = ep_dir / rel
            if p.exists():
                yield p, p.relative_to(PROJECT_ROOT).as_posix()


def _count_episodes() -> int:
    p = PROJECT_ROOT / "project"
    if not p.exists():
        return 0
    return sum(1 for d in p.iterdir() if d.is_dir() and (d / "episode.json").exists())


# ── Backup list ────────────────────────────────────────────────────────────────

def list_backups() -> list[dict]:
    """Return all backup ZIPs sorted newest first."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for z in sorted(BACKUP_DIR.glob("backup_*.zip"), reverse=True):
        meta = _read_manifest(z)
        results.append({
            "path":          z,
            "name":          z.name,
            "size_mb":       round(z.stat().st_size / (1024 * 1024), 2),
            "created_at":    meta.get("backup_date", ""),
            "label":         meta.get("label", ""),
            "app_version":   meta.get("app_version", ""),
            "episode_count": meta.get("episode_count", 0),
            "file_count":    meta.get("file_count", 0),
            "backup_id":     meta.get("backup_id", ""),
            # FUTURE: cloud_synced, cloud_url
        })
    return results


def list_packages() -> list[dict]:
    """Return all exported package ZIPs sorted newest first."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    for z in sorted(BACKUP_DIR.glob("package_*.zip"), reverse=True):
        meta = _read_manifest(z)
        results.append({
            "path":        z,
            "name":        z.name,
            "size_mb":     round(z.stat().st_size / (1024 * 1024), 2),
            "created_at":  meta.get("export_date", ""),
            "label":       meta.get("label", ""),
            "app_version": meta.get("app_version", ""),
        })
    return results


# ── Create backup ──────────────────────────────────────────────────────────────

def create_backup(label: str = "", include_project: bool = True) -> dict:
    """Create a backup ZIP. Returns metadata dict."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    ts  = now.strftime("%Y%m%d_%H%M%S")
    slug = f"_{label.strip().replace(' ', '_')}" if label.strip() else ""
    zip_path = BACKUP_DIR / f"backup_{ts}{slug}.zip"

    files = list(_iter_backup_files(include_project=include_project))
    manifest = {
        "app_version":   APP_VERSION,
        "backup_date":   now.isoformat(),
        "backup_id":     uuid.uuid4().hex,
        "label":         label.strip(),
        "file_count":    len(files),
        "episode_count": _count_episodes(),
        "include_project": include_project,
        # FUTURE: user_id, cloud_backup_id, subscription_tier
    }

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for abs_path, arc_name in files:
            try:
                zf.write(abs_path, arc_name)
            except Exception:
                pass
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))

    _prune_old_backups()

    return {
        "path":     zip_path,
        "size_mb":  round(zip_path.stat().st_size / (1024 * 1024), 2),
        "manifest": manifest,
    }


# ── Restore ────────────────────────────────────────────────────────────────────

def restore_backup(
    backup_path: Path,
    overwrite_config: bool = True,
    overwrite_project: bool = False,
) -> dict:
    """Restore files from a backup ZIP. Returns {restored, skipped}."""
    if not backup_path.exists():
        raise FileNotFoundError(str(backup_path))

    result = validate_package(backup_path)
    if not result["is_valid"]:
        raise ValueError(f"Invalid backup: {result['errors']}")

    restored: list[str] = []
    skipped:  list[str] = []

    with zipfile.ZipFile(backup_path, "r") as zf:
        for name in zf.namelist():
            if name == MANIFEST_NAME:
                continue
            is_config  = name.startswith("config/")
            is_project = name.startswith("project/")
            if is_config and not overwrite_config:
                skipped.append(name)
                continue
            if is_project and not overwrite_project:
                skipped.append(name)
                continue
            target = PROJECT_ROOT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(name))
            restored.append(name)

    return {"restored": restored, "skipped": skipped}


def delete_backup(backup_path: Path) -> bool:
    try:
        backup_path.unlink(missing_ok=True)
        return True
    except Exception:
        return False


# ── Project package (shareable ZIP) ───────────────────────────────────────────

def export_project_zip(label: str = "") -> Path:
    """Export a shareable project package ZIP."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    now  = datetime.now()
    ts   = now.strftime("%Y%m%d_%H%M%S")
    slug = f"_{label.strip().replace(' ', '_')}" if label.strip() else ""
    zip_path = BACKUP_DIR / f"package_{ts}{slug}.zip"

    files = list(_iter_backup_files(include_project=True))
    manifest = {
        "package_type":  "project_export",
        "app_version":   APP_VERSION,
        "export_date":   now.isoformat(),
        "package_id":    uuid.uuid4().hex,
        "label":         label.strip(),
        "file_count":    len(files),
        "episode_count": _count_episodes(),
        # FUTURE: user_id, license_key, cloud_project_id
    }

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for abs_path, arc_name in files:
            try:
                zf.write(abs_path, arc_name)
            except Exception:
                pass
        for doc in _EXTRA_DOCS:
            p = PROJECT_ROOT / doc
            if p.exists():
                try:
                    zf.write(p, doc)
                except Exception:
                    pass
        zf.writestr(MANIFEST_NAME, json.dumps(manifest, ensure_ascii=False, indent=2))

    return zip_path


def import_project_zip(
    zip_data: bytes,
    overwrite_config: bool = True,
    overwrite_project: bool = False,
) -> dict:
    """Import an uploaded project ZIP. zip_data is raw bytes."""
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(zip_data)
        tmp_path = Path(tmp.name)
    try:
        v = validate_package(tmp_path)
        if not v["is_valid"]:
            return {"success": False, "errors": v["errors"], "restored": [], "skipped": [], "validation": v}
        r = restore_backup(tmp_path, overwrite_config=overwrite_config, overwrite_project=overwrite_project)
        return {"success": True, "errors": [], **r, "validation": v}
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass


# ── Validation ─────────────────────────────────────────────────────────────────

def validate_package(zip_path: Path) -> dict:
    """Validate a backup or package ZIP. Returns {is_valid, errors, warnings, manifest}."""
    errors:   list[str] = []
    warnings: list[str] = []
    manifest: dict      = {}

    if not zip_path.exists():
        return {"is_valid": False, "errors": ["ファイルが存在しません"], "warnings": [], "manifest": {}}
    if zip_path.stat().st_size == 0:
        return {"is_valid": False, "errors": ["空のファイルです"], "warnings": [], "manifest": {}}

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            if MANIFEST_NAME not in names:
                errors.append("MANIFEST.json が見つかりません")
            else:
                manifest = json.loads(zf.read(MANIFEST_NAME))
                pkg_ver = manifest.get("app_version", "")
                if pkg_ver != APP_VERSION:
                    warnings.append(
                        f"バージョン不一致: パッケージ={pkg_ver or '不明'}, 現在={APP_VERSION}"
                    )
            # Check for at least some content
            data_files = [n for n in names if n != MANIFEST_NAME]
            if not data_files:
                errors.append("データファイルが含まれていません")
    except zipfile.BadZipFile:
        errors.append("ZIP ファイルが破損しています")
    except json.JSONDecodeError as exc:
        errors.append(f"MANIFEST.json の解析エラー: {exc}")
    except Exception as exc:
        errors.append(f"検証エラー: {exc}")

    return {
        "is_valid": len(errors) == 0,
        "errors":   errors,
        "warnings": warnings,
        "manifest": manifest,
    }


# ── Recent activity ────────────────────────────────────────────────────────────

def get_recent_activity(max_items: int = 15) -> list[dict]:
    """Scan key files and return them sorted by modification time (newest first)."""
    items: list[dict] = []

    def _add_dir(base: Path, label_prefix: str, globs: list[str]) -> None:
        if not base.exists():
            return
        for g in globs:
            for f in base.rglob(g):
                try:
                    mtime = f.stat().st_mtime
                    rel   = f.relative_to(PROJECT_ROOT).as_posix()
                    items.append({
                        "label":    f"{label_prefix}/{f.name}",
                        "path":     rel,
                        "mtime":    mtime,
                        "mtime_dt": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M"),
                    })
                except Exception:
                    pass

    _add_dir(PROJECT_ROOT / "config",  "config",  ["*.json"])
    _add_dir(PROJECT_ROOT / "project", "project", ["*.json", "*.txt", "*.srt"])

    items.sort(key=lambda x: x["mtime"], reverse=True)
    return items[:max_items]


# ── Auto-backup helpers ────────────────────────────────────────────────────────

def hours_since_last_backup() -> float | None:
    """Return hours since the most recent backup, or None if no backup exists."""
    backups = list_backups()
    if not backups:
        return None
    last_ts = backups[0]["created_at"]
    if not last_ts:
        return None
    try:
        last_dt = datetime.fromisoformat(last_ts)
        diff = datetime.now() - last_dt
        return diff.total_seconds() / 3600
    except Exception:
        return None


def _read_manifest(zip_path: Path) -> dict:
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            if MANIFEST_NAME in zf.namelist():
                return json.loads(zf.read(MANIFEST_NAME))
    except Exception:
        pass
    return {}


def _prune_old_backups(max_keep: int = 20) -> None:
    backups = sorted(BACKUP_DIR.glob("backup_*.zip"))
    for old in backups[:-max_keep]:
        try:
            old.unlink()
        except Exception:
            pass
