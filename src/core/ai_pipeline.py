"""
V2.0 AI pipeline — generates a complete episode (script + scene split +
image/video prompts + voice script + SRT) in a single OpenAI call.
"""

import json
from openai import OpenAI

from src.utils.config import OPENAI_API_KEY
from src.core import episode_manager as em

DURATION_SECONDS: dict[str, int] = {
    "1分": 60,
    "2分": 120,
    "3分": 180,
    "5分": 300,
    "10分": 600,
}


def generate_episode_ai(
    topic: str,
    episode_id: str,
    duration: str = "3分",
    style: str = "解説・教育",
    target: str = "",
    num_scenes: int = 4,
    cost_saving: bool = False,
) -> tuple[dict, dict]:
    """
    Full pipeline: OpenAI → episode dict → export all files.
    Returns (episode, written_files).
    cost_saving=True reduces max_tokens and instructs shorter content.
    """
    total_sec = DURATION_SECONDS.get(duration, 180)
    sec_per_scene = total_sec // num_scenes

    raw = _call_openai(topic, duration, total_sec, style, target, num_scenes, sec_per_scene, cost_saving)
    _validate(raw, num_scenes)

    ep = _build_episode(episode_id, raw, target, sec_per_scene)
    written = em.export_episode(ep)
    return ep, written


# ── OpenAI call ──────────────────────────────────────────────────────────────

def _call_openai(
    topic: str,
    duration: str,
    total_sec: int,
    style: str,
    target: str,
    num_scenes: int,
    sec_per_scene: int,
    cost_saving: bool = False,
) -> dict:
    from src.utils.settings_manager import load_settings
    _ai = load_settings()["ai"]
    model       = _ai.get("model", "gpt-4o-mini")
    temperature = float(_ai.get("temperature", 0.8))
    max_tokens  = 1500 if cost_saving else int(_ai.get("max_tokens", 3000))

    client = OpenAI(api_key=OPENAI_API_KEY)

    cost_note = (
        "\n- コスト節約モード: narrationは120文字以内、image_promptとvideo_promptは40語以内で簡潔に"
        if cost_saving else ""
    )

    prompt = f"""あなたはプロの動画プロデューサーです。

条件:
- テーマ: {topic}
- 動画の長さ: {duration}（合計{total_sec}秒）
- スタイル: {style}
- ターゲット視聴者: {target or "一般視聴者"}
- シーン数: {num_scenes}（各シーン約{sec_per_scene}秒）{cost_note}

以下のJSON形式で動画エピソードを生成してください:
{{
  "title": "動画タイトル（日本語、35文字以内）",
  "description": "動画の概要（日本語、1-2文）",
  "scenes": [
    {{
      "title": "シーンタイトル（日本語）",
      "label": "scene_label（英数字＋アンダースコアのみ、例: intro, main_1, outro）",
      "narration": "ナレーション全文（日本語、TTSで読み上げる自然な文章、マークダウン記法は使わない）",
      "duration_seconds": {sec_per_scene},
      "image_prompt": "English AI image generation prompt (subject, style, lighting, 16:9 composition)",
      "video_prompt": "English Runway Gen-3 Alpha prompt ({sec_per_scene}s clip, motion, camera movement, visual style)"
    }}
  ]
}}

重要: scenesは必ず{num_scenes}個、JSONのみ出力（説明文不要）"""

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return json.loads(response.choices[0].message.content)


# ── Validation ───────────────────────────────────────────────────────────────

def _validate(raw: dict, num_scenes: int) -> None:
    if not isinstance(raw.get("scenes"), list) or len(raw["scenes"]) == 0:
        raise ValueError(f"OpenAI returned no scenes. Raw keys: {list(raw.keys())}")
    if len(raw["scenes"]) < 1:
        raise ValueError("OpenAI returned an empty scenes list")


# ── Episode assembly ─────────────────────────────────────────────────────────

def _build_episode(
    episode_id: str,
    raw: dict,
    target: str,
    sec_per_scene: int,
) -> dict:
    ep = em.create_new_episode(
        episode_id=episode_id,
        title=raw.get("title", ""),
        description=raw.get("description", ""),
        target_audience=target,
    )

    for scene in raw.get("scenes", []):
        em.add_section(
            ep,
            title=scene.get("title", ""),
            narration_text=scene.get("narration", ""),
            duration_seconds=int(scene.get("duration_seconds", sec_per_scene)),
            label=scene.get("label", ""),
        )
        section = ep["sections"][-1]
        section["image_prompt"] = scene.get("image_prompt", "")
        section["video_prompt"] = scene.get("video_prompt", "")

    em.update_step_status(ep, "script", "done")
    em.update_step_status(ep, "image_prompts", "done")
    em.update_step_status(ep, "video_prompts", "done")
    em.build_voice_script(ep)   # sets voice_script = "draft"
    em.build_srt(ep)            # sets subtitles = "draft"
    em.save_episode(ep)
    return ep
