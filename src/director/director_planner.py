"""Director planner — load/save director plans and AI-assisted generation."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.director.director_schema import (
    CAMERA_ANGLE_OPTIONS,
    CAMERA_MOTION_OPTIONS,
    VISUAL_STYLE_OPTIONS,
    make_empty_plan,
    make_empty_scene_direction,
)

PLAN_FILENAME = "director_plan.json"


def plan_path(episode_dir: Path) -> Path:
    return episode_dir / PLAN_FILENAME


def plan_exists(episode_dir: Path) -> bool:
    return (episode_dir / PLAN_FILENAME).exists()


def load_director_plan(episode_dir: Path) -> dict | None:
    p = plan_path(episode_dir)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def save_director_plan(episode_dir: Path, plan: dict) -> None:
    plan["updated_at"] = datetime.now().isoformat()
    plan_path(episode_dir).write_text(
        json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def duplicate_director_plan(episode_dir: Path, new_episode_dir: Path) -> dict | None:
    """Copy a director plan to a different episode directory."""
    plan = load_director_plan(episode_dir)
    if plan is None:
        return None
    plan = dict(plan)
    plan["episode_id"]  = new_episode_dir.name
    plan["created_at"]  = datetime.now().isoformat()
    plan["updated_at"]  = datetime.now().isoformat()
    save_director_plan(new_episode_dir, plan)
    return plan


def generate_plan_with_ai(
    episode_dir: Path,
    episode_data: dict,
    character: dict | None = None,
    background: dict | None = None,
    template: dict | None = None,
    overall_tone: str = "",
    visual_style: str = "",
    pacing: str = "moderate",
    target_emotion: str = "",
) -> dict:
    """Generate a director plan using OpenAI text generation only."""
    from src.utils.settings_manager import load_settings
    from src.utils.config import OPENAI_API_KEY

    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API キーが未設定です。.env に OPENAI_API_KEY を設定してください。")

    import openai

    settings = load_settings()
    ai_cfg   = settings["ai"]
    client   = openai.OpenAI(api_key=OPENAI_API_KEY)

    sections  = episode_data.get("sections", [])
    ep_title  = episode_data.get("title", "")
    ep_desc   = episode_data.get("description", "")

    # Build context blocks
    char_note = ""
    if character:
        b = character.get("basic", {})
        a = character.get("appearance", {})
        p = character.get("personality", {})
        char_note = (
            f"キャラクター: {b.get('display_name','')} / 役割: {b.get('role','')}\n"
            f"外見: {a.get('hairstyle','')} / {a.get('clothing','')}\n"
            f"性格: {p.get('personality','')} / 話し方: {p.get('speaking_style','')}"
        )

    bg_note = ""
    if background:
        b   = background.get("basic", {})
        v   = background.get("visual", {})
        cam = background.get("camera", {})
        bg_note = (
            f"背景: {b.get('display_name','')} ({b.get('category','')})\n"
            f"ロケーション: {v.get('location_type','')} / 時間帯: {v.get('time_of_day','')}\n"
            f"カメラ: {cam.get('default_camera_angle','')} / {cam.get('default_motion','')}"
        )

    scenes_desc = "\n".join(
        f"シーン{s.get('id', i + 1)}: 【{s.get('title', '')}】 {s.get('narration_text', '')[:120]}"
        for i, s in enumerate(sections)
    )

    constraints_parts = []
    if overall_tone:
        constraints_parts.append(f"全体トーン: {overall_tone}")
    if visual_style:
        constraints_parts.append(f"ビジュアルスタイル: {visual_style}")
    if pacing:
        constraints_parts.append(f"ペーシング: {pacing}")
    if target_emotion:
        constraints_parts.append(f"目標感情: {target_emotion}")
    constraint_text = "\n".join(constraints_parts) or "（制約なし — 自由に設計してください）"

    n_scenes = len(sections)

    sys_prompt = (
        "あなたは動画制作の熟練AIディレクターです。"
        "以下のエピソード情報をもとに、シーンごとの演出計画を作成してください。"
        "必ず有効なJSONのみを返してください。説明文、マークダウン、コードブロック記法は不要です。"
    )

    user_prompt = f"""エピソードタイトル: {ep_title}
概要: {ep_desc[:200]}

シーン構成:
{scenes_desc}

演出制約:
{constraint_text}

{char_note}
{bg_note}

以下のJSON形式で演出計画を作成してください（キー名を完全に守ること）:
{{
  "overall_tone": "...",
  "target_emotion": "...",
  "visual_style": "...",
  "pacing": "...",
  "thumbnail_direction": "...",
  "bgm_direction": "...",
  "se_direction": "...",
  "risk_notes": "...",
  "scenes": [
    {{
      "scene_no": 1,
      "scene_goal": "...",
      "emotion": "...",
      "camera_angle": "...",
      "camera_motion": "...",
      "framing": "...",
      "lighting": "...",
      "image_prompt_direction": "...",
      "video_prompt_direction": "...",
      "voice_direction": "...",
      "editing_notes": "..."
    }}
  ]
}}

scenes 配列は {n_scenes} 要素にしてください。すべてのフィールドを日本語で記入してください。
camera_angle は次のいずれかにしてください: {', '.join(CAMERA_ANGLE_OPTIONS)}
camera_motion は次のいずれかにしてください: {', '.join(CAMERA_MOTION_OPTIONS)}"""

    model = ai_cfg.get("model", "gpt-4o-mini")
    resp  = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=4000,
    )

    raw = resp.choices[0].message.content.strip()
    # Strip markdown code block if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        end   = -1 if lines[-1].strip() == "```" else len(lines)
        raw   = "\n".join(lines[1:end])

    ai_result = json.loads(raw)

    # Build full plan merging AI result into empty template
    plan = make_empty_plan(episode_dir.name, episode_data)

    plan["overall_tone"]        = ai_result.get("overall_tone", "")
    plan["target_emotion"]      = ai_result.get("target_emotion", "")
    plan["visual_style"]        = ai_result.get("visual_style", VISUAL_STYLE_OPTIONS[0])
    plan["pacing"]              = ai_result.get("pacing", "moderate")
    plan["thumbnail_direction"] = ai_result.get("thumbnail_direction", "")
    plan["bgm_direction"]       = ai_result.get("bgm_direction", "")
    plan["se_direction"]        = ai_result.get("se_direction", "")
    plan["risk_notes"]          = ai_result.get("risk_notes", "")

    if character:
        plan["recommended_character_id"] = character.get("id")
    if background:
        plan["recommended_background_id"] = background.get("id")

    ai_scenes = ai_result.get("scenes", [])
    merged_scenes: list[dict] = []
    for i, section in enumerate(sections):
        sd = make_empty_scene_direction(i + 1)
        if i < len(ai_scenes):
            ai_s = ai_scenes[i]
            # Validate enum fields
            ca = ai_s.get("camera_angle", "")
            cm = ai_s.get("camera_motion", "")
            sd.update({
                "scene_goal":             ai_s.get("scene_goal", ""),
                "emotion":                ai_s.get("emotion", ""),
                "camera_angle":           ca if ca in CAMERA_ANGLE_OPTIONS else CAMERA_ANGLE_OPTIONS[0],
                "camera_motion":          cm if cm in CAMERA_MOTION_OPTIONS else CAMERA_MOTION_OPTIONS[0],
                "framing":                ai_s.get("framing", ""),
                "lighting":               ai_s.get("lighting", ""),
                "image_prompt_direction": ai_s.get("image_prompt_direction", ""),
                "video_prompt_direction": ai_s.get("video_prompt_direction", ""),
                "voice_direction":        ai_s.get("voice_direction", ""),
                "editing_notes":          ai_s.get("editing_notes", ""),
            })
        if character:
            sd["character_id"] = character.get("id")
        if background:
            sd["background_id"] = background.get("id")
        merged_scenes.append(sd)

    plan["scenes"] = merged_scenes
    return plan
