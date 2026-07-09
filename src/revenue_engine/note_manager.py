from __future__ import annotations

from typing import Any


class NoteManager:
    def queue(self, opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "title": item.get("title", ""),
                "article_angle": item.get("next_action", ""),
                "expected_profit": item.get("expected_profit", 0),
                "roi": item.get("roi", 0),
            }
            for item in opportunities
            if item.get("channel") == "note"
        ]
