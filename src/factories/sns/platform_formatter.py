"""Platform Formatter — rule-based post text generation per platform. No external API."""
from src.factories.sns.hashtag_generator import generate_hashtags, format_hashtags


def _extract_points(text: str, max_points: int = 3) -> list[str]:
    points = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("-", "*", "・", "•")) or (
            len(line) > 1 and line[0].isdigit() and line[1] in (".", "、", " ")
        ):
            clean = line.lstrip("-*・•0123456789. 　").strip()
            if clean and len(clean) >= 4:
                points.append(clean)
    if not points:
        lines = [l.strip() for l in text.split("\n") if l.strip() and not l.startswith("#")]
        points = lines[:max_points]
    return points[:max_points]


def format_x(topic: str, body: str = "", tags: list[str] | None = None, source_title: str = "") -> str:
    """X: hook-first, under 280 chars."""
    hashtag_str = format_hashtags((tags or [])[:4])
    points = _extract_points(body, 2)

    hook = f"【{topic[:30]}】" if topic else ""
    lines = [hook, ""]

    if points:
        for pt in points:
            lines.append(f"✅ {pt[:40]}")
    elif source_title:
        lines.append(f"「{source_title[:40]}」について発信します")
    else:
        lines.append("最新情報をシェアします")

    lines += ["", "🔗 リンクはプロフィールから"]
    if hashtag_str:
        lines += ["", hashtag_str]

    text = "\n".join(lines)
    if len(text) > 280:
        text = text[:277] + "…"
    return text


def format_threads(topic: str, body: str = "", tags: list[str] | None = None, source_title: str = "") -> str:
    """Threads: conversational, up to 500 chars."""
    hashtag_str = format_hashtags((tags or [])[:5])
    points = _extract_points(body, 3)

    lines = [f"💬 {topic}", ""]
    if source_title:
        lines += [f"「{source_title}」より", ""]

    if points:
        lines.append("この件で大事なポイント：")
        for pt in points:
            lines.append(f"▶ {pt[:60]}")
    lines += ["", "みなさんはどう思いますか？ぜひコメントで教えてください！"]
    if hashtag_str:
        lines += ["", hashtag_str]

    return "\n".join(lines)


def format_instagram(topic: str, body: str = "", tags: list[str] | None = None, source_title: str = "") -> str:
    """Instagram: visual caption + many hashtags."""
    hashtag_str = format_hashtags((tags or [])[:20])
    points = _extract_points(body, 4)

    lines = [f"✨ {topic}", ""]
    if source_title:
        lines += [f"📖 {source_title}", ""]

    if points:
        for pt in points:
            lines.append(f"◆ {pt[:80]}")
        lines.append("")

    lines += [
        "コメント欄で感想を教えてください！💬",
        "フォローするといち早く最新情報をお届けします。",
        "",
        "—",
        hashtag_str,
    ]
    return "\n".join(lines)


def format_tiktok(topic: str, body: str = "", tags: list[str] | None = None, source_title: str = "") -> str:
    """TikTok: short hook + CTA, under 150 chars."""
    hashtag_str = format_hashtags((tags or [])[:5])
    hook = f"{topic[:30]}を知っていますか？" if topic else "必見です！"
    text = f"{hook} これを見て正解でした！\n{hashtag_str}"
    if len(text) > 150:
        text = text[:147] + "…"
    return text


def format_youtube_shorts(topic: str, body: str = "", tags: list[str] | None = None, source_title: str = "") -> str:
    """YouTube Shorts: title + description + hashtags."""
    hashtag_str = format_hashtags((tags or [])[:10])
    points = _extract_points(body, 3)

    title_line = f"📹 {topic[:70]}"
    lines = [title_line, ""]

    if source_title:
        lines += [f"元記事: {source_title}", ""]

    if points:
        lines.append("このShortで学べること：")
        for pt in points:
            lines.append(f"• {pt[:80]}")
        lines.append("")

    lines += [
        "チャンネル登録してね！🔔",
        "概要欄のリンクもチェック！",
        "",
        hashtag_str,
    ]
    return "\n".join(lines)


def format_linkedin(topic: str, body: str = "", tags: list[str] | None = None, source_title: str = "") -> str:
    """LinkedIn: professional, insight-driven."""
    hashtag_str = format_hashtags((tags or [])[:5])
    points = _extract_points(body, 4)

    lines = [f"{topic}について考えてみました。", ""]
    if source_title:
        lines += [f"最近「{source_title}」についてまとめました。", ""]

    if points:
        lines.append("主なポイント：")
        for i, pt in enumerate(points, 1):
            lines.append(f"{i}. {pt[:100]}")
        lines.append("")

    lines += [
        "同じテーマで取り組んでいる方、ぜひつながりましょう。",
        "コメントでご意見をお聞かせください。",
        "",
        hashtag_str,
    ]
    return "\n".join(lines)


def format_facebook(topic: str, body: str = "", tags: list[str] | None = None, source_title: str = "") -> str:
    """Facebook: community tone, friendly and shareable."""
    hashtag_str = format_hashtags((tags or [])[:5])
    points = _extract_points(body, 3)

    lines = [f"📢 {topic}"]
    if source_title:
        lines += ["", f"「{source_title}」をシェアします。"]

    lines.append("")
    if points:
        for pt in points:
            lines.append(f"👉 {pt[:120]}")
        lines.append("")

    lines += [
        "友達にもシェアしてもらえると嬉しいです😊",
        "コメントで感想をぜひ聞かせてください！",
        "",
        hashtag_str,
    ]
    return "\n".join(lines)


_FORMATTERS = {
    "x":              format_x,
    "threads":        format_threads,
    "instagram":      format_instagram,
    "tiktok":         format_tiktok,
    "youtube_shorts": format_youtube_shorts,
    "linkedin":       format_linkedin,
    "facebook":       format_facebook,
}


def format_post(
    platform: str,
    topic: str,
    body: str = "",
    category: str = "",
    extra_keywords: list[str] | None = None,
    source_title: str = "",
) -> dict:
    """Generate a formatted post for the given platform. Returns {text, hashtags, char_count}."""
    hashtags = generate_hashtags(topic, platform, category, extra_keywords)
    formatter = _FORMATTERS.get(platform, format_x)
    text = formatter(topic, body, hashtags, source_title)
    return {
        "text": text,
        "hashtags": hashtags,
        "char_count": len(text),
        "platform": platform,
    }


def format_all_platforms(
    topic: str,
    body: str = "",
    category: str = "",
    extra_keywords: list[str] | None = None,
    source_title: str = "",
    platforms: list[str] | None = None,
) -> dict[str, dict]:
    """Generate formatted posts for all (or specified) platforms."""
    from src.factories.sns.sns_post_manager import PLATFORMS
    target_platforms = platforms or PLATFORMS
    return {p: format_post(p, topic, body, category, extra_keywords, source_title)
            for p in target_platforms}
