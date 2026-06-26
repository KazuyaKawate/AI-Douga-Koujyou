"""Audio pipeline — validates voice, BGM, and SE assets for an episode."""
from __future__ import annotations

from pathlib import Path

AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".opus"}


def list_voice_files(episode_dir: Path) -> list[Path]:
    """Find audio files in episode dir and voices/ folder (episode-prefixed)."""
    files: list[Path] = [
        f for f in episode_dir.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXT
    ]
    try:
        from src.utils.config import PROJECT_ROOT
        voices_dir = PROJECT_ROOT / "voices"
        ep_id = episode_dir.name.lower()
        if voices_dir.exists():
            files += [
                f for f in voices_dir.iterdir()
                if f.is_file()
                and ep_id in f.name.lower()
                and f.suffix.lower() in AUDIO_EXT
            ]
    except Exception:
        pass
    return sorted(set(files), key=lambda f: f.name)


def validate_audio(episode_dir: Path) -> dict:
    script_files = list(episode_dir.glob("*_voice_script.txt"))
    voice_files  = list_voice_files(episode_dir)
    return {
        "voice_script_exists": bool(script_files),
        "voice_script_files":  [f.name for f in script_files],
        "voice_file_count":    len(voice_files),
        "voice_files":         [f.name for f in voice_files],
        "has_voice":           bool(voice_files),
    }


def is_audio_complete(episode_dir: Path) -> bool:
    return validate_audio(episode_dir)["has_voice"]
