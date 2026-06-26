"""Schema definitions and empty-record factories for director plans."""
from __future__ import annotations

from datetime import datetime

VISUAL_STYLE_OPTIONS = ["cinematic", "anime", "documentary", "educational", "realistic", "watercolor"]
PACING_OPTIONS       = ["slow", "moderate", "fast", "varied"]
CAMERA_ANGLE_OPTIONS = ["正面", "俯瞰", "ローアングル", "斜め45度", "サイド", "指定なし"]
CAMERA_MOTION_OPTIONS = ["静止", "スローパン", "ズームイン", "ズームアウト", "ドリー", "クレーン", "ハンドヘルド", "指定なし"]

EMOTION_HINT    = "例: calm / serious / emotional / urgent / hopeful / educational"
LIGHTING_HINT   = "例: 自然光 / ドラマチック / ソフト / 逆光 / 夜間照明"
FRAMING_HINT    = "例: close-up / medium shot / wide shot / over-the-shoulder"


def make_empty_scene_direction(scene_no: int) -> dict:
    return {
        "scene_no":               scene_no,
        "scene_goal":             "",
        "emotion":                "",
        "camera_angle":           CAMERA_ANGLE_OPTIONS[0],
        "camera_motion":          CAMERA_MOTION_OPTIONS[0],
        "framing":                "",
        "lighting":               "",
        "background_id":          None,
        "character_id":           None,
        "image_prompt_direction": "",
        "video_prompt_direction": "",
        "voice_direction":        "",
        "editing_notes":          "",
    }


def make_empty_plan(episode_id: str, episode_data: dict | None = None) -> dict:
    sections    = (episode_data or {}).get("sections", [])
    scene_count = len(sections)
    title       = (episode_data or {}).get("title", "")
    now         = datetime.now().isoformat()
    return {
        "episode_id":               episode_id,
        "title":                    title,
        "overall_tone":             "",
        "target_emotion":           "",
        "visual_style":             VISUAL_STYLE_OPTIONS[0],
        "pacing":                   PACING_OPTIONS[1],
        "recommended_character_id": None,
        "recommended_background_id": None,
        "scenes": [make_empty_scene_direction(i + 1) for i in range(scene_count)],
        "thumbnail_direction":      "",
        "bgm_direction":            "",
        "se_direction":             "",
        "risk_notes":               "",
        "created_at":               now,
        "updated_at":               now,
    }
