"""Script pipeline — validates episode script and prompt text files."""
from __future__ import annotations

import json
from pathlib import Path

# (pattern, human label, is_glob)
REQUIRED_FILES: list[tuple[str, str, bool]] = [
    ("episode.json",        "エピソードデータ",  False),
    ("*_voice_script.txt",  "音声台本",          True),
    ("*.srt",               "字幕 (SRT)",        True),
    ("*_image_prompts.txt", "画像プロンプト",     True),
    ("*_video_prompts.txt", "動画プロンプト",     True),
]


def validate_script(episode_dir: Path) -> dict[str, dict]:
    """
    Check required script files exist.
    Returns {label: {"exists": bool, "pattern": str, "files": [str]}}
    """
    results: dict[str, dict] = {}
    for pattern, label, is_glob in REQUIRED_FILES:
        if is_glob:
            found = list(episode_dir.glob(pattern))
            results[label] = {
                "exists":  bool(found),
                "pattern": pattern,
                "files":   [f.name for f in found],
            }
        else:
            path = episode_dir / pattern
            results[label] = {
                "exists":  path.exists(),
                "pattern": pattern,
                "files":   [pattern] if path.exists() else [],
            }
    return results


def load_episode_data(episode_dir: Path) -> dict | None:
    ep_json = episode_dir / "episode.json"
    if not ep_json.exists():
        return None
    try:
        return json.loads(ep_json.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_script_complete(episode_dir: Path) -> bool:
    return all(v["exists"] for v in validate_script(episode_dir).values())


def get_voice_script_path(episode_dir: Path) -> Path | None:
    files = list(episode_dir.glob("*_voice_script.txt"))
    return files[0] if files else None


def get_srt_path(episode_dir: Path) -> Path | None:
    files = list(episode_dir.glob("*.srt"))
    return files[0] if files else None


def get_image_prompts_path(episode_dir: Path) -> Path | None:
    files = list(episode_dir.glob("*_image_prompts.txt"))
    return files[0] if files else None


def get_video_prompts_path(episode_dir: Path) -> Path | None:
    files = list(episode_dir.glob("*_video_prompts.txt"))
    return files[0] if files else None
