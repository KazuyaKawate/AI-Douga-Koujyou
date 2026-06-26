"""
PromptAgent — enhances prompts by injecting director scene directions.

For each scene in the director plan, the agent appends the director's
visual/camera/emotion guidance to the existing image and video prompt files.

Input keys:
  episode_id  str

Output keys:
  episode_id, scenes_enhanced, director_plan_used,
  image_prompts_path, video_prompts_path
"""
from __future__ import annotations

from src.agents.base_agent import BaseAgent, Task, TaskQueue


class PromptAgent(BaseAgent):
    NAME        = "PromptAgent"
    ROLE        = "プロンプトへの演出ディレクションの注入"
    ICON        = "✨"
    VERSION     = "1.0"
    NEXT_AGENTS = ["EditorAgent"]
    DESCRIPTION = "演出計画をプロンプトファイルに注入してビジュアル指示を強化します"

    def run(self, task: Task, queue: TaskQueue) -> Task:
        from src.utils.config import PROJECT_ROOT
        from src.pipeline.script_pipeline import get_image_prompts_path, get_video_prompts_path
        from src.director.director_planner import load_director_plan, plan_exists

        inp        = task.input
        episode_id = inp.get("episode_id", "")
        ep_dir     = PROJECT_ROOT / "project" / episode_id

        if not ep_dir.exists():
            return queue.fail(task.id, f"エピソードフォルダが存在しません: {episode_id}")

        queue.update(task.id, progress=0.2)

        img_path = get_image_prompts_path(ep_dir)
        vid_path = get_video_prompts_path(ep_dir)

        scenes_enhanced = 0
        plan_used       = False

        if plan_exists(ep_dir):
            plan   = load_director_plan(ep_dir)
            scenes = plan.get("scenes", []) if plan else []
            if scenes and (img_path or vid_path):
                lines: list[str] = []
                for sc in scenes:
                    sn  = sc.get("scene_no", "?")
                    cam = sc.get("camera_angle", "")
                    mot = sc.get("camera_motion", "")
                    emo = sc.get("emotion_hint", "")
                    lit = sc.get("lighting_hint", "")
                    note = sc.get("prompt_note", "")
                    parts = [p for p in [cam, mot, emo, lit, note] if p]
                    if parts:
                        lines.append(f"[Scene {sn} director] {', '.join(parts)}")
                        scenes_enhanced += 1

                inject_text = "\n\n[Director Notes — injected by PromptAgent]\n" + "\n".join(lines) + "\n"

                for fpath in [img_path, vid_path]:
                    if fpath and fpath.exists():
                        try:
                            existing = fpath.read_text(encoding="utf-8")
                            # Only inject once (check sentinel)
                            if "[Director Notes — injected by PromptAgent]" not in existing:
                                fpath.write_text(existing + inject_text, encoding="utf-8")
                        except Exception:
                            pass

                plan_used = True

        output = {
            "episode_id":         episode_id,
            "scenes_enhanced":    scenes_enhanced,
            "director_plan_used": plan_used,
            "image_prompts_path": str(img_path) if img_path else "",
            "video_prompts_path": str(vid_path) if vid_path else "",
        }
        queue.complete(task.id, output)

        for next_name in self._next_agents:
            queue.create(
                agent       = next_name,
                input_data  = {"episode_id": episode_id},
                pipeline_id = task.pipeline_id,
                depends_on  = [task.id],
                label       = f"{next_name} — {episode_id}",
            )

        return queue.get(task.id)
