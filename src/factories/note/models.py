"""Note Factory データモデル定義。"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
import json


class ArticleStatus(str, Enum):
    """記事のライフサイクル状態。"""
    IDEA      = "idea"       # アイデア生成済み
    PLANNED   = "planned"    # 構成計画完了
    DRAFT     = "draft"      # 執筆完了（ドラフト）
    REVIEWED  = "reviewed"   # レビュー完了
    APPROVED  = "approved"   # 人間承認済み
    PUBLISHED = "published"  # 公開済み（draft.md出力済み）
    ANALYZED  = "analyzed"   # 統計更新済み


@dataclass
class NotePlan:
    """記事の構成計画。"""
    topic:             str
    category:          str
    tags:              list[str]
    target_audience:   str
    seo_keywords:      list[str]
    monetization_path: str        # "有料記事" / "会員向け" / "無料+CTA"
    outline:           list[str]
    estimated_word_count: int = 1500

    def to_dict(self) -> dict:
        return {
            "topic":               self.topic,
            "category":            self.category,
            "tags":                self.tags,
            "target_audience":     self.target_audience,
            "seo_keywords":        self.seo_keywords,
            "monetization_path":   self.monetization_path,
            "outline":             self.outline,
            "estimated_word_count": self.estimated_word_count,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NotePlan":
        return cls(
            topic=d.get("topic", ""),
            category=d.get("category", "テクノロジー"),
            tags=d.get("tags", []),
            target_audience=d.get("target_audience", ""),
            seo_keywords=d.get("seo_keywords", []),
            monetization_path=d.get("monetization_path", "無料+CTA"),
            outline=d.get("outline", []),
            estimated_word_count=d.get("estimated_word_count", 1500),
        )


@dataclass
class NoteArticle:
    """1本の記事を表すデータクラス。"""
    article_id:       str
    status:           ArticleStatus
    topic:            str
    title:            str             = ""
    intro:            str             = ""
    body:             str             = ""
    cta:              str             = ""
    summary:          str             = ""
    meta_description: str             = ""
    word_count:       int             = 0
    review_notes:     list[str]       = field(default_factory=list)
    draft_path:       str | None      = None
    plan:             NotePlan | None = None
    created_at:       str             = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    published_at:     str | None      = None

    @classmethod
    def new(cls, topic: str) -> "NoteArticle":
        return cls(
            article_id=str(uuid.uuid4())[:8],
            status=ArticleStatus.IDEA,
            topic=topic,
        )

    def to_dict(self) -> dict:
        return {
            "article_id":       self.article_id,
            "status":           self.status.value,
            "topic":            self.topic,
            "title":            self.title,
            "intro":            self.intro,
            "body":             self.body,
            "cta":              self.cta,
            "summary":          self.summary,
            "meta_description": self.meta_description,
            "word_count":       self.word_count,
            "review_notes":     self.review_notes,
            "draft_path":       self.draft_path,
            "plan":             self.plan.to_dict() if self.plan else None,
            "created_at":       self.created_at,
            "published_at":     self.published_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NoteArticle":
        plan_data = d.get("plan")
        return cls(
            article_id=d.get("article_id", ""),
            status=ArticleStatus(d.get("status", "idea")),
            topic=d.get("topic", ""),
            title=d.get("title", ""),
            intro=d.get("intro", ""),
            body=d.get("body", ""),
            cta=d.get("cta", ""),
            summary=d.get("summary", ""),
            meta_description=d.get("meta_description", ""),
            word_count=d.get("word_count", 0),
            review_notes=d.get("review_notes", []),
            draft_path=d.get("draft_path"),
            plan=NotePlan.from_dict(plan_data) if plan_data else None,
            created_at=d.get("created_at", ""),
            published_at=d.get("published_at"),
        )


@dataclass
class NoteStats:
    """Dashboard 表示用 Note Factory 統計。"""
    articles_today:       int   = 0
    articles_this_month:  int   = 0
    waiting_publish:      int   = 0
    waiting_approval:     int   = 0
    published_total:      int   = 0
    total_word_count:     int   = 0
    avg_word_count:       float = 0.0
    estimated_revenue_jpy: int  = 0

    def to_dict(self) -> dict:
        return {
            "articles_today":        self.articles_today,
            "articles_this_month":   self.articles_this_month,
            "waiting_publish":       self.waiting_publish,
            "waiting_approval":      self.waiting_approval,
            "published_total":       self.published_total,
            "total_word_count":      self.total_word_count,
            "avg_word_count":        self.avg_word_count,
            "estimated_revenue_jpy": self.estimated_revenue_jpy,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NoteStats":
        return cls(
            articles_today=d.get("articles_today", 0),
            articles_this_month=d.get("articles_this_month", 0),
            waiting_publish=d.get("waiting_publish", 0),
            waiting_approval=d.get("waiting_approval", 0),
            published_total=d.get("published_total", 0),
            total_word_count=d.get("total_word_count", 0),
            avg_word_count=d.get("avg_word_count", 0.0),
            estimated_revenue_jpy=d.get("estimated_revenue_jpy", 0),
        )


_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "note_factory.json"


@dataclass
class NoteConfig:
    """Note Factory 設定。config/note_factory.json から読む。"""
    target_word_count: int       = 1500
    category_default:  str       = "テクノロジー"
    forbidden_words:   list[str] = field(default_factory=list)
    min_word_count:    int       = 800
    max_word_count:    int       = 3000
    stub_mode:         bool      = True    # True=固定値, False=AI Router
    price_jpy:         int       = 500     # 有料記事の設定価格

    @classmethod
    def load(cls, path: Path | None = None) -> "NoteConfig":
        p = path or _CONFIG_PATH
        if not p.exists():
            return cls()
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            return cls(
                target_word_count=d.get("target_word_count", 1500),
                category_default=d.get("category_default", "テクノロジー"),
                forbidden_words=d.get("forbidden_words", []),
                min_word_count=d.get("min_word_count", 800),
                max_word_count=d.get("max_word_count", 3000),
                stub_mode=d.get("stub_mode", True),
                price_jpy=d.get("price_jpy", 500),
            )
        except (json.JSONDecodeError, OSError):
            return cls()
