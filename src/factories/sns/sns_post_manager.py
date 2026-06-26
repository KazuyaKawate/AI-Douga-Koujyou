"""SNS Post Manager — CRUD and status lifecycle for SNS posts."""
import json
import uuid
from datetime import date
from pathlib import Path

POSTS_PATH = Path(__file__).parent.parent.parent.parent / "config" / "sns_posts.json"

PLATFORMS = ["x", "threads", "instagram", "tiktok", "youtube_shorts", "linkedin", "facebook"]

PLATFORM_LABELS = {
    "x":              "X (Twitter)",
    "threads":        "Threads",
    "instagram":      "Instagram",
    "tiktok":         "TikTok",
    "youtube_shorts": "YouTube Shorts",
    "linkedin":       "LinkedIn",
    "facebook":       "Facebook",
}

PLATFORM_ICONS = {
    "x":              "𝕏",
    "threads":        "🧵",
    "instagram":      "📸",
    "tiktok":         "🎵",
    "youtube_shorts": "▶️",
    "linkedin":       "💼",
    "facebook":       "👥",
}

PLATFORM_LIMITS = {
    "x":              280,
    "threads":        500,
    "instagram":      2200,
    "tiktok":         150,
    "youtube_shorts": 5000,
    "linkedin":       3000,
    "facebook":       63206,
}

SOURCE_TYPES = ["idea", "note", "video", "sales"]
SOURCE_LABELS = {
    "idea":  "アイデア",
    "note":  "note記事",
    "video": "動画エピソード",
    "sales": "営業キャンペーン",
}

STATUSES = ["draft", "scheduled", "published", "archived"]
STATUS_LABELS = {
    "draft":     "下書き",
    "scheduled": "スケジュール済",
    "published": "公開済",
    "archived":  "アーカイブ",
}
STATUS_ICONS = {
    "draft":     "📄",
    "scheduled": "🗓️",
    "published": "✅",
    "archived":  "📦",
}

TRANSITIONS: dict[str, list[str]] = {
    "draft":     ["scheduled", "published", "archived"],
    "scheduled": ["published", "draft", "archived"],
    "published": ["archived"],
    "archived":  ["draft"],
}

_DEFAULT_POST = {
    "title": "",
    "source_type": "idea",
    "source_id": None,
    "platform": "x",
    "post_text": "",
    "hashtags": [],
    "status": "draft",
    "scheduled_date": None,
    "published_date": None,
    "engagement": {
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "reach": 0,
        "impressions": 0,
    },
}


def load_posts() -> dict:
    if POSTS_PATH.exists():
        try:
            return json.loads(POSTS_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    data: dict = {"posts": [], "meta": {"version": "4.4", "created_at": date.today().isoformat()}}
    _save(data)
    return data


def save_posts(data: dict) -> None:
    _save(data)


def _save(data: dict) -> None:
    POSTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    POSTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def create_post(title: str, platform: str, post_text: str = "", **kwargs) -> dict:
    today = date.today().isoformat()
    post = dict(_DEFAULT_POST)
    post.update(kwargs)
    post["id"] = f"sns_{uuid.uuid4().hex[:8]}"
    post["title"] = title
    post["platform"] = platform
    post["post_text"] = post_text
    post["status"] = "draft"
    post["created_at"] = today
    post["updated_at"] = today
    post["engagement"] = dict(_DEFAULT_POST["engagement"])

    data = load_posts()
    data["posts"].append(post)
    _save(data)
    return post


def update_post(post_id: str, **kwargs) -> dict:
    data = load_posts()
    for post in data.get("posts", []):
        if post["id"] == post_id:
            for k, v in kwargs.items():
                if k not in ("id", "created_at"):
                    post[k] = v
            post["updated_at"] = date.today().isoformat()
            break
    _save(data)
    return data


def delete_post(post_id: str) -> dict:
    data = load_posts()
    data["posts"] = [p for p in data.get("posts", []) if p["id"] != post_id]
    _save(data)
    return data


def transition_status(post_id: str, new_status: str) -> tuple[bool, str, dict]:
    """Move post to new_status. Returns (success, message, updated_data)."""
    data = load_posts()
    target = next((p for p in data.get("posts", []) if p["id"] == post_id), None)
    if not target:
        return False, "投稿が見つかりません", data

    current = target.get("status", "draft")
    allowed = TRANSITIONS.get(current, [])
    if new_status not in allowed:
        allowed_labels = [STATUS_LABELS.get(s, s) for s in allowed]
        return False, f"「{STATUS_LABELS[current]}」→「{STATUS_LABELS[new_status]}」への変更は不可です。可能: {', '.join(allowed_labels)}", data

    today = date.today().isoformat()
    target["status"] = new_status
    target["updated_at"] = today

    if new_status == "published":
        target["published_date"] = today
        _on_publish(target)

    _save(data)
    return True, f"✅ 「{STATUS_LABELS[new_status]}」に変更しました", data


def _on_publish(post: dict) -> None:
    """Side effects when SNS post is published: increment KPI + update factory status."""
    try:
        from src.hq.kpi_manager import load_kpi, update_actual
        kpi_data = load_kpi()
        current = kpi_data.get("actuals", {}).get("sns_posts", 0)
        update_actual("sns_posts", current + 1)
    except Exception:
        pass

    try:
        from src.hq.factory_status import load_factory_status, save_factory_status
        factory_data = load_factory_status()
        entry = factory_data.get("SNS投稿工場", {})
        entry["completed_today"] = entry.get("completed_today", 0) + 1
        entry["status"] = "active"
        platform_label = PLATFORM_LABELS.get(post.get("platform", ""), "SNS")
        entry["next_action"] = f"{platform_label}投稿完了！次の投稿を準備しましょう。"
        factory_data["SNS投稿工場"] = entry
        save_factory_status(factory_data)
    except Exception:
        pass


def get_posts_by_status(data: dict) -> dict[str, list]:
    buckets: dict[str, list] = {s: [] for s in STATUSES}
    for post in data.get("posts", []):
        s = post.get("status", "draft")
        if s in buckets:
            buckets[s].append(post)
    return buckets


def get_posts_by_platform(data: dict) -> dict[str, list]:
    buckets: dict[str, list] = {p: [] for p in PLATFORMS}
    for post in data.get("posts", []):
        p = post.get("platform", "x")
        if p in buckets:
            buckets[p].append(post)
    return buckets


def get_factory_summary(data: dict) -> dict:
    posts = data.get("posts", [])
    by_status = get_posts_by_status(data)
    today = date.today().isoformat()
    published_today = [p for p in by_status["published"] if p.get("published_date") == today]
    total_engagement = sum(
        p.get("engagement", {}).get("likes", 0) +
        p.get("engagement", {}).get("comments", 0) +
        p.get("engagement", {}).get("shares", 0)
        for p in by_status["published"]
    )
    return {
        "total": len(posts),
        "draft": len(by_status["draft"]),
        "scheduled": len(by_status["scheduled"]),
        "published": len(by_status["published"]),
        "published_today": len(published_today),
        "archived": len(by_status["archived"]),
        "active_items": len(by_status["scheduled"]),
        "completed_today": len(published_today),
        "total_engagement": total_engagement,
        "warnings": len([p for p in by_status["scheduled"]
                         if p.get("scheduled_date") and p["scheduled_date"] < today]),
    }
