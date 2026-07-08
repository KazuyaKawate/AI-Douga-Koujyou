from __future__ import annotations

from typing import Any


COMMANDER_JOB_TEMPLATES: list[dict[str, Any]] = [
    {
        "template_id": "note_article",
        "label": "note記事作成",
        "engine": "content_factory",
        "instruction": "note売上につながる有料note下書きとSEO導線を改善する",
        "priority": 85,
        "target_files": ["src/content_factory/note_builder.py", "src/revenue_engine/note_manager.py"],
    },
    {
        "template_id": "threads_post",
        "label": "Threads投稿",
        "engine": "revenue",
        "instruction": "Threads実投稿からPV取得と初クリックを改善する",
        "priority": 90,
        "target_files": ["src/business_engine/threads_automation.py", "src/revenue_engine/threads_manager.py"],
    },
    {
        "template_id": "official_site",
        "label": "Official Site改善",
        "engine": "growth",
        "instruction": "Official SiteのSEO、CTA、アフィリエイト導線を改善する",
        "priority": 80,
        "target_files": ["src/official_site/site_manager.py", "src/official_site/website_engine.py"],
    },
    {
        "template_id": "knowledge_update",
        "label": "Knowledge更新",
        "engine": "business",
        "instruction": "初収益に近いnote、Threads、SEOの成功パターンをKnowledgeへ反映する",
        "priority": 70,
        "target_files": ["src/self_builder/knowledge_manager.py", "config/self_builder_knowledge.json"],
    },
]


def list_templates() -> list[dict[str, Any]]:
    return [dict(template) for template in COMMANDER_JOB_TEMPLATES]


def get_template(template_id: str) -> dict[str, Any] | None:
    return next((dict(template) for template in COMMANDER_JOB_TEMPLATES if template["template_id"] == template_id), None)
