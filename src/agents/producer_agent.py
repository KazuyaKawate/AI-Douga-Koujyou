"""
ProducerAgent — generates a complete episode (script + prompts + SRT)
using the existing AI pipeline (OpenAI text only).

Input keys:
  episode_id        str   — target episode ID (e.g. "EP01")
  topic             str   — video topic / title
  duration          str   — "1分" / "2分" / "3分" / "5分" / "10分"
  style             str   — 解説・教育 / エンタメ / etc.
  target            str   — target audience (optional)
  num_scenes        int   — number of scenes (default 3)
  cost_saving       bool  — reduce OpenAI tokens (default False)
  character_id      str   — config/characters.json character id (optional)
  background_id     str   — config/backgrounds.json background id (optional)
  template_id       str   — config/prompt_templates.json template id (optional)

Output keys:
  episode_id, title, scene_count, files_created
"""
from __future__ import annotations

from src.agents.base_agent import BaseAgent, Task, TaskQueue, TASK_RUNNING


class ProducerAgent(BaseAgent):
    NAME        = "ProducerAgent"
    ROLE        = "エピソード全体の企画・生成を担当"
    ICON        = "🎬"
    VERSION     = "1.0"
    NEXT_AGENTS = ["DirectorAgent"]
    DESCRIPTION = "テーマ・設定からエピソード全体（台本・プロンプト・字幕）をAI生成します"

    def run(self, task: Task, queue: TaskQueue) -> Task:
        from src.core.ai_pipeline import generate_episode_ai
        from src.utils.config import PROJECT_ROOT

        inp        = task.input
        episode_id = inp.get("episode_id", "EP01")
        topic      = inp.get("topic", "")
        if not topic:
            return queue.fail(task.id, "topic が未入力です")

        # Optionally load character / background / template dicts
        character  = _load_record("characters.json",       "characters",  inp.get("character_id"))
        background = _load_record("backgrounds.json",      "backgrounds", inp.get("background_id"))
        template   = _load_record("prompt_templates.json", "templates",   inp.get("template_id"))

        queue.update(task.id, progress=0.2)

        try:
            ep, written = generate_episode_ai(
                topic           = topic,
                episode_id      = episode_id,
                duration        = inp.get("duration",   "3分"),
                style           = inp.get("style",      "解説・教育"),
                target          = inp.get("target",     ""),
                num_scenes      = int(inp.get("num_scenes",  3)),
                cost_saving     = bool(inp.get("cost_saving", False)),
                character       = character,
                background      = background,
                prompt_template = template,
            )
        except Exception as exc:
            return queue.fail(task.id, f"generate_episode_ai 失敗: {exc}")

        output = {
            "episode_id":   episode_id,
            "title":        ep.get("title", ""),
            "scene_count":  len(ep.get("sections", [])),
            "files_created": list(written.keys()) if isinstance(written, dict) else [],
        }
        queue.complete(task.id, output)

        # ── Create next task ───────────────────────────────────────────────────
        for next_name in self._next_agents:
            queue.create(
                agent       = next_name,
                input_data  = {
                    "episode_id":   episode_id,
                    "overall_tone": inp.get("overall_tone", "educational"),
                    "visual_style": inp.get("visual_style", "cinematic"),
                    "pacing":       inp.get("pacing",       "moderate"),
                    "target_emotion": inp.get("target_emotion", ""),
                },
                pipeline_id = task.pipeline_id,
                depends_on  = [task.id],
                label       = f"{next_name} — {episode_id}",
            )

        return queue.get(task.id)


# ── Helper ────────────────────────────────────────────────────────────────────

def _load_record(cfg_file: str, list_key: str, record_id: str | None) -> dict | None:
    if not record_id:
        return None
    import json
    from src.utils.config import PROJECT_ROOT
    p = PROJECT_ROOT / "config" / cfg_file
    if not p.exists():
        return None
    try:
        records = json.loads(p.read_text(encoding="utf-8")).get(list_key, [])
        return next((r for r in records if r.get("id") == record_id), None)
    except Exception:
        return None
