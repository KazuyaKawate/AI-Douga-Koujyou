from __future__ import annotations

from typing import Any
from uuid import uuid4


TEMPLATES = {
    "seo": ["検索意図", "結論", "具体手順", "失敗例", "FAQ"],
    "comparison": ["比較軸", "おすすめ順", "価格", "向いている人", "結論"],
    "review": ["使った背景", "良かった点", "注意点", "収益化への使い方", "CTA"],
    "ai_explainer": ["何ができるか", "仕組み", "活用例", "リスク", "始め方"],
    "ranking": ["評価基準", "ランキング", "選び方", "よくある質問", "CTA"],
}


class NoteBuilder:
    def build(self, topic: str, *, template: str = "seo", keywords: list[str] | None = None) -> dict[str, Any]:
        selected = TEMPLATES.get(template, TEMPLATES["seo"])
        keywords = keywords or [topic, "AI", "収益化"]
        title = f"【保存版】{topic}で初収益を狙う方法"
        sections = [
            {"heading": f"H2: {heading}", "body": f"{topic}について、{heading}を読者がすぐ実行できる形で解説します。"}
            for heading in selected
        ]
        cta = self.cta(topic)
        body = "\n\n".join([f"## {item['heading'].replace('H2: ', '')}\n{item['body']}" for item in sections])
        return {
            "content_id": f"note-{uuid4().hex[:10]}",
            "type": "note",
            "template": template,
            "topic": topic,
            "title": title,
            "keywords": keywords,
            "description": f"{topic}の始め方、比較、注意点、収益導線を解説します。",
            "sections": sections,
            "body": f"# {title}\n\n{body}\n\n{cta}",
            "cta": cta,
            "estimated_revenue": 18000,
            "status": "draft",
        }

    @staticmethod
    def cta(topic: str) -> str:
        return f"{topic}を今日から試したい人は、まず無料テンプレートで1本作って反応を見てください。"
