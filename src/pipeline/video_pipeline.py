"""Video pipeline — validates video clip assets for an episode."""
from __future__ import annotations

from pathlib import Path

CLIP_EXT = {".mp4", ".mov", ".webm", ".avi", ".mkv", ".m4v"}


def list_video_clips(episode_dir: Path) -> list[Path]:
    """Find video clips in episode dir and videos/ folder (episode-prefixed)."""
    clips: list[Path] = [
        f for f in episode_dir.iterdir()
        if f.is_file() and f.suffix.lower() in CLIP_EXT
    ]
    try:
        from src.utils.config import PROJECT_ROOT
        videos_dir = PROJECT_ROOT / "videos"
        ep_id = episode_dir.name.lower()
        if videos_dir.exists():
            clips += [
                f for f in videos_dir.iterdir()
                if f.is_file()
                and ep_id in f.name.lower()
                and f.suffix.lower() in CLIP_EXT
            ]
    except Exception:
        pass
    return sorted(set(clips), key=lambda f: f.name)


def validate_videos(episode_dir: Path) -> dict:
    prompt_files = list(episode_dir.glob("*_video_prompts.txt"))
    clip_files   = list_video_clips(episode_dir)
    return {
        "prompt_file_exists": bool(prompt_files),
        "prompt_files":       [f.name for f in prompt_files],
        "clip_count":         len(clip_files),
        "clip_files":         [f.name for f in clip_files],
        "has_clips":          bool(clip_files),
    }


def is_videos_complete(episode_dir: Path) -> bool:
    return validate_videos(episode_dir)["has_clips"]
