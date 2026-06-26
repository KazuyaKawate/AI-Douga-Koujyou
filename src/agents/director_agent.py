"""
DirectorAgent — generates an AI director plan for an episode.

Input keys:
  episode_id      str  — must exist under project/
  overall_tone    str  — e.g. "educational"
  visual_style    str  — e.g. "cinematic"
  pacing          str  — slow / moderate / fast / varied
  target_emotion  str  — optional

Output keys:
  episode_id, plan_created, scene_count, updated_at
"""
from __future__ import annotations

from src.agents.base_agent import BaseAgent, Task, TaskQueue


class DirectorAgent(BaseAgent):
    NAME        = "DirectorAgent"
    ROLE        = "シーンごとの演出計画を設計するディレクター"
    ICON        = "🎭"
    VERSION     = "1.0"
    NEXT_AGENTS = ["ScriptAgent"]
    DESCRIPTION = "エピソードの演出プラン（カメラ・感情・トーン）をAI生成します"

    def run(self, task: Task, queue: TaskQueue) -> Task:
        from pathlib import Path
        from src.utils.config import PROJECT_ROOT
        from src.director.director_planner import (
            generate_plan_with_ai,
            load_director_plan,
            plan_exists,
            save_director_plan,
        )
        from src.pipeline.script_pipeline import load_episode_data

        inp        = task.input
        episode_id = inp.get("episode_id", "")
        ep_dir     = PROJECT_ROOT / "project" / episode_id

        if not ep_dir.exists():
            return queue.fail(task.id, f"エピソードフォルダが存在しません: {episode_id}")

        ep_data = load_episode_data(ep_dir)
        if not ep_data:
            return queue.fail(task.id, f"episode.json が見つかりません: {episode_id}")

        queue.update(task.id, progress=0.2)

        try:
            plan = generate_plan_with_ai(
                episode_dir   = ep_dir,
                episode_data  = ep_data,
                overall_tone  = inp.get("overall_tone",    "educational"),
                visual_style  = inp.get("visual_style",    "cinematic"),
                pacing        = inp.get("pacing",          "moderate"),
                target_emotion = inp.get("target_emotion", ""),
            )
        except Exception as exc:
            return queue.fail(task.id, f"generate_plan_with_ai 失敗: {exc}")

        output = {
            "episode_id":  episode_id,
            "plan_created": True,
            "scene_count":  len(plan.get("scenes", [])),
            "updated_at":   plan.get("updated_at", ""),
        }
        queue.complete(task.id, output)

        # Create next task
        for next_name in self._next_agents:
            queue.create(
                agent       = next_name,
                input_data  = {"episode_id": episode_id},
                pipeline_id = task.pipeline_id,
                depends_on  = [task.id],
                label       = f"{next_name} — {episode_id}",
            )

        return queue.get(task.id)
