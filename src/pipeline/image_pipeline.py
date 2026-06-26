"""Image pipeline — validates image asset files for an episode."""
from __future__ import annotations

from pathlib import Path

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"}


def list_image_files(episode_dir: Path) -> list[Path]:
    """Find image files in episode dir and assets/images/ (episode-prefixed)."""
    files: list[Path] = [
        f for f in episode_dir.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXT
    ]
    try:
        from src.utils.config import PROJECT_ROOT
        assets_dir = PROJECT_ROOT / "assets" / "images"
        ep_id = episode_dir.name.lower()
        if assets_dir.exists():
            files += [
                f for f in assets_dir.iterdir()
                if f.is_file()
                and ep_id in f.name.lower()
                and f.suffix.lower() in IMAGE_EXT
            ]
    except Exception:
        pass
    return sorted(set(files), key=lambda f: f.name)


def validate_images(episode_dir: Path) -> dict:
    prompt_files = list(episode_dir.glob("*_image_prompts.txt"))
    image_files  = list_image_files(episode_dir)
    return {
        "prompt_file_exists": bool(prompt_files),
        "prompt_files":       [f.name for f in prompt_files],
        "image_count":        len(image_files),
        "image_files":        [f.name for f in image_files],
        "has_images":         bool(image_files),
    }


def is_images_complete(episode_dir: Path) -> bool:
    return validate_images(episode_dir)["has_images"]
