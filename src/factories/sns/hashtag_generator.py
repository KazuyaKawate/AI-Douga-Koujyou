"""Hashtag Generator — rule-based hashtag generation. No external API."""

_CATEGORY_TAGS: dict[str, list[str]] = {
    "AI": ["AI", "人工知能", "ChatGPT", "機械学習", "テクノロジー"],
    "動画": ["動画制作", "YouTube", "Shorts", "クリエイター", "映像制作"],
    "note": ["note", "ブログ", "コンテンツ", "ライティング", "記事"],
    "ビジネス": ["ビジネス", "起業", "副業", "フリーランス", "マーケティング"],
    "SNS": ["SNS", "インフルエンサー", "フォロワー", "エンゲージメント", "バズ"],
    "収益化": ["収益化", "マネタイズ", "稼ぐ", "副収入", "ネット収益"],
    "学習": ["学習", "勉強法", "スキルアップ", "資格", "オンライン学習"],
    "ライフスタイル": ["ライフスタイル", "日常", "暮らし", "習慣", "ルーティン"],
    "プログラミング": ["プログラミング", "Python", "コーディング", "エンジニア", "開発"],
    "マーケティング": ["マーケティング", "集客", "SEO", "コンテンツマーケ", "ブランディング"],
}

_PLATFORM_TAGS: dict[str, list[str]] = {
    "x":              [],
    "threads":        ["Threads"],
    "instagram":      ["instagood", "photooftheday"],
    "tiktok":         ["fyp", "foryou", "TikTok"],
    "youtube_shorts": ["YouTubeShorts", "Shorts"],
    "linkedin":       [],
    "facebook":       [],
}

_GENERAL_TAGS = ["クリエイター", "コンテンツ制作", "日本語"]


def generate_hashtags(
    topic: str,
    platform: str,
    category: str = "",
    extra_keywords: list[str] | None = None,
    max_count: int = 10,
) -> list[str]:
    """Generate hashtags rule-based from topic/platform/category."""
    tags: list[str] = []

    # Topic-derived tags (clean the topic into hashtag)
    topic_clean = topic.strip().replace(" ", "").replace("　", "")
    if topic_clean and len(topic_clean) <= 20:
        tags.append(topic_clean)

    # Extra keywords as hashtags
    for kw in (extra_keywords or [])[:3]:
        kw_clean = kw.strip().replace(" ", "")
        if kw_clean and kw_clean not in tags and len(kw_clean) <= 20:
            tags.append(kw_clean)

    # Category-based tags
    for cat_key, cat_tags in _CATEGORY_TAGS.items():
        if cat_key in (category or "") or cat_key in topic:
            for t in cat_tags[:2]:
                if t not in tags:
                    tags.append(t)

    # Platform-specific tags
    for pt in _PLATFORM_TAGS.get(platform, []):
        if pt not in tags:
            tags.append(pt)

    # Fill with general tags if under limit
    for gt in _GENERAL_TAGS:
        if len(tags) >= max_count:
            break
        if gt not in tags:
            tags.append(gt)

    # Platform-specific max
    platform_max = {
        "x": 4,
        "threads": 5,
        "instagram": 20,
        "tiktok": 5,
        "youtube_shorts": 10,
        "linkedin": 5,
        "facebook": 5,
    }
    limit = min(max_count, platform_max.get(platform, 10))
    return tags[:limit]


def format_hashtags(tags: list[str]) -> str:
    """Return hashtag string with # prefixes."""
    return " ".join(f"#{t}" if not t.startswith("#") else t for t in tags)


def suggest_from_note_article(article: dict, platform: str) -> list[str]:
    """Derive hashtags from a note article dict."""
    topic = article.get("target_keyword") or article.get("title", "")
    extra = article.get("tags", [])[:5]
    category = article.get("category", "")
    return generate_hashtags(topic, platform, category, extra)


def suggest_from_episode(episode: dict, platform: str) -> list[str]:
    """Derive hashtags from a video episode dict."""
    topic = episode.get("theme") or episode.get("title", "")
    extra = []
    if episode.get("character"):
        extra.append(episode["character"])
    return generate_hashtags(topic, platform, "動画", extra)
