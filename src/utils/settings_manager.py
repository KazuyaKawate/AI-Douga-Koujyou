import json
from pathlib import Path

from src.utils.config import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "config" / "settings.json"

DEFAULTS: dict = {
    "project": {
        "default_output_folder": "output",
        "default_episode_length": "3分",
        "default_scene_count": 4,
        "video_aspect_ratio": "16:9",
        "fps": 30,
        "resolution": "1920x1080",
    },
    "ai": {
        "model": "gpt-4o-mini",
        "dev_mode": True,
        "cost_saving": True,
        "temperature": 0.8,
        "max_tokens": 3000,
    },
    "generation": {
        "image_provider": "Manual",
        "video_provider": "Manual",
        "voice_provider": "Manual",
    },
    "export": {
        "youtube_shorts": False,
        "tiktok": False,
        "instagram_reels": False,
    },
}


def load_settings() -> dict:
    """Return settings merged over DEFAULTS; never raises."""
    if CONFIG_PATH.exists():
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return _deep_merge(DEFAULTS, raw)
        except Exception:
            pass
    return _copy(DEFAULTS)


def save_settings(settings: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def _copy(d: dict) -> dict:
    return json.loads(json.dumps(d))
