"""Article Scorer — rule-based scoring across 6 criteria. No external API."""
from datetime import date

CRITERIA = ["seo", "readability", "cta", "story", "originality", "monetization"]

CRITERIA_LABELS = {
    "seo":           "SEO",
    "readability":   "読みやすさ",
    "cta":           "CTA",
    "story":         "ストーリー",
    "originality":   "独自性",
    "monetization":  "収益性",
}

CRITERIA_ICONS = {
    "seo":          "🔍",
    "readability":  "📖",
    "cta":          "📣",
    "story":        "📖",
    "originality":  "💡",
    "monetization": "💰",
}

CRITERIA_DESCRIPTIONS = {
    "seo":          "タイトル長・キーワード・タグ数・本文量",
    "readability":  "推定読了時間・アウトライン充実度・段落構成",
    "cta":          "行動喚起ワード・リンク・有料コンテンツ",
    "story":        "個人的体験・フック・ナラティブ構造",
    "originality":  "独自視点・実体験・ニッチ特化",
    "monetization": "価格設定・アフィリエイト・PR要素",
}


def score_article(article: dict) -> dict:
    """Score an article. Returns {scores: {criterion: int}, total: int, grade: str, scored_at: str}."""
    title = article.get("title", "")
    keyword = article.get("target_keyword", "")
    tags = article.get("tags", [])
    outline = article.get("body_outline", "")
    read_time = article.get("estimated_read_time", 0)
    price = article.get("price", 0)
    note_url = article.get("note_url") or ""

    scores: dict[str, int] = {}

    # ── SEO (0–20) ─────────────────────────────────────────────────────────────
    seo = 0
    if 10 <= len(title) <= 60:
        seo += 4
    elif len(title) >= 6:
        seo += 2
    if keyword and keyword in title:
        seo += 6
    elif keyword:
        seo += 2
    if len(tags) >= 3:
        seo += 4
    elif len(tags) >= 1:
        seo += 2
    if len(outline) >= 200:
        seo += 4
    elif len(outline) >= 80:
        seo += 2
    elif len(outline) >= 20:
        seo += 1
    scores["seo"] = min(seo, 20)

    # ── Readability (0–20) ──────────────────────────────────────────────────────
    read = 0
    if 3 <= read_time <= 10:
        read += 8
    elif 1 <= read_time < 3 or 10 < read_time <= 15:
        read += 4
    if len(outline) >= 300:
        read += 6
    elif len(outline) >= 150:
        read += 4
    elif len(outline) >= 50:
        read += 2
    newline_count = outline.count("\n")
    if newline_count >= 5:
        read += 6
    elif newline_count >= 2:
        read += 3
    scores["readability"] = min(read, 20)

    # ── CTA (0–20) ─────────────────────────────────────────────────────────────
    cta = 0
    cta_words = ["フォロー", "購読", "コメント", "シェア", "購入", "申し込み", "チェック",
                 "ご覧", "クリック", "登録", "参加", "DM", "お問い合わせ"]
    for w in cta_words:
        if w in outline:
            cta += 8
            break
    if "http" in outline or "リンク" in outline or "URL" in outline:
        cta += 6
    if price > 0:
        cta += 6
    scores["cta"] = min(cta, 20)

    # ── Story (0–20) ────────────────────────────────────────────────────────────
    story = 0
    personal = ["私は", "私が", "私の", "僕は", "僕が", "僕の", "自分が", "自分の", "実は", "正直"]
    for w in personal:
        if w in outline:
            story += 6
            break
    hook_words = ["知っていますか", "驚き", "衝撃", "秘密", "ヒント", "方法", "理由", "なぜ", "実は", "意外"]
    first_part = outline[:120]
    for w in hook_words:
        if w in first_part:
            story += 8
            break
    narrative = ["まず", "次に", "そして", "最後に", "結論", "まとめ", "ポイント", "ステップ"]
    matches = sum(1 for w in narrative if w in outline)
    story += min(matches * 2, 6)
    scores["story"] = min(story, 20)

    # ── Originality (0–20) ─────────────────────────────────────────────────────
    orig = 0
    orig_words = ["独自", "オリジナル", "実体験", "体験談", "実際に", "実際の", "経験", "失敗", "成功"]
    for w in orig_words:
        if w in outline:
            orig += 8
            break
    if keyword:
        orig += 6
    angle_words = ["独自視点", "新しい", "初めて", "誰も", "唯一", "特別", "ユニーク"]
    for w in angle_words:
        if w in outline:
            orig += 6
            break
    scores["originality"] = min(orig, 20)

    # ── Monetization (0–20) ────────────────────────────────────────────────────
    money = 0
    if price > 0:
        money += 8
    if price >= 500:
        money += 4
    if price >= 1000:
        money += 2
    money_words = ["アフィリエイト", "PR", "広告", "スポンサー", "購入リンク", "有料", "限定"]
    for w in money_words:
        if w in outline:
            money += 6
            break
    scores["monetization"] = min(money, 20)

    total = sum(scores.values())

    if total >= 85:
        grade = "S"
    elif total >= 70:
        grade = "A"
    elif total >= 55:
        grade = "B"
    elif total >= 40:
        grade = "C"
    else:
        grade = "D"

    return {
        "scores": scores,
        "total": total,
        "grade": grade,
        "scored_at": date.today().isoformat(),
    }


def score_and_save(article_id: str) -> dict:
    """Score an article and persist the result."""
    from src.factories.note.article_manager import load_articles, save_articles
    data = load_articles()
    for article in data.get("articles", []):
        if article["id"] == article_id:
            result = score_article(article)
            article["score"] = result
            break
    save_articles(data)
    return data


def get_score_tips(scores: dict) -> list[str]:
    """Return improvement tips for low-scoring criteria."""
    tips = []
    s = scores.get("scores", {})
    if s.get("seo", 0) < 12:
        tips.append("🔍 **SEO改善:** タイトルにキーワードを含め、タグを3つ以上設定してください。")
    if s.get("readability", 0) < 12:
        tips.append("📖 **読みやすさ改善:** アウトラインを300字以上記入し、見出しや改行を増やしてください。")
    if s.get("cta", 0) < 12:
        tips.append("📣 **CTA改善:** 「フォロー」「コメント」「購入」などの行動喚起ワードを追加してください。")
    if s.get("story", 0) < 12:
        tips.append("📖 **ストーリー改善:** 冒頭に個人的な体験や「実は...」というフックを入れてください。")
    if s.get("originality", 0) < 12:
        tips.append("💡 **独自性改善:** 実体験や独自の視点・失敗談を加えてください。")
    if s.get("monetization", 0) < 12:
        tips.append("💰 **収益性改善:** 有料販売または関連商品のリンクを追加することを検討してください。")
    return tips
