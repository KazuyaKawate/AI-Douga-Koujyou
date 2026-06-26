"""Content Repurpose Engine — rule-based generation. No external API calls."""
from datetime import date


def _extract_points(outline: str, max_points: int = 3) -> list[str]:
    """Extract key bullet points from body outline."""
    points = []
    for line in outline.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Skip markdown headers
        if line.startswith("#"):
            continue
        # Keep bullet points and numbered items
        if line.startswith(("-", "*", "・", "•")) or (len(line) > 1 and line[0].isdigit() and line[1] in (".", "、", " ")):
            clean = line.lstrip("-*・•0123456789. 　").strip()
            if clean and len(clean) >= 5:
                points.append(clean)
    # Fallback: use first N non-empty lines
    if not points:
        all_lines = [l.strip() for l in outline.split("\n") if l.strip() and not l.startswith("#")]
        points = all_lines[:max_points]
    return points[:max_points]


def generate_x_post(article: dict) -> str:
    title = article.get("title", "無題")
    tags = article.get("tags", [])
    keyword = article.get("target_keyword", "")
    outline = article.get("body_outline", "")

    points = _extract_points(outline, 3)
    if not points:
        points = [f"{keyword}について詳しく解説しています" if keyword else "詳しくは記事をご覧ください"]

    hashtags_list = [f"#{t}" for t in tags[:3]]
    if keyword and f"#{keyword}" not in hashtags_list:
        hashtags_list.append(f"#{keyword}")

    lines = [f"【{title}】", ""]
    for pt in points:
        trimmed = pt[:38] + "…" if len(pt) > 40 else pt
        lines.append(f"✅ {trimmed}")
    lines += ["", "詳しくはnoteで→ [URLをここに貼り付け]", ""]
    if hashtags_list:
        lines.append(" ".join(hashtags_list[:4]))

    text = "\n".join(lines)
    if len(text) > 280:
        text = text[:277] + "…"
    return text


def generate_threads_post(article: dict) -> str:
    title = article.get("title", "無題")
    tags = article.get("tags", [])
    keyword = article.get("target_keyword", "")
    outline = article.get("body_outline", "")
    read_time = article.get("estimated_read_time", 5)

    points = _extract_points(outline, 4)
    hashtags = " ".join(f"#{t}" for t in tags[:5])

    sections = [
        f"📝 {title}",
        "",
        f"（約{read_time}分で読めます）",
        "",
        "この記事でわかること：",
    ]
    for pt in points:
        sections.append(f"▶ {pt}")

    sections += [
        "",
        f"{'今日は実際に' if keyword else '今日は'}「{keyword or title}」について深掘りしました。",
        "ぜひ読んでみてください！",
        "",
        "🔗 noteリンク → [URLをここに貼り付け]",
        "",
        f"気に入ったらフォロー＆スキお願いします！",
    ]
    if hashtags:
        sections += ["", hashtags]

    return "\n".join(sections)


def generate_youtube_shorts_script(article: dict) -> str:
    title = article.get("title", "無題")
    keyword = article.get("target_keyword", "") or title
    outline = article.get("body_outline", "")

    points = _extract_points(outline, 3)
    if not points:
        points = ["ポイント1", "ポイント2", "ポイント3"]

    script_lines = [
        "# YouTube Shorts スクリプト（目安: 約60秒）",
        "",
        "## 🎬 HOOK（0〜3秒）",
        f'「{keyword}について知っていますか？ほとんどの人が見落としているポイントがあります。」',
        "",
        "## 📌 POINT 1（3〜20秒）",
        f'「まず大切なのは、{points[0][:50]}。これを意識するだけで結果が変わります。」',
        "",
        "## 📌 POINT 2（20〜38秒）",
        f'「次に、{points[1][:50] if len(points) > 1 else "もう一つのポイントがあります"}。実際に試してみてください。」',
        "",
        "## 📌 POINT 3（38〜52秒）",
        f'「そして、{points[2][:50] if len(points) > 2 else "最後のコツは継続すること"}。これが一番重要です。」',
        "",
        "## 📣 CTA（52〜60秒）",
        f'「詳しくはnoteの記事「{title[:30]}」をチェック！リンクはプロフィールから。チャンネル登録もよろしく！」',
        "",
        "---",
        f"*記事タイトル: {title}*",
        f"*キーワード: {keyword}*",
    ]
    return "\n".join(script_lines)


def generate_video_episode_proposal(article: dict) -> str:
    title = article.get("title", "無題")
    keyword = article.get("target_keyword", "") or title
    tags = article.get("tags", [])
    outline = article.get("body_outline", "")
    article_id = article.get("id", "note_001")

    ep_suffix = article_id[-4:].upper()
    ep_id = f"EP_NOTE_{ep_suffix}"

    points = _extract_points(outline, 4)
    scenes = []
    for i, pt in enumerate(points, 1):
        scenes.append(f"  シーン{i}: {pt[:60]}")
    if not scenes:
        scenes = ["  シーン1: イントロ・フック", "  シーン2: メインコンテンツ", "  シーン3: まとめ・CTA"]

    related_tags = ", ".join(tags[:4]) if tags else keyword

    proposal_lines = [
        "# 動画エピソード提案",
        "",
        f"**エピソードID:** {ep_id}",
        f"**タイトル案:** 「{title}」を動画で解説",
        f"**テーマ:** {keyword}",
        f"**推定尺:** 3〜5分",
        f"**関連タグ:** {related_tags}",
        "",
        "## シーン構成",
        "",
    ]
    proposal_lines.extend(scenes)
    proposal_lines += [
        "",
        "## 制作メモ",
        f"- note記事「{title}」を元に動画化",
        f"- 記事ID: {article_id}",
        f"- 記事のアウトラインをナレーション台本のベースに使用",
        "- サムネイルに記事タイトルを使用",
        "",
        "## AI動画工場での次のステップ",
        "1. ⚡ 一発生成 でエピソードIDを入力",
        f'2. テーマに「{keyword[:30]}」を入力',
        "3. 生成後、このnote記事と相互リンク",
        "",
        f"*生成元記事ID: {article_id} — {date.today().isoformat()}*",
    ]
    return "\n".join(proposal_lines)


def generate_all(article: dict) -> dict:
    """Generate all repurpose formats and return as dict."""
    return {
        "x_post": generate_x_post(article),
        "threads_post": generate_threads_post(article),
        "youtube_shorts_script": generate_youtube_shorts_script(article),
        "video_episode_proposal": generate_video_episode_proposal(article),
        "generated_at": date.today().isoformat(),
    }


def save_repurpose(article_id: str, repurpose_data: dict) -> dict:
    from src.factories.note.article_manager import load_articles, save_articles
    data = load_articles()
    for article in data.get("articles", []):
        if article["id"] == article_id:
            article["repurpose"] = repurpose_data
            break
    save_articles(data)
    return data
