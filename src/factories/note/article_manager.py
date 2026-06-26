"""Article Manager — CRUD and status lifecycle for note articles."""
import json
import uuid
from datetime import date
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "note_articles.json"

STATUSES = ["draft", "reviewing", "scheduled", "published", "archived"]
STATUS_LABELS = {
    "draft":     "下書き",
    "reviewing": "レビュー中",
    "scheduled": "スケジュール済",
    "published": "公開済",
    "archived":  "アーカイブ",
}
STATUS_ICONS = {
    "draft":     "📄",
    "reviewing": "🔍",
    "scheduled": "🗓️",
    "published": "✅",
    "archived":  "📦",
}

# Allowed status transitions: from → [to, ...]
TRANSITIONS: dict[str, list[str]] = {
    "draft":     ["reviewing", "archived"],
    "reviewing": ["scheduled", "draft", "archived"],
    "scheduled": ["published", "reviewing"],
    "published": ["archived"],
    "archived":  ["draft"],
}

_DEFAULT_ARTICLE = {
    "title": "",
    "status": "draft",
    "category": "",
    "tags": [],
    "target_keyword": "",
    "body_outline": "",
    "estimated_read_time": 5,
    "price": 0,
    "sales_count": 0,
    "estimated_revenue": 0,
    "actual_revenue": 0,
    "view_count": 0,
    "like_count": 0,
    "note_url": None,
    "scheduled_at": None,
    "published_at": None,
    "score": None,
    "repurpose": {
        "x_post": None,
        "threads_post": None,
        "youtube_shorts_script": None,
        "video_episode_proposal": None,
        "generated_at": None,
    },
}


def load_articles() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    data: dict = {"articles": [], "integration": _default_integration()}
    _save(data)
    return data


def save_articles(data: dict) -> None:
    _save(data)


def _save(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_integration() -> dict:
    return {
        "note_api_enabled": False,
        "note_api_key": None,
        "rss_url": None,
        "analytics_id": None,
        "last_sync": None,
    }


def create_article(title: str, **kwargs) -> dict:
    today = date.today().isoformat()
    article = dict(_DEFAULT_ARTICLE)
    article.update(kwargs)
    article["id"] = f"note_{uuid.uuid4().hex[:8]}"
    article["title"] = title
    article["status"] = "draft"
    article["created_at"] = today
    article["updated_at"] = today
    # Ensure repurpose sub-dict is a fresh copy
    article["repurpose"] = dict(_DEFAULT_ARTICLE["repurpose"])

    data = load_articles()
    data["articles"].append(article)
    _save(data)
    return article


def update_article(article_id: str, **kwargs) -> dict:
    data = load_articles()
    for article in data.get("articles", []):
        if article["id"] == article_id:
            for k, v in kwargs.items():
                if k not in ("id", "created_at", "status"):
                    article[k] = v
            article["updated_at"] = date.today().isoformat()
            break
    _save(data)
    return data


def delete_article(article_id: str) -> dict:
    data = load_articles()
    data["articles"] = [a for a in data.get("articles", []) if a["id"] != article_id]
    _save(data)
    return data


def transition_status(article_id: str, new_status: str, note_url: str = "") -> tuple[bool, str, dict]:
    """Move article to new_status. Returns (success, message, updated_data)."""
    data = load_articles()
    target = next((a for a in data.get("articles", []) if a["id"] == article_id), None)
    if not target:
        return False, "記事が見つかりません", data

    current = target.get("status", "draft")
    allowed = TRANSITIONS.get(current, [])
    if new_status not in allowed:
        allowed_labels = [STATUS_LABELS.get(s, s) for s in allowed]
        return False, f"「{STATUS_LABELS[current]}」から「{STATUS_LABELS[new_status]}」への移行はできません。可能: {', '.join(allowed_labels)}", data

    today = date.today().isoformat()
    target["status"] = new_status
    target["updated_at"] = today

    if new_status == "published":
        target["published_at"] = today
        if note_url:
            target["note_url"] = note_url
        _on_publish(target)
    elif new_status == "scheduled" and not target.get("scheduled_at"):
        target["scheduled_at"] = today
    elif new_status == "archived":
        pass

    _save(data)
    return True, f"✅ 「{STATUS_LABELS[new_status]}」に変更しました", data


def _on_publish(article: dict) -> None:
    """Side effects when article is published: increment KPI + update factory status."""
    try:
        from src.hq.kpi_manager import load_kpi, update_actual
        kpi_data = load_kpi()
        current_count = kpi_data.get("actuals", {}).get("note_posts", 0)
        update_actual("note_posts", current_count + 1)
    except Exception:
        pass

    try:
        from src.hq.factory_status import load_factory_status, save_factory_status
        factory_data = load_factory_status()
        entry = factory_data.get("note投稿工場", {})
        entry["completed_today"] = entry.get("completed_today", 0) + 1
        entry["status"] = "active"
        entry["next_action"] = "本日の投稿完了！次の記事の準備を始めましょう。"
        factory_data["note投稿工場"] = entry
        save_factory_status(factory_data)
    except Exception:
        pass


def get_articles_by_status(data: dict) -> dict[str, list]:
    buckets: dict[str, list] = {s: [] for s in STATUSES}
    for article in data.get("articles", []):
        s = article.get("status", "draft")
        if s in buckets:
            buckets[s].append(article)
    return buckets


def get_factory_summary(data: dict) -> dict:
    """Return counts for Mission Control factory card."""
    articles = data.get("articles", [])
    by_status = get_articles_by_status(data)
    today = date.today().isoformat()
    published_today = [
        a for a in by_status["published"]
        if a.get("published_at") == today
    ]
    return {
        "total": len(articles),
        "draft": len(by_status["draft"]),
        "reviewing": len(by_status["reviewing"]),
        "scheduled": len(by_status["scheduled"]),
        "published": len(by_status["published"]),
        "published_today": len(published_today),
        "archived": len(by_status["archived"]),
        "active_items": len(by_status["reviewing"]) + len(by_status["scheduled"]),
        "completed_today": len(published_today),
    }
