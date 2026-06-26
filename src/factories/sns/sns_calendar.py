"""SNS Calendar — schedule management for SNS posts."""
import json
from datetime import date, timedelta
from pathlib import Path

SCHEDULE_PATH = Path(__file__).parent.parent.parent.parent / "config" / "sns_schedule.json"


def load_schedule() -> dict:
    if SCHEDULE_PATH.exists():
        try:
            return json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    data = {"schedule": {}, "meta": {"version": "4.4", "updated_at": date.today().isoformat()}}
    _save(data)
    return data


def _save(data: dict) -> None:
    SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_posts_for_date(target_date: str) -> list[dict]:
    """Return all SNS posts scheduled or published on target_date."""
    try:
        from src.factories.sns.sns_post_manager import load_posts
        data = load_posts()
        result = []
        for post in data.get("posts", []):
            scheduled = post.get("scheduled_date") or ""
            published = post.get("published_date") or ""
            if scheduled[:10] == target_date or published[:10] == target_date:
                result.append(post)
        return result
    except Exception:
        return []


def get_week_schedule(start_date: date | None = None) -> dict[str, list[dict]]:
    """Return posts organized by day for the next 7 days."""
    base = start_date or date.today()
    result: dict[str, list[dict]] = {}
    for offset in range(7):
        day = (base + timedelta(days=offset)).isoformat()
        result[day] = get_posts_for_date(day)
    return result


def get_overdue_posts() -> list[dict]:
    """Return scheduled posts whose scheduled_date is in the past."""
    today = date.today().isoformat()
    try:
        from src.factories.sns.sns_post_manager import load_posts
        data = load_posts()
        return [
            p for p in data.get("posts", [])
            if p.get("status") == "scheduled"
            and (p.get("scheduled_date") or "") < today
        ]
    except Exception:
        return []


def get_today_posts() -> list[dict]:
    return get_posts_for_date(date.today().isoformat())


def get_monthly_summary(year_month: str | None = None) -> dict:
    """Return published/scheduled counts for a given YYYY-MM month."""
    if not year_month:
        year_month = date.today().isoformat()[:7]
    try:
        from src.factories.sns.sns_post_manager import load_posts, PLATFORMS
        data = load_posts()
        published = [
            p for p in data.get("posts", [])
            if p.get("status") == "published"
            and (p.get("published_date") or "")[:7] == year_month
        ]
        by_platform: dict[str, int] = {p: 0 for p in PLATFORMS}
        for post in published:
            plat = post.get("platform", "x")
            if plat in by_platform:
                by_platform[plat] += 1
        return {
            "year_month": year_month,
            "total_published": len(published),
            "by_platform": by_platform,
        }
    except Exception:
        return {"year_month": year_month, "total_published": 0, "by_platform": {}}
