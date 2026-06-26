"""
PublisherAgent — final pipeline stage; generates a publish checklist.

No external APIs are called.  This agent produces a publish_report.json
under project/EPXX/export/ that lists everything needed before publishing.

In a future release this agent will:
  - Upload to YouTube / Vimeo via their APIs.
  - Post metadata to social platforms.
  - Trigger a CDN cache purge.

Input keys:
  episode_id   str
  platform     str  — "YouTube" / "Vimeo" / "TikTok" / etc. (optional)
  notes        str  — freeform publisher notes (optional)
  export_ready bool — propagated from EditorAgent

Output keys:
  episode_id, checklist_items, checklist_passed, publish_report_path
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.agents.base_agent import BaseAgent, Task, TaskQueue


class PublisherAgent(BaseAgent):
    NAME        = "PublisherAgent"
    ROLE        = "公開準備チェックリストの生成（プレースホルダー）"
    ICON        = "📡"
    VERSION     = "1.0"
    NEXT_AGENTS = []          # End of pipeline
    DESCRIPTION = "公開前チェックリストを生成します。将来のバージョンで外部プラットフォームと連携予定"

    def run(self, task: Task, queue: TaskQueue) -> Task:
        from src.utils.config import PROJECT_ROOT
        from src.pipeline.script_pipeline import load_episode_data
        from src.director.director_planner import plan_exists
        from src.pipeline.export_pipeline import load_production_report

        inp        = task.input
        episode_id = inp.get("episode_id", "")
        ep_dir     = PROJECT_ROOT / "project" / episode_id

        if not ep_dir.exists():
            return queue.fail(task.id, f"エピソードフォルダが存在しません: {episode_id}")

        queue.update(task.id, progress=0.2)

        ep_data = load_episode_data(ep_dir)
        report  = load_production_report(ep_dir)

        checklist = [
            {"item": "episode.json 存在",        "ok": ep_data is not None},
            {"item": "export パッケージ作成済",  "ok": report  is not None},
            {"item": "演出計画 (director) 存在", "ok": plan_exists(ep_dir)},
            {"item": "export_ready フラグ",      "ok": bool(inp.get("export_ready", False))},
            {"item": "タイトル設定済",           "ok": bool(ep_data.get("title", "") if ep_data else "")},
            # FUTURE: thumbnail uploaded, captions available, metadata filled
        ]

        all_passed = all(c["ok"] for c in checklist)

        publish_report = {
            "episode_id":    episode_id,
            "platform":      inp.get("platform", "(未設定)"),
            "notes":         inp.get("notes", ""),
            "checklist":     checklist,
            "all_passed":    all_passed,
            "generated_at":  datetime.now().isoformat(),
            "agent_version": self.VERSION,
            # FUTURE: upload_url, publish_status, cdn_url
        }

        export_dir = ep_dir / "export"
        export_dir.mkdir(parents=True, exist_ok=True)
        rp = export_dir / "publish_report.json"
        rp.write_text(json.dumps(publish_report, ensure_ascii=False, indent=2), encoding="utf-8")

        output = {
            "episode_id":         episode_id,
            "checklist_items":    len(checklist),
            "checklist_passed":   all_passed,
            "publish_report_path": str(rp),
        }
        queue.complete(task.id, output)

        # No next agent — pipeline ends here
        return queue.get(task.id)
