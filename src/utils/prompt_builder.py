import copy
import json
import uuid
from datetime import datetime
from pathlib import Path

from src.utils.config import PROJECT_ROOT

TEMPLATES_PATH = PROJECT_ROOT / "config" / "prompt_templates.json"

# ── Option sets ────────────────────────────────────────────────────────────────

OUTPUT_TYPES = [
    "Nano Banana 画像プロンプト",
    "Runway 動画プロンプト",
    "ボイスディレクション",
    "サムネイルプロンプト",
]

MOOD_OPTIONS = ["calm", "serious", "emotional", "urgent", "hopeful", "educational"]
CAMERA_OPTIONS = [
    "close-up", "medium shot", "wide shot",
    "over-the-shoulder", "static", "slow push-in",
]
STYLE_OPTIONS = [
    "anime", "cinematic", "documentary",
    "educational", "realistic", "watercolor",
]

# ── Mapping tables ─────────────────────────────────────────────────────────────

MOOD_EN: dict[str, str] = {
    "calm":        "calm, serene, peaceful, soft natural lighting",
    "serious":     "serious, professional, dramatic lighting, intense focus",
    "emotional":   "emotional, warm, heartfelt, golden hour lighting",
    "urgent":      "urgent, dynamic, high contrast, fast-paced energy",
    "hopeful":     "hopeful, bright, optimistic, uplifting warm tones",
    "educational": "clean, clear, informative, neutral professional lighting",
}

MOOD_JP: dict[str, str] = {
    "calm":        "落ち着いた・穏やかな雰囲気で、ゆっくりと語りかけるように",
    "serious":     "真剣で力強く、プロフェッショナルな語り口で",
    "emotional":   "感情を込めて、温かみと共感を持った語り口で",
    "urgent":      "緊迫感を持って、テンポよく力強く",
    "hopeful":     "希望に満ちた前向きな声で、明るく励ますように",
    "educational": "わかりやすく親切に、聴き取りやすいペースで",
}

CAMERA_EN: dict[str, str] = {
    "close-up":          "close-up shot, tight framing, detailed facial expression",
    "medium shot":       "medium shot, waist-up, natural balanced composition",
    "wide shot":         "wide shot, full body, environmental context visible",
    "over-the-shoulder": "over-the-shoulder perspective, depth and dimension",
    "static":            "static locked-off camera, stable and composed framing",
    "slow push-in":      "slow dolly push-in, gradual cinematic approach",
}

CAMERA_MOTION_EN: dict[str, str] = {
    "close-up":          "static camera hold",
    "medium shot":       "steady cam, no movement",
    "wide shot":         "slow pan, wide establishing",
    "over-the-shoulder": "subtle drift, minimal movement",
    "static":            "locked off, no camera movement",
    "slow push-in":      "slow dolly forward, gradual zoom in",
}

CAMERA_JP: dict[str, str] = {
    "close-up":          "クローズアップ",
    "medium shot":       "ミディアムショット",
    "wide shot":         "ワイドショット",
    "over-the-shoulder": "オーバーザショルダー",
    "static":            "固定カメラ",
    "slow push-in":      "スロープッシュイン",
}

STYLE_EN: dict[str, str] = {
    "anime":         "anime style, Japanese animation, vibrant colors, clean linework, 2D cel shading",
    "cinematic":     "cinematic film quality, anamorphic bokeh, movie-grade color grading, 35mm aesthetic",
    "documentary":   "documentary realism, natural handheld camera, journalistic authenticity",
    "educational":   "clean educational graphics, clear visual hierarchy, professional presentation",
    "realistic":     "photorealistic, hyperrealistic, DSLR quality, natural lighting, 8k resolution",
    "watercolor":    "watercolor illustration, soft paint strokes, hand-painted texture, delicate washes",
}

STYLE_NEG: dict[str, str] = {
    "anime":         "photorealistic, 3D CGI, ugly proportions, blurry",
    "cinematic":     "flat lighting, amateur, phone quality, cartoon, blurry, overexposed",
    "documentary":   "staged, over-processed, HDR, cartoon, artificial",
    "educational":   "cluttered, confusing, low quality, dark, blurry",
    "realistic":     "cartoon, anime, illustration, painting, stylized, blurry, watermark",
    "watercolor":    "photorealistic, sharp hard edges, 3D render, digital gloss, blurry",
}

QUALITY_NEG = "low quality, worst quality, deformed, bad anatomy, watermark, signature, lowres"


# ── Build functions ────────────────────────────────────────────────────────────

def build_prompt(
    output_type: str,
    mood: str,
    camera: str,
    style: str,
    character: dict | None = None,
    background: dict | None = None,
) -> tuple[str, str]:
    """
    Build a combined prompt locally from selected settings.
    Returns (prompt_text, negative_prompt).
    """
    if output_type == "Nano Banana 画像プロンプト":
        return _build_image_prompt(mood, camera, style, character, background)
    elif output_type == "Runway 動画プロンプト":
        return _build_video_prompt(mood, camera, style, character, background)
    elif output_type == "ボイスディレクション":
        return _build_voice_direction(mood, camera, style, character, background)
    elif output_type == "サムネイルプロンプト":
        return _build_thumbnail_prompt(mood, camera, style, character, background)
    return "", ""


def _build_image_prompt(
    mood: str,
    camera: str,
    style: str,
    character: dict | None,
    background: dict | None,
) -> tuple[str, str]:
    parts: list[str] = []

    if character:
        base = character.get("prompt", {}).get("image_prompt_base", "")
        if base:
            parts.append(base)
        app = character.get("appearance", {})
        looks = ", ".join(filter(None, [
            f"{app.get('hair_color','')} {app.get('hairstyle','')} hair".strip(),
            f"{app.get('eye_color','')} eyes".strip() if app.get("eye_color") else "",
            app.get("clothing", ""),
        ]))
        if looks:
            parts.append(looks)

    if background:
        base = background.get("prompt", {}).get("image_prompt_base", "")
        if base:
            parts.append(base)
        vis = background.get("visual", {})
        for field in ("location_type", "lighting", "color_tone"):
            val = vis.get(field, "")
            if val:
                parts.append(val)

    parts.append(MOOD_EN.get(mood, mood))
    parts.append(CAMERA_EN.get(camera, camera))
    parts.append(STYLE_EN.get(style, style))
    parts.append("high quality")

    neg_parts = [QUALITY_NEG, STYLE_NEG.get(style, "")]
    if background:
        bg_neg = background.get("prompt", {}).get("negative_prompt", "")
        if bg_neg:
            neg_parts.append(bg_neg)

    return ", ".join(p for p in parts if p), ", ".join(p for p in neg_parts if p)


def _build_video_prompt(
    mood: str,
    camera: str,
    style: str,
    character: dict | None,
    background: dict | None,
) -> tuple[str, str]:
    parts: list[str] = []

    if character:
        base = character.get("prompt", {}).get("video_prompt_base", "")
        if base:
            parts.append(base)

    if background:
        base = background.get("prompt", {}).get("video_prompt_base", "")
        if base:
            parts.append(base)
        cam_def = background.get("camera", {}).get("default_motion", "")
        if cam_def and cam_def != "指定なし":
            parts.append(cam_def)

    parts.append(CAMERA_MOTION_EN.get(camera, camera))
    parts.append(CAMERA_EN.get(camera, camera))
    parts.append(MOOD_EN.get(mood, mood))
    parts.append(STYLE_EN.get(style, style))
    parts.append("professional broadcast quality")

    neg_parts = [QUALITY_NEG, STYLE_NEG.get(style, "")]
    if background:
        bg_neg = background.get("prompt", {}).get("negative_prompt", "")
        if bg_neg:
            neg_parts.append(bg_neg)

    return ", ".join(p for p in parts if p), ", ".join(p for p in neg_parts if p)


def _build_voice_direction(
    mood: str,
    camera: str,
    style: str,
    character: dict | None,
    background: dict | None,
) -> tuple[str, str]:
    lines = ["【ボイスディレクション】"]

    if character:
        b = character.get("basic", {})
        p = character.get("personality", {})
        pr = character.get("prompt", {})
        lines.append(f"キャラクター: {b.get('display_name','（名前未設定）')}（{b.get('role','')}）")
        if pr.get("voice_description"):
            lines.append(f"声の特徴: {pr['voice_description']}")
        if p.get("speaking_style"):
            lines.append(f"話し方: {p['speaking_style']}")
        if p.get("first_person"):
            lines.append(f"一人称: {p['first_person']}")
        if p.get("catch_phrase"):
            lines.append(f"キャッチフレーズ: {p['catch_phrase']}")
    else:
        lines.append("キャラクター: （未選択）")

    lines.append(f"ムード・感情: {MOOD_JP.get(mood, mood)}")
    lines.append(f"カメラ（参考）: {CAMERA_JP.get(camera, camera)}")

    style_note = {
        "anime":         "キャラクターらしい個性的な声色で",
        "cinematic":     "映画的な重みと緊張感のある語り口で",
        "documentary":   "自然体でリアリティのある話し方で",
        "educational":   "明瞭で聞き取りやすく、教育的なトーンで",
        "realistic":     "自然で日常的な話し方で",
        "watercolor":    "柔らかく詩的な語り口で",
    }.get(style, "")
    if style_note:
        lines.append(f"スタイル: {style_note}")

    if background:
        v = background.get("visual", {})
        atm = v.get("atmosphere", "")
        if atm:
            lines.append(f"場の雰囲気: {atm}")

    return "\n".join(lines), ""


def _build_thumbnail_prompt(
    mood: str,
    camera: str,
    style: str,
    character: dict | None,
    background: dict | None,
) -> tuple[str, str]:
    parts: list[str] = []

    if character:
        base = character.get("prompt", {}).get("image_prompt_base", "")
        if base:
            parts.append(base)
        b = character.get("basic", {})
        if b.get("display_name"):
            parts.append(f"{b['display_name']} character")

    if background:
        base = background.get("prompt", {}).get("image_prompt_base", "")
        if base:
            parts.append(base)

    parts += [
        "YouTube thumbnail",
        "bold eye-catching composition",
        "high contrast",
        "vibrant colors",
        "clear text area at top",
        MOOD_EN.get(mood, mood),
        STYLE_EN.get(style, style),
        "professional graphic design",
        "16:9 aspect ratio",
        "8k quality",
    ]

    neg_parts = [
        QUALITY_NEG,
        STYLE_NEG.get(style, ""),
        "cluttered, text overlap, boring, flat, dull",
    ]
    if background:
        bg_neg = background.get("prompt", {}).get("negative_prompt", "")
        if bg_neg:
            neg_parts.append(bg_neg)

    return ", ".join(p for p in parts if p), ", ".join(p for p in neg_parts if p)


def template_to_pipeline_note(tmpl: dict) -> str:
    """Build the text block injected into the OpenAI pipeline prompt."""
    lines = [
        "【プロンプトテンプレート（以下の設定を各シーンの生成に反映すること）】",
        f"・テンプレート名: {tmpl.get('name','')}",
        f"・出力タイプ: {tmpl.get('output_type','')}",
        f"・ムード: {tmpl.get('mood','')}",
        f"・カメラ: {tmpl.get('camera','')}",
        f"・スタイル: {tmpl.get('style','')}",
    ]
    if tmpl.get("prompt_text"):
        lines.append(
            f"・プロンプト参考テキスト（各シーンのimage_prompt/video_promptに反映すること）:"
            f"\n  {tmpl['prompt_text'][:400]}"
        )
    if tmpl.get("negative_prompt"):
        lines.append(f"・除外要素: {tmpl['negative_prompt'][:200]}")
    if tmpl.get("notes"):
        lines.append(f"・制作ノート: {tmpl['notes']}")
    return "\n".join(lines)


# ── CRUD ───────────────────────────────────────────────────────────────────────

def load_templates() -> dict:
    """Return {"templates": [...]}."""
    if TEMPLATES_PATH.exists():
        try:
            return json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"templates": []}


def save_templates(data: dict) -> None:
    TEMPLATES_PATH.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATES_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def get_template(tmpl_id: str) -> dict | None:
    return next(
        (t for t in load_templates()["templates"] if t["id"] == tmpl_id), None
    )


def add_template(tmpl_dict: dict) -> dict:
    data = load_templates()
    now = datetime.now().isoformat()
    tmpl_dict = copy.deepcopy(tmpl_dict)
    tmpl_dict["id"] = f"tmpl_{uuid.uuid4().hex[:8]}"
    tmpl_dict["created_at"] = now
    tmpl_dict["updated_at"] = now
    data["templates"].append(tmpl_dict)
    save_templates(data)
    return tmpl_dict


def update_template(tmpl_id: str, updates: dict) -> dict | None:
    data = load_templates()
    for tmpl in data["templates"]:
        if tmpl["id"] == tmpl_id:
            tmpl.update(updates)
            tmpl["updated_at"] = datetime.now().isoformat()
            save_templates(data)
            return tmpl
    return None


def delete_template(tmpl_id: str) -> bool:
    data = load_templates()
    before = len(data["templates"])
    data["templates"] = [t for t in data["templates"] if t["id"] != tmpl_id]
    save_templates(data)
    return len(data["templates"]) < before


def duplicate_template(tmpl_id: str) -> dict | None:
    tmpl = get_template(tmpl_id)
    if not tmpl:
        return None
    new_tmpl = copy.deepcopy(tmpl)
    for key in ("id", "created_at", "updated_at"):
        new_tmpl.pop(key, None)
    new_tmpl["name"] += " (コピー)"
    return add_template(new_tmpl)
