"""MarketplaceProvider — Agent Marketplace API クライアント。

将来 https://store.ap-aios.com から取得できるよう Provider のみ実装。
通信部分は Mock で構築済み。実 API が完成次第 _fetch() を置き換えるだけで動く。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# 将来の実 API URL
_BASE_URL = "https://store.ap-aios.com/api/v1"

# Mock カタログ — 将来 API レスポンスと同じ形式
_MOCK_CATALOG: list[dict] = [
    {
        "package_id":  "writing_specialist_pkg",
        "name":        "Writing Specialist",
        "version":     "1.2.0",
        "author":      "AIOS Official",
        "description": "高品質な日本語コンテンツを生成する記事執筆専門 Agent。SEO 意識・読者ファーストの文章を得意とする。",
        "tags":        ["writing", "seo", "japanese", "content"],
        "downloads":   4820,
        "rating":      4.8,
        "price":       "free",
        "category":    "Writing",
        "agent_id":    "writing_specialist",
        "workflow_name": "writing.article_draft",
    },
    {
        "package_id":  "sns_strategist_pkg",
        "name":        "SNS Strategist",
        "version":     "1.1.0",
        "author":      "AIOS Official",
        "description": "SNS 戦略全体を設計するストラテジスト。プラットフォームの特性・アルゴリズム・ユーザー心理を熟知する。",
        "tags":        ["sns", "strategy", "marketing", "social"],
        "downloads":   3210,
        "rating":      4.7,
        "price":       "free",
        "category":    "Marketing",
        "agent_id":    "sns_strategist",
    },
    {
        "package_id":  "research_analyst_pkg",
        "name":        "Research Analyst",
        "version":     "1.0.0",
        "author":      "AIOS Official",
        "description": "データと事実に基づく調査・分析を行うリサーチ専門 Agent。ビジネスインテリジェンスに強い。",
        "tags":        ["research", "analysis", "business", "strategy"],
        "downloads":   2890,
        "rating":      4.9,
        "price":       "free",
        "category":    "Analysis",
        "agent_id":    "research_analyst",
    },
    {
        "package_id":  "video_director_pkg",
        "name":        "Video Director",
        "version":     "1.0.0",
        "author":      "AIOS Official",
        "description": "動画コンテンツの企画・演出・台本制作を担当するディレクター Agent。視聴者を引き込む構成が得意。",
        "tags":        ["video", "direction", "script", "production"],
        "downloads":   1540,
        "rating":      4.6,
        "price":       "free",
        "category":    "Video",
        "agent_id":    "video_director",
    },
    {
        "package_id":  "fortune_teller_pkg",
        "name":        "Fortune Teller",
        "version":     "1.0.0",
        "author":      "AIOS Official",
        "description": "占い・運勢コンテンツを生成する専門 Agent。読者に希望と励ましを届けることを使命とする。",
        "tags":        ["fortune", "zodiac", "tarot", "lifestyle"],
        "downloads":   980,
        "rating":      4.5,
        "price":       "free",
        "category":    "Lifestyle",
        "agent_id":    "fortune_teller",
    },
    {
        "package_id":  "hashtag_generator_pkg",
        "name":        "Hashtag Generator Pro",
        "version":     "2.0.0",
        "author":      "AIOS Official",
        "description": "リーチを最大化するハッシュタグ戦略の専門家。大・中・小規模タグを組み合わせて最適セットを生成。",
        "tags":        ["hashtag", "instagram", "tiktok", "reach"],
        "downloads":   6100,
        "rating":      4.9,
        "price":       "free",
        "category":    "Marketing",
        "agent_id":    "hashtag_generator",
    },
    {
        "package_id":  "legal_reviewer_pkg",
        "name":        "Legal Document Reviewer",
        "version":     "1.0.0",
        "author":      "Partner Studio",
        "description": "契約書・規約・利用規約をレビューし、リスク箇所を特定する法務 Agent。",
        "tags":        ["legal", "contract", "review", "risk"],
        "downloads":   430,
        "rating":      4.3,
        "price":       "¥1,980/月",
        "category":    "Legal",
        "agent_id":    "legal_reviewer",
    },
    {
        "package_id":  "email_writer_pkg",
        "name":        "Business Email Writer",
        "version":     "1.1.0",
        "author":      "Partner Studio",
        "description": "ビジネスメールの下書き・返信・フォローアップを自動生成するメール特化 Agent。",
        "tags":        ["email", "business", "communication", "writing"],
        "downloads":   2100,
        "rating":      4.4,
        "price":       "free",
        "category":    "Business",
        "agent_id":    "email_writer",
    },
]


@dataclass
class MarketplaceItem:
    """Marketplace の1パッケージ情報（GUI 表示用）。"""
    package_id:    str
    name:          str
    version:       str
    author:        str
    description:   str
    tags:          list[str]     = field(default_factory=list)
    downloads:     int           = 0
    rating:        float         = 0.0
    price:         str           = "free"
    category:      str           = "General"
    agent_id:      str           = ""
    workflow_name: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "MarketplaceItem":
        return cls(
            package_id=d["package_id"],
            name=d.get("name", ""),
            version=d.get("version", "1.0.0"),
            author=d.get("author", "unknown"),
            description=d.get("description", ""),
            tags=list(d.get("tags", [])),
            downloads=int(d.get("downloads", 0)),
            rating=float(d.get("rating", 0.0)),
            price=d.get("price", "free"),
            category=d.get("category", "General"),
            agent_id=d.get("agent_id", ""),
            workflow_name=d.get("workflow_name"),
        )

    def to_dict(self) -> dict:
        return {
            "package_id":   self.package_id,
            "name":         self.name,
            "version":      self.version,
            "author":       self.author,
            "description":  self.description,
            "tags":         self.tags,
            "downloads":    self.downloads,
            "rating":       self.rating,
            "price":        self.price,
            "category":     self.category,
            "agent_id":     self.agent_id,
            "workflow_name": self.workflow_name,
        }


class MarketplaceProvider:
    """
    Agent Marketplace API プロバイダー。

    現在は Mock 実装。将来 _fetch() を実 HTTP クライアントに差し替えることで
    https://store.ap-aios.com と通信できるようになる。

    使い方:
        mp = MarketplaceProvider()
        items = mp.search("writing")
        featured = mp.get_featured()
        categories = mp.get_categories()
        pkg_bytes = mp.download("writing_specialist_pkg")  # Mock: returns None
    """

    BASE_URL = _BASE_URL

    def __init__(self, use_mock: bool = True) -> None:
        self._use_mock = use_mock
        self._catalog  = [MarketplaceItem.from_dict(d) for d in _MOCK_CATALOG]

    # ---- Search / Browse -------------------------------------------

    def search(
        self,
        query:    str            = "",
        tags:     Optional[list[str]] = None,
        category: Optional[str]  = None,
        free_only: bool          = False,
    ) -> list[MarketplaceItem]:
        """パッケージを検索する（Mock）。"""
        results = list(self._catalog)

        if query:
            q = query.lower()
            results = [
                i for i in results
                if q in i.name.lower()
                or q in i.description.lower()
                or any(q in t for t in i.tags)
            ]

        if tags:
            results = [i for i in results if any(t in i.tags for t in tags)]

        if category:
            results = [i for i in results if i.category == category]

        if free_only:
            results = [i for i in results if i.price == "free"]

        return sorted(results, key=lambda i: i.downloads, reverse=True)

    def get_featured(self) -> list[MarketplaceItem]:
        """おすすめパッケージを返す（Mock: downloads top 3）。"""
        return sorted(self._catalog, key=lambda i: i.downloads, reverse=True)[:3]

    def get_package_info(self, package_id: str) -> Optional[MarketplaceItem]:
        """パッケージ詳細を返す（Mock）。"""
        return next((i for i in self._catalog if i.package_id == package_id), None)

    def get_categories(self) -> list[str]:
        """カテゴリ一覧を返す（Mock）。"""
        cats = sorted({i.category for i in self._catalog})
        return cats

    def get_top_by_category(self, limit: int = 3) -> dict[str, list[MarketplaceItem]]:
        """カテゴリ別トップ N を返す（GUI サイドバー用）。"""
        result: dict[str, list[MarketplaceItem]] = {}
        for cat in self.get_categories():
            items = [i for i in self._catalog if i.category == cat]
            result[cat] = sorted(items, key=lambda i: i.downloads, reverse=True)[:limit]
        return result

    # ---- Download --------------------------------------------------

    def download(
        self,
        package_id: str,
        output_dir: Path = Path("output/store"),
    ) -> Optional[Path]:
        """
        パッケージをダウンロードする。

        Mock 実装: ローカルに既にエクスポート済みの .apagent があれば返す。
        将来: _fetch(f"{self.BASE_URL}/packages/{package_id}/download") を使用。
        """
        # Mock: ローカルの出力済みファイルを探す
        item = self.get_package_info(package_id)
        if item is None:
            return None

        # data/store/packages/ から探す
        pkg_dir = Path("data/store/packages")
        for f in pkg_dir.glob(f"{package_id}*.apagent"):
            return f

        return None   # 未ダウンロード = None

    # ---- Future: real HTTP -----------------------------------------

    def _fetch(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        """
        将来の実 HTTP 実装プレースホルダー。

        Mock 実装では None を返す。
        実装例:
            import httpx
            resp = httpx.get(f"{self.BASE_URL}{endpoint}", params=params, timeout=10)
            resp.raise_for_status()
            return resp.json()
        """
        return None
