"""Export pipeline — production state management and export package creation."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

STAGE_ORDER: list[str] = ["script", "images", "videos", "voice", "bgm", "se"]

STAGE_LABELS: dict[str, str] = {
    "script": "📝 台本・スクリプト",
    "images": "🖼️ 画像制作",
    "videos": "🎬 動画クリップ",
    "voice":  "🎙️ 音声ナレーション",
    "bgm":    "🎵 BGM",
    "se":     "🔊 効果音 (SE)",
}

STATUS_OPTIONS: list[str] = ["pending", "in_progress", "done", "skipped"]

STATUS_LABELS: dict[str, str] = {
    "pending":     "⏸ 未着手",
    "in_progress": "🔄 進行中",
    "done":        "✅ 完了",
    "skipped":     "⏭ スキップ",
}


# ── Production state ───────────────────────────────────────────────────────────

def load_production_state(episode_dir: Path) -> dict:
    path = episode_dir / "production_state.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for stage in STAGE_ORDER:
                data["stages"].setdefault(stage, {"status": "pending", "completed_at": None})
            return data
        except Exception:
            pass
    return _default_state(episode_dir.name)


def save_production_state(episode_dir: Path, state: dict) -> None:
    state["last_updated"] = datetime.now().isoformat()
    (episode_dir / "production_state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def mark_stage(episode_dir: Path, stage: str, status: str) -> dict:
    state = load_production_state(episode_dir)
    state["stages"][stage]["status"] = status
    state["stages"][stage]["completed_at"] = (
        datetime.now().isoformat() if status == "done" else None
    )
    save_production_state(episode_dir, state)
    return state


def get_completion_pct(state: dict) -> float:
    stages = state.get("stages", {})
    if not stages:
        return 0.0
    done = sum(1 for s in stages.values() if s["status"] in ("done", "skipped"))
    return done / len(stages)


def is_production_ready(state: dict) -> bool:
    """True when all required stages (script, images, videos, voice) are done or skipped."""
    required = {"script", "images", "videos", "voice"}
    stages = state.get("stages", {})
    return all(stages.get(s, {}).get("status") in ("done", "skipped") for s in required)


def _default_state(episode_id: str) -> dict:
    defaults = {s: "pending" for s in STAGE_ORDER}
    defaults["bgm"] = "skipped"
    defaults["se"]  = "skipped"
    return {
        "episode_id":   episode_id,
        "stages":       {s: {"status": defaults[s], "completed_at": None} for s in STAGE_ORDER},
        "notes":        "",
        "last_updated": datetime.now().isoformat(),
    }


# ── Validation helpers ─────────────────────────────────────────────────────────

def validate_episode(episode_dir: Path) -> dict:
    """Aggregate validation of all production files for an episode."""
    from src.pipeline.script_pipeline import validate_script
    from src.pipeline.image_pipeline  import validate_images
    from src.pipeline.video_pipeline  import validate_videos
    from src.pipeline.audio_pipeline  import validate_audio
    return {
        "script": validate_script(episode_dir),
        "images": validate_images(episode_dir),
        "videos": validate_videos(episode_dir),
        "audio":  validate_audio(episode_dir),
    }


def validate_assets(episode_dir: Path) -> dict:
    """Check image, video, and audio asset files."""
    from src.pipeline.image_pipeline import validate_images
    from src.pipeline.video_pipeline import validate_videos
    from src.pipeline.audio_pipeline import validate_audio
    return {
        "images": validate_images(episode_dir),
        "videos": validate_videos(episode_dir),
        "audio":  validate_audio(episode_dir),
    }


def validate_export(episode_dir: Path) -> dict:
    """Alias for validate_export_ready — checks readiness for export."""
    return validate_export_ready(episode_dir)


def validate_export_ready(episode_dir: Path) -> dict:
    """Check required script files exist before creating export package."""
    from src.pipeline.script_pipeline import validate_script
    script_status = validate_script(episode_dir)
    missing = [label for label, v in script_status.items() if not v["exists"]]
    return {
        "ready":         len(missing) == 0,
        "missing":       missing,
        "script_status": script_status,
    }


# ── Export package ─────────────────────────────────────────────────────────────

def create_export_package(
    episode_dir: Path,
    production_state: dict,
    episode_data: dict | None = None,
    metadata: dict | None = None,
) -> dict:
    """
    Copy production files into project/EPXX/export/ and create production_report.json.
    Returns {"export_dir", "copied", "skipped", "report"}.
    """
    export_dir = episode_dir / "export"
    export_dir.mkdir(parents=True, exist_ok=True)

    copied:  list[str] = []
    skipped: list[str] = []

    copy_targets: list[tuple[str, bool]] = [
        ("episode.json",          False),
        ("*_voice_script.txt",    True),
        ("*.srt",                 True),
        ("*_image_prompts.txt",   True),
        ("*_video_prompts.txt",   True),
        ("asset_manifest.json",   False),
        ("production_state.json", False),
    ]
    for pattern, is_glob in copy_targets:
        if is_glob:
            for src in episode_dir.glob(pattern):
                shutil.copy2(src, export_dir / src.name)
                copied.append(src.name)
        else:
            src = episode_dir / pattern
            if src.exists():
                shutil.copy2(src, export_dir / pattern)
                copied.append(pattern)
            else:
                skipped.append(pattern)

    stages = production_state.get("stages", {})
    completed_stages = [s for s, v in stages.items() if v["status"] == "done"]
    missing_stages   = [s for s, v in stages.items() if v["status"] == "pending"]

    report = {
        "episode_id":       episode_dir.name,
        "title":            (episode_data or {}).get("title", ""),
        "export_date":      datetime.now().isoformat(),
        "generation_date":  (episode_data or {}).get("created_at", ""),
        "status":           "production_ready" if not missing_stages else "in_progress",
        "completion_pct":   int(get_completion_pct(production_state) * 100),
        "completed_steps":  completed_stages,
        "missing_steps":    missing_stages,
        "duration_seconds": (episode_data or {}).get("total_duration_seconds", 0),
        "scene_count":      len((episode_data or {}).get("sections", [])),
        "character":        (metadata or {}).get("character"),
        "background":       (metadata or {}).get("background"),
        "prompt_template":  (metadata or {}).get("prompt_template"),
        "notes":            production_state.get("notes", ""),
        "exported_files":   copied,
        "skipped_files":    skipped,
    }

    (export_dir / "production_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    copied.append("production_report.json")

    return {
        "export_dir": export_dir,
        "copied":     copied,
        "skipped":    skipped,
        "report":     report,
    }


def load_production_report(episode_dir: Path) -> dict | None:
    path = episode_dir / "export" / "production_report.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None
