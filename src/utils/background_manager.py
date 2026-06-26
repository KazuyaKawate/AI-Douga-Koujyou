import copy
import json
import uuid
from datetime import datetime
from pathlib import Path

from src.utils.config import PROJECT_ROOT

BACKGROUNDS_PATH = PROJECT_ROOT / "config" / "backgrounds.json"

CATEGORY_OPTIONS = [
    "インドア", "アウトドア", "スタジオ", "自然", "都市",
    "ファンタジー", "SF・未来", "歴史・時代", "その他",
]
TIME_OPTIONS  = ["昼", "朝", "夕方", "夜", "夜明け", "曇天", "指定なし"]
ANGLE_OPTIONS = ["正面", "俯瞰", "ローアングル", "斜め45度", "サイド", "指定なし"]
MOTION_OPTIONS = [
    "静止", "スローパン", "ズームイン", "ズームアウト",
    "ドリー", "クレーン", "ハンドヘルド", "指定なし",
]


# ── Storage ────────────────────────────────────────────────────────────────────

def load_backgrounds() -> dict:
    """Return {"backgrounds": [...], "default_background_id": str|None}."""
    if BACKGROUNDS_PATH.exists():
        try:
            return json.loads(BACKGROUNDS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"backgrounds": [], "default_background_id": None}


def save_backgrounds(data: dict) -> None:
    BACKGROUNDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKGROUNDS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Read ───────────────────────────────────────────────────────────────────────

def get_background(bg_id: str) -> dict | None:
    return next(
        (b for b in load_backgrounds()["backgrounds"] if b["id"] == bg_id), None
    )


def get_default_background() -> dict | None:
    data = load_backgrounds()
    if data.get("default_background_id"):
        return get_background(data["default_background_id"])
    return None


# ── Mutate ─────────────────────────────────────────────────────────────────────

def add_background(bg_dict: dict) -> dict:
    """Add background; always assigns a new id and timestamps. Returns saved bg."""
    data = load_backgrounds()
    now = datetime.now().isoformat()
    bg_dict = copy.deepcopy(bg_dict)
    bg_dict["id"] = f"bg_{uuid.uuid4().hex[:8]}"
    bg_dict["created_at"] = now
    bg_dict["updated_at"] = now
    data["backgrounds"].append(bg_dict)
    save_backgrounds(data)
    return bg_dict


def update_background(bg_id: str, updates: dict) -> dict | None:
    data = load_backgrounds()
    for bg in data["backgrounds"]:
        if bg["id"] == bg_id:
            _deep_update(bg, updates)
            bg["updated_at"] = datetime.now().isoformat()
            save_backgrounds(data)
            return bg
    return None


def delete_background(bg_id: str) -> bool:
    data = load_backgrounds()
    before = len(data["backgrounds"])
    data["backgrounds"] = [b for b in data["backgrounds"] if b["id"] != bg_id]
    if data.get("default_background_id") == bg_id:
        data["default_background_id"] = None
    save_backgrounds(data)
    return len(data["backgrounds"]) < before


def duplicate_background(bg_id: str) -> dict | None:
    bg = get_background(bg_id)
    if not bg:
        return None
    new_bg = copy.deepcopy(bg)
    for key in ("id", "created_at", "updated_at"):
        new_bg.pop(key, None)
    new_bg["basic"]["display_name"] += " (コピー)"
    new_bg["assets"] = {
        "reference_images": [],
        "layout_image": None,
        "sample_video": None,
    }
    return add_background(new_bg)


def set_default_background(bg_id: str | None) -> None:
    data = load_backgrounds()
    data["default_background_id"] = bg_id
    save_backgrounds(data)


# ── Prompt helpers ─────────────────────────────────────────────────────────────

def background_to_prompt_snippet(bg: dict) -> str:
    """Return the text block injected into AI prompts for this background."""
    basic  = bg.get("basic", {})
    visual = bg.get("visual", {})
    camera = bg.get("camera", {})
    prompt = bg.get("prompt", {})

    lines = ["【背景・シーン設定（以下に従って各シーンのimage_prompt/video_promptを生成すること）】"]
    if basic.get("display_name"):
        lines.append(f"・背景名: {basic['display_name']}")
    if basic.get("category"):
        lines.append(f"・カテゴリ: {basic['category']}")
    if visual.get("location_type"):
        lines.append(f"・ロケーション: {visual['location_type']}")
    if visual.get("time_of_day") and visual["time_of_day"] != "指定なし":
        lines.append(f"・時間帯: {visual['time_of_day']}")
    if visual.get("lighting"):
        lines.append(f"・照明: {visual['lighting']}")
    if visual.get("color_tone"):
        lines.append(f"・カラートーン: {visual['color_tone']}")
    if visual.get("props"):
        lines.append(f"・小道具・装飾: {visual['props']}")
    if visual.get("atmosphere"):
        lines.append(f"・雰囲気: {visual['atmosphere']}")
    if camera.get("default_camera_angle") and camera["default_camera_angle"] != "指定なし":
        lines.append(f"・カメラアングル: {camera['default_camera_angle']}")
    if camera.get("default_lens"):
        lines.append(f"・レンズ: {camera['default_lens']}")
    if camera.get("default_motion") and camera["default_motion"] != "指定なし":
        lines.append(f"・カメラモーション: {camera['default_motion']}")
    if camera.get("framing"):
        lines.append(f"・フレーミング: {camera['framing']}")
    if prompt.get("image_prompt_base"):
        lines.append(
            f"・画像プロンプトベース（各シーンのimage_promptに含めること）: {prompt['image_prompt_base']}"
        )
    if prompt.get("video_prompt_base"):
        lines.append(
            f"・動画プロンプトベース（各シーンのvideo_promptに含めること）: {prompt['video_prompt_base']}"
        )
    if prompt.get("negative_prompt"):
        lines.append(f"・除外要素（ネガティブプロンプト）: {prompt['negative_prompt']}")
    if prompt.get("style_notes"):
        lines.append(f"・スタイルノート: {prompt['style_notes']}")
    return "\n".join(lines)


def preview_prompt(bg: dict, prompt_type: str = "image") -> str:
    """Preview the background's contribution to a specific prompt type."""
    if not bg:
        return ""
    visual = bg.get("visual", {})
    camera = bg.get("camera", {})
    prompt_cfg = bg.get("prompt", {})
    if prompt_type == "image":
        parts = []
        if prompt_cfg.get("image_prompt_base"):
            parts.append(prompt_cfg["image_prompt_base"])
        if visual.get("location_type"):
            parts.append(visual["location_type"])
        if visual.get("lighting"):
            parts.append(visual["lighting"])
        if visual.get("color_tone"):
            parts.append(f"{visual['color_tone']} color tone")
        if visual.get("atmosphere"):
            parts.append(visual["atmosphere"])
        return ", ".join(p for p in parts if p)
    elif prompt_type == "video":
        parts = []
        if prompt_cfg.get("video_prompt_base"):
            parts.append(prompt_cfg["video_prompt_base"])
        if camera.get("default_motion") and camera["default_motion"] != "指定なし":
            parts.append(camera["default_motion"])
        if camera.get("default_camera_angle") and camera["default_camera_angle"] != "指定なし":
            parts.append(f"{camera['default_camera_angle']} angle")
        return ", ".join(p for p in parts if p)
    elif prompt_type == "negative":
        return prompt_cfg.get("negative_prompt", "")
    return ""


# ── Scaffold ──────────────────────────────────────────────────────────────────

def make_empty_background(display_name: str = "", category: str = "インドア") -> dict:
    return {
        "basic": {
            "display_name": display_name,
            "category":     category,
            "description":  "",
        },
        "visual": {
            "location_type": "",
            "time_of_day":   "昼",
            "lighting":      "",
            "color_tone":    "",
            "props":         "",
            "atmosphere":    "",
        },
        "camera": {
            "default_camera_angle": "正面",
            "default_lens":         "",
            "default_motion":       "静止",
            "framing":              "",
        },
        "prompt": {
            "image_prompt_base": "",
            "video_prompt_base": "",
            "negative_prompt":   "",
            "style_notes":       "",
        },
        "assets": {
            "reference_images": [],
            "layout_image":     None,
            "sample_video":     None,
        },
    }


# ── Internal ──────────────────────────────────────────────────────────────────

def _deep_update(target: dict, source: dict) -> dict:
    for k, v in source.items():
        if k in target and isinstance(target[k], dict) and isinstance(v, dict):
            _deep_update(target[k], v)
        else:
            target[k] = v
    return target
