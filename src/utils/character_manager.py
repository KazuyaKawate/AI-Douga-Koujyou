import copy
import json
import uuid
from datetime import datetime
from pathlib import Path

from src.utils.config import PROJECT_ROOT

CHARACTERS_PATH = PROJECT_ROOT / "config" / "characters.json"

GENDER_MAP = {"female": "女性", "male": "男性", "other": "その他"}


# ── Storage ────────────────────────────────────────────────────────────────────

def load_characters() -> dict:
    """Return {"characters": [...], "default_character_id": str|None}."""
    if CHARACTERS_PATH.exists():
        try:
            return json.loads(CHARACTERS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"characters": [], "default_character_id": None}


def save_characters(data: dict) -> None:
    CHARACTERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHARACTERS_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Read ───────────────────────────────────────────────────────────────────────

def get_character(char_id: str) -> dict | None:
    return next(
        (c for c in load_characters()["characters"] if c["id"] == char_id), None
    )


def get_default_character() -> dict | None:
    data = load_characters()
    if data.get("default_character_id"):
        return get_character(data["default_character_id"])
    return None


# ── Mutate ─────────────────────────────────────────────────────────────────────

def add_character(char_dict: dict) -> dict:
    """Add character; always assigns a new id and timestamps. Returns saved char."""
    data = load_characters()
    now = datetime.now().isoformat()
    char_dict = copy.deepcopy(char_dict)
    char_dict["id"] = f"char_{uuid.uuid4().hex[:8]}"
    char_dict["created_at"] = now
    char_dict["updated_at"] = now
    data["characters"].append(char_dict)
    save_characters(data)
    return char_dict


def edit_character(char_id: str, updates: dict) -> dict | None:
    data = load_characters()
    for char in data["characters"]:
        if char["id"] == char_id:
            _deep_update(char, updates)
            char["updated_at"] = datetime.now().isoformat()
            save_characters(data)
            return char
    return None


def delete_character(char_id: str) -> bool:
    data = load_characters()
    before = len(data["characters"])
    data["characters"] = [c for c in data["characters"] if c["id"] != char_id]
    if data.get("default_character_id") == char_id:
        data["default_character_id"] = None
    save_characters(data)
    return len(data["characters"]) < before


def duplicate_character(char_id: str) -> dict | None:
    char = get_character(char_id)
    if not char:
        return None
    new_char = copy.deepcopy(char)
    for key in ("id", "created_at", "updated_at"):
        new_char.pop(key, None)
    new_char["basic"]["display_name"] += " (コピー)"
    new_char["assets"] = {"portrait": None, "expressions": [], "voice_sample": None}
    return add_character(new_char)


def set_default_character(char_id: str | None) -> None:
    data = load_characters()
    data["default_character_id"] = char_id
    save_characters(data)


# ── Prompt helpers ─────────────────────────────────────────────────────────────

def character_to_prompt_snippet(char: dict) -> str:
    """Return the text block injected into AI prompts for this character."""
    basic   = char.get("basic", {})
    persona = char.get("personality", {})
    prompt  = char.get("prompt", {})

    lines = ["【キャラクター設定（以下に従ってナレーション・各プロンプトを生成すること）】"]
    if basic.get("display_name"):
        lines.append(f"・名前: {basic['display_name']}")
    if basic.get("age"):
        lines.append(f"・年齢: {basic['age']}歳")
    if basic.get("gender"):
        lines.append(f"・性別: {GENDER_MAP.get(basic['gender'], basic['gender'])}")
    if basic.get("role"):
        lines.append(f"・役割: {basic['role']}")
    if persona.get("personality"):
        lines.append(f"・性格: {persona['personality']}")
    if persona.get("speaking_style"):
        lines.append(f"・話し方: {persona['speaking_style']}")
    if persona.get("first_person"):
        lines.append(f"・一人称: {persona['first_person']}")
    if persona.get("catch_phrase"):
        lines.append(f"・キャッチフレーズ: {persona['catch_phrase']}")
    if prompt.get("image_prompt_base"):
        lines.append(f"・画像プロンプトベース（各シーンのimage_promptに含めること）: {prompt['image_prompt_base']}")
    if prompt.get("video_prompt_base"):
        lines.append(f"・動画プロンプトベース（各シーンのvideo_promptに含めること）: {prompt['video_prompt_base']}")
    if prompt.get("voice_description"):
        lines.append(f"・音声説明: {prompt['voice_description']}")
    first = persona.get("first_person", "私")
    style = persona.get("speaking_style", "")
    lines.append(f"・ナレーションは「{first}」を主語に{style}で書くこと")
    return "\n".join(lines)


def preview_prompt(char: dict, prompt_type: str = "image") -> str:
    """Preview the character's contribution to a specific prompt type."""
    if not char:
        return ""
    appearance = char.get("appearance", {})
    prompt_cfg = char.get("prompt", {})
    if prompt_type == "image":
        base = prompt_cfg.get("image_prompt_base", "")
        parts = [base] if base else []
        hair = f"{appearance.get('hair_color','')} {appearance.get('hairstyle','')} hair".strip()
        eye  = f"{appearance.get('eye_color','')} eyes".strip() if appearance.get("eye_color") else ""
        for part in [hair, eye, appearance.get("clothing",""), appearance.get("accessories","")]:
            if part:
                parts.append(part)
        return ", ".join(p for p in parts if p)
    elif prompt_type == "video":
        return prompt_cfg.get("video_prompt_base", "")
    elif prompt_type == "voice":
        return prompt_cfg.get("voice_description", "")
    return ""


# ── Scaffold ──────────────────────────────────────────────────────────────────

def make_empty_character(display_name: str = "", role: str = "ナレーター") -> dict:
    return {
        "basic": {
            "display_name": display_name,
            "age": 25,
            "gender": "female",
            "role": role,
        },
        "appearance": {
            "hairstyle":   "",
            "hair_color":  "",
            "eye_color":   "",
            "clothing":    "",
            "accessories": "",
        },
        "personality": {
            "personality":    "",
            "speaking_style": "",
            "first_person":   "私",
            "catch_phrase":   "",
        },
        "prompt": {
            "image_prompt_base": "",
            "video_prompt_base": "",
            "voice_description": "",
        },
        "assets": {
            "portrait":    None,
            "expressions": [],
            "voice_sample": None,
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
