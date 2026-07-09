from __future__ import annotations

from typing import Any


class ImagePromptBuilder:
    def build(self, content: dict[str, Any]) -> dict[str, Any]:
        title = content.get("title") or content.get("topic") or content.get("offer") or "AIOS content"
        base = f"Clean Japanese digital editorial image about {title}, clear subject, readable composition"
        return {
            "article_image": base + ", 16:9, article eyecatch",
            "threads_image": base + ", square social post, bold focal point",
            "thumbnail": base + ", YouTube thumbnail style, high contrast",
            "ogp_image": base + ", web OGP banner, professional",
        }
