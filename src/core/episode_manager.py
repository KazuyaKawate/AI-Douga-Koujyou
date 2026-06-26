from pathlib import Path
from datetime import datetime
import json
from typing import Literal

from src.utils.config import PROJECT_ROOT

SCHEMA_VERSION = "1.1"
VALID_STEPS = ("script", "image_prompts", "video_prompts", "voice_script", "subtitles")
VALID_STATUSES = ("pending", "draft", "done")


# ── Lifecycle ─────────────────────────────────────────────────────────────────

def create_new_episode(
    episode_id: str,
    title: str = "",
    description: str = "",
    target_audience: str = "",
) -> dict:
    if not episode_id:
        raise ValueError("episode_id cannot be empty")
    now = datetime.now().isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "episode_id": episode_id,
        "title": title,
        "description": description,
        "target_audience": target_audience,
        "total_duration_seconds": 0,
        "created_at": now,
        "updated_at": now,
        "steps": {step: "pending" for step in VALID_STEPS},
        "sections": [],
    }


def load_episode(episode_id: str) -> dict | None:
    path = PROJECT_ROOT / "project" / episode_id / "episode.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_episode(episode: dict) -> Path:
    recalculate_total_duration(episode)
    episode["updated_at"] = datetime.now().isoformat()
    folder = PROJECT_ROOT / "project" / episode["episode_id"]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "episode.json"
    path.write_text(json.dumps(episode, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def get_episode_list() -> list[str]:
    project_dir = PROJECT_ROOT / "project"
    if not project_dir.exists():
        return []
    return sorted(
        d.name for d in project_dir.iterdir()
        if d.is_dir() and (d / "episode.json").exists()
    )


# ── Section mutation ───────────────────────────────────────────────────────────

def add_section(
    episode: dict,
    title: str,
    narration_text: str = "",
    duration_seconds: int = 10,
    label: str = "",
) -> dict:
    existing_ids = [s["id"] for s in episode["sections"]]
    new_id = max(existing_ids, default=0) + 1
    episode["sections"].append({
        "id": new_id,
        "label": label or f"section_{new_id}",
        "title": title,
        "narration_text": narration_text,
        "image_prompt": "",
        "video_prompt": "",
        "duration_seconds": duration_seconds,
        "notes": "",
    })
    return episode


def remove_section(episode: dict, section_id: int) -> dict:
    before = len(episode["sections"])
    episode["sections"] = [s for s in episode["sections"] if s["id"] != section_id]
    if len(episode["sections"]) == before:
        raise KeyError(f"Section id {section_id} not found")
    return episode


def update_section(episode: dict, section_id: int, **fields) -> dict:
    fields.pop("id", None)
    for s in episode["sections"]:
        if s["id"] == section_id:
            s.update(fields)
            return episode
    raise KeyError(f"Section id {section_id} not found")


def recalculate_total_duration(episode: dict) -> dict:
    episode["total_duration_seconds"] = sum(
        s["duration_seconds"] for s in episode["sections"]
    )
    return episode


# ── Generation (no API calls) ──────────────────────────────────────────────────

def generate_image_prompts(
    episode: dict,
    style_suffix: str = "cinematic photography, 8K resolution, --ar 16:9",
    force: bool = False,
) -> dict:
    for s in episode["sections"]:
        if force or not s.get("image_prompt"):
            desc = s["narration_text"][:120].strip().replace("\n", " ")
            s["image_prompt"] = f"{s['title']}, {desc}. {style_suffix}"
    episode["steps"]["image_prompts"] = "draft"
    return episode


def generate_video_prompts(
    episode: dict,
    style_suffix: str = "cinematic motion, smooth camera movement, Runway Gen-3 Alpha",
    force: bool = False,
) -> dict:
    for s in episode["sections"]:
        if force or not s.get("video_prompt"):
            desc = s["narration_text"][:120].strip().replace("\n", " ")
            s["video_prompt"] = (
                f"{s['duration_seconds']}s clip, {s['title']}, {desc}. {style_suffix}"
            )
    episode["steps"]["video_prompts"] = "draft"
    return episode


def build_voice_script(episode: dict) -> str:
    lines = [
        f"# {episode['title']}",
        f"# {episode['episode_id']} — 音声台本",
        f"# 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    for i, s in enumerate(episode["sections"], 1):
        lines += [
            "---",
            f"## {i}. {s['title']}",
            f"（{s['duration_seconds']}秒）",
            "",
            s["narration_text"].strip() or "（ナレーションなし）",
            "",
        ]
    episode["steps"]["voice_script"] = "draft"
    return "\n".join(lines)


def build_srt(episode: dict) -> str:
    entries = []
    current = 0.0
    for i, s in enumerate(episode["sections"], 1):
        start = current
        end = current + s["duration_seconds"]
        text = s["narration_text"].strip() or s["title"]
        entries.append(f"{i}\n{_fmt(start)} --> {_fmt(end)}\n{_wrap(text, 40)}")
        current = end
    episode["steps"]["subtitles"] = "draft"
    return "\n\n".join(entries)


def update_step_status(
    episode: dict,
    step: str,
    status: Literal["pending", "draft", "done"],
) -> dict:
    if step not in VALID_STEPS:
        raise ValueError(f"Invalid step: {step}")
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    episode["steps"][step] = status
    return episode


# ── Export ─────────────────────────────────────────────────────────────────────

def export_episode(episode: dict) -> dict[str, Path]:
    ep_id = episode["episode_id"]
    folder = PROJECT_ROOT / "project" / ep_id
    folder.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}

    written["episode_json"] = save_episode(episode)

    steps = episode["steps"]

    if steps["voice_script"] != "pending":
        p = folder / f"{ep_id}_voice_script.txt"
        p.write_text(build_voice_script(episode), encoding="utf-8")
        written["voice_script"] = p

    if steps["image_prompts"] != "pending":
        p = folder / f"{ep_id}_image_prompts.txt"
        p.write_text(_build_prompts_txt(episode, "image_prompt", "画像プロンプト集"), encoding="utf-8")
        written["image_prompts"] = p

    if steps["video_prompts"] != "pending":
        p = folder / f"{ep_id}_video_prompts.txt"
        p.write_text(_build_prompts_txt(episode, "video_prompt", "動画プロンプト集（Runway）"), encoding="utf-8")
        written["video_prompts"] = p

    if steps["subtitles"] != "pending":
        p = folder / f"{ep_id}.srt"
        p.write_text(build_srt(episode), encoding="utf-8")
        written["subtitles"] = p

    return written


# ── Helpers ────────────────────────────────────────────────────────────────────

def _build_prompts_txt(episode: dict, field: str, heading: str) -> str:
    ep_id = episode["episode_id"]
    lines = [
        f"# {ep_id} — {heading}",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d')}",
        "",
    ]
    for s in episode["sections"]:
        lines += [
            f"## [{s['id']}] {s['label']} — {s['title']}",
            s.get(field) or "（未設定）",
            "",
        ]
    return "\n".join(lines)


def _fmt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _wrap(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    lines = []
    while len(text) > width:
        cut = max(text.rfind("　", 0, width), text.rfind(" ", 0, width))
        if cut <= 0:
            cut = width
        lines.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        lines.append(text)
    return "\n".join(lines)
