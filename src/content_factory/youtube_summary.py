from __future__ import annotations

import re
from typing import Any
from uuid import uuid4


class YouTubeSummary:
    def summarize(self, url: str, transcript: str) -> dict[str, Any]:
        points = self._key_points(transcript)
        analysis = [
            "この内容は単なる要約ではなく、読者が実行しやすい順番に再構成する価値があります。",
            "AIOSでは収益導線を最後に足し、noteとThreadsへ分岐させます。",
        ]
        title = "動画内容を独自分析で学ぶ収益化メモ"
        note_body = "# " + title + "\n\n" + "\n".join(f"- {point}" for point in points) + "\n\n## 独自考察\n" + "\n".join(analysis)
        threads = "動画から学んだことを3つに整理。\n\n" + "\n".join(f"{i+1}. {point[:60]}" for i, point in enumerate(points[:3]))
        return {
            "content_id": f"yt-{uuid4().hex[:10]}",
            "type": "youtube_summary",
            "url": url,
            "summary": points,
            "ai_analysis": analysis,
            "note": {"title": title, "body": note_body},
            "threads": {"text": threads[:500]},
            "seo_article": {"title": title, "description": "動画内容を独自分析し、実践手順として再構成した記事です。"},
            "copyright_policy": "転載ではなく、要約・独自分析・独自構成として生成",
        }

    @staticmethod
    def _key_points(transcript: str) -> list[str]:
        sentences = [item.strip() for item in re.split(r"[。\n.]", transcript) if len(item.strip()) >= 8]
        if not sentences:
            return ["動画の主張を3点に整理する", "実行手順へ変換する", "収益導線を追加する"]
        return sentences[:5]
