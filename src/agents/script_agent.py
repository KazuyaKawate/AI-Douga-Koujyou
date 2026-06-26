"""
ScriptAgent — validates and reports on the episode script.

Does not regenerate the script (ProducerAgent already did that).
Validates that all required files exist and reports their contents.

Input keys:
  episode_id  str

Output keys:
  episode_id, title, scene_count, has_voice_script, has_srt,
  has_image_prompts, has_video_prompts, validation_passed
"""
from __future__ import annotations

from src.agents.base_agent import BaseAgent, Task, TaskQueue


class ScriptAgent(BaseAgent):
    NAME        = "ScriptAgent"
    ROLE        = "台本・プロンプトファイルを検証・整理"
    ICON        = "📝"
    VERSION     = "1.0"
    NEXT_AGENTS = ["PromptAgent"]
    DESCRIPTION = "生成済みの台本・プロンプトファイルを検証し、次のエージェントに引き継ぎます"

    def run(self, task: Task, queue: TaskQueue) -> Task:
        from src.utils.config import PROJECT_ROOT
        from src.pipeline.script_pipeline import (
            validate_script,
            load_episode_data,
            get_voice_script_path,
            get_srt_path,
            get_image_prompts_path,
            get_video_prompts_path,
        )

        inp        = task.input
        episode_id = inp.get("episode_id", "")
        ep_dir     = PROJECT_ROOT / "project" / episode_id

        if not ep_dir.exists():
            return queue.fail(task.id, f"エピソードフォルダが存在しません: {episode_id}")

        ep_data = load_episode_data(ep_dir)
        if not ep_data:
            return queue.fail(task.id, f"episode.json が見つかりません: {episode_id}")

        queue.update(task.id, progress=0.3)

        validation = validate_script(ep_dir)
        has_voice   = get_voice_script_path(ep_dir) is not None
        has_srt     = get_srt_path(ep_dir) is not None
        has_img_p   = get_image_prompts_path(ep_dir) is not None
        has_vid_p   = get_video_prompts_path(ep_dir) is not None
        passed      = has_voice and has_img_p

        output = {
            "episode_id":         episode_id,
            "title":              ep_data.get("title", ""),
            "scene_count":        len(ep_data.get("sections", [])),
            "has_voice_script":   has_voice,
            "has_srt":            has_srt,
            "has_image_prompts":  has_img_p,
            "has_video_prompts":  has_vid_p,
            "validation_passed":  passed,
            "validation_detail":  validation,
        }

        if not passed:
            return queue.fail(task.id, "必須ファイルが不足しています（台本または画像プロンプト）")

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
