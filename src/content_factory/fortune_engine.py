from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4


SIGNS = ["牡羊座", "牡牛座", "双子座", "蟹座", "獅子座", "乙女座", "天秤座", "蠍座", "射手座", "山羊座", "水瓶座", "魚座"]
COLORS = ["青", "白", "緑", "金", "紫", "赤"]
ITEMS = ["ノート", "マグカップ", "イヤホン", "ハンカチ", "ペン", "本"]


class FortuneEngine:
    def daily(self, seed: int | None = None) -> dict[str, Any]:
        base = seed if seed is not None else date.today().toordinal()
        ranking = []
        for index, sign in enumerate(SIGNS):
            score = ((base + index * 7) % 100) + 1
            ranking.append(
                {
                    "rank": 0,
                    "sign": sign,
                    "score": score,
                    "blood_type_hint": ["A型", "B型", "O型", "AB型"][(base + index) % 4],
                    "tarot": ["太陽", "星", "力", "節制", "恋人", "運命の輪"][(base + index) % 6],
                    "lucky_color": COLORS[(base + index) % len(COLORS)],
                    "lucky_item": ITEMS[(base + index) % len(ITEMS)],
                    "message": f"{sign}は小さな発信が収益導線につながる日です。",
                }
            )
        ranked = sorted(ranking, key=lambda item: item["score"], reverse=True)
        for rank, item in enumerate(ranked, start=1):
            item["rank"] = rank
        return {
            "content_id": f"fortune-{uuid4().hex[:10]}",
            "type": "fortune",
            "date": date.today().isoformat(),
            "daily_ranking": ranked,
            "weekly": "今週は発信頻度を増やすほど反応が蓄積します。",
            "monthly": "今月は継続テーマを決めてシリーズ化すると伸びます。",
        }
