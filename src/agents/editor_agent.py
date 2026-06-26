"""
EditorAgent — validates production assets and creates the export package.

Input keys:
  episode_id  str

Output keys:
  episode_id, export_created, stages_completed,
  production_ready, report_path
"""
from __future__ import annotations

from src.agents.base_agent import BaseAgent, Task, TaskQueue


class EditorAgent(BaseAgent):
    NAME        = "EditorAgent"
    ROLE        = "制作素材のバリデーションとエクスポートパッケージ作成"
    ICON        = "✂️"
    VERSION     = "1.0"
    NEXT_AGENTS = ["PublisherAgent"]
    DESCRIPTION = "制作チェックリストを確認しエクスポートパッケージを自動生成します"

    def run(self, task: Task, queue: TaskQueue) -> Task:
        from src.utils.config import PROJECT_ROOT
        from src.pipeline.export_pipeline import (
            create_export_package,
            load_production_state,
            is_production_ready,
            get_completion_pct,
        )
        from src.pipeline.script_pipeline import load_episode_data

        inp        = task.input
        episode_id = inp.get("episode_id", "")
        ep_dir     = PROJECT_ROOT / "project" / episode_id

        if not ep_dir.exists():
            return queue.fail(task.id, f"エピソードフォルダが存在しません: {episode_id}")

        ep_data    = load_episode_data(ep_dir)
        prod_state = load_production_state(ep_dir)
        queue.update(task.id, progress=0.3)

        report_path = ""
        export_ok   = False
        try:
            report = create_export_package(
                episode_dir      = ep_dir,
                production_state = prod_state,
                episode_data     = ep_data or {},
            )
            rp = ep_dir / "export" / "production_report.json"
            report_path = str(rp) if rp.exists() else ""
            export_ok   = True
        except Exception as exc:
            # Export failure is non-fatal — report it and continue
            report_path = f"エラー: {exc}"

        pct   = get_completion_pct(prod_state)
        ready = is_production_ready(prod_state)

        output = {
            "episode_id":       episode_id,
            "export_created":   export_ok,
            "stages_completed": f"{int(pct * 100)}%",
            "production_ready": ready,
            "report_path":      report_path,
        }
        queue.complete(task.id, output)

        for next_name in self._next_agents:
            queue.create(
                agent       = next_name,
                input_data  = {"episode_id": episode_id, "export_ready": export_ok},
                pipeline_id = task.pipeline_id,
                depends_on  = [task.id],
                label       = f"{next_name} — {episode_id}",
            )

        return queue.get(task.id)
