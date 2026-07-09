from __future__ import annotations

from typing import Any
from uuid import uuid4

from src.content_factory.fortune_engine import FortuneEngine


class ThreadsBuilder:
    def build(self, topic: str, *, genre: str = "fortune") -> dict[str, Any]:
        if genre == "fortune":
            fortune = FortuneEngine().daily()
            top = fortune["daily_ranking"][0]
            text = (
                f"今日の運勢1位は{top['sign']}。\n\n"
                f"ラッキーカラーは{top['lucky_color']}、アイテムは{top['lucky_item']}。\n"
                "小さく投稿して、反応が出たテーマをnote化しよう。\n\n"
                "#占い #Threads #今日の運勢"
            )
        else:
            hooks = {
                "ai_news": "今日のAIニュースで見るべきポイントは1つ。",
                "psychology": "人が思わず反応する投稿には共通点があります。",
                "trivia": "知らないと損する小ネタ。",
                "work": "仕事が軽くなる考え方。",
            }
            text = f"{hooks.get(genre, '今日の発信テーマ。')}\n\n{topic}\n\n保存してあとで試してください。\n#AIOS #収益化"
        return {
            "content_id": f"threads-{uuid4().hex[:10]}",
            "type": "threads",
            "genre": genre,
            "topic": topic,
            "text": text[:500],
            "buzz_factors": ["冒頭フック", "短文", "保存CTA", "note導線"],
            "estimated_revenue": 12000,
            "status": "draft",
        }
