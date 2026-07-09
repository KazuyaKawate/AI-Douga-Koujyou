from __future__ import annotations

from typing import Any
from uuid import uuid4


class LandingPageBuilder:
    def build(self, offer: str) -> dict[str, Any]:
        return {
            "content_id": f"lp-{uuid4().hex[:10]}",
            "type": "landing_page",
            "offer": offer,
            "hero": {"headline": offer, "subcopy": "小さく始めて、収益化までの手戻りを減らします。"},
            "cta": "今日の1本を作る",
            "faq": [
                {"q": "初心者でも使えますか？", "a": "最初の投稿から順番に進められる構成です。"},
                {"q": "費用はかかりますか？", "a": "無料運用から始め、反応が出た部分だけ伸ばします。"},
            ],
            "pricing": [{"plan": "Starter", "price": 0}, {"plan": "Pro", "price": 980}],
            "case_studies": ["Threads投稿からnoteへ誘導", "比較記事からAffiliateへ誘導"],
            "comparison": ["生成速度", "SEO", "CTA", "分析"],
        }
