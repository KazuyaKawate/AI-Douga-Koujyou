from __future__ import annotations

from typing import Any
from uuid import uuid4


class AffiliateWriter:
    def build(self, product: str, *, audience: str = "AI活用に興味がある個人") -> dict[str, Any]:
        return {
            "content_id": f"aff-{uuid4().hex[:10]}",
            "type": "affiliate",
            "product": product,
            "audience": audience,
            "headline": f"{product}は{audience}に向いている？",
            "body": f"{product}の特徴、向いている人、注意点を比較し、必要な人だけが選べる構成にします。",
            "cta": f"{product}を試す前に、無料プランと解約条件を確認してください。",
            "compliance": {"no_false_claims": True, "disclosure_required": True},
            "estimated_revenue": 16000,
        }
