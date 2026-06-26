"""SNS Analytics Placeholder — stub classes for future analytics integrations.

No external API calls are made. These classes are extension points for v4.6+.
"""
from datetime import date


class XAnalytics:
    """Placeholder for X (Twitter) Analytics API integration."""

    def __init__(self, bearer_token: str | None = None):
        self.bearer_token = bearer_token

    def is_configured(self) -> bool:
        return bool(self.bearer_token)

    def get_post_metrics(self, tweet_id: str) -> dict:
        return {"status": "not_implemented", "likes": 0, "retweets": 0, "impressions": 0}

    def get_account_metrics(self, since: str = None) -> dict:
        return {"status": "not_implemented", "followers": 0, "following": 0}


class InstagramInsights:
    """Placeholder for Instagram Graph API insights."""

    def __init__(self, access_token: str | None = None):
        self.access_token = access_token

    def is_configured(self) -> bool:
        return bool(self.access_token)

    def get_media_insights(self, media_id: str) -> dict:
        return {"status": "not_implemented", "likes": 0, "comments": 0, "reach": 0}


class YouTubeAnalytics:
    """Placeholder for YouTube Data API v3 analytics."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_video_stats(self, video_id: str) -> dict:
        return {"status": "not_implemented", "views": 0, "likes": 0, "comments": 0}


class ThreadsAnalytics:
    """Placeholder for Threads API (not publicly available yet)."""

    def __init__(self):
        pass

    def is_configured(self) -> bool:
        return False

    def get_post_metrics(self, post_id: str) -> dict:
        return {"status": "not_implemented"}


def update_post_engagement(post_id: str, likes: int = 0, comments: int = 0,
                           shares: int = 0, reach: int = 0, impressions: int = 0) -> dict:
    """Manually update engagement stats for a post."""
    try:
        from src.factories.sns.sns_post_manager import load_posts, save_posts
        data = load_posts()
        for post in data.get("posts", []):
            if post["id"] == post_id:
                post.setdefault("engagement", {})
                if likes:
                    post["engagement"]["likes"] = likes
                if comments:
                    post["engagement"]["comments"] = comments
                if shares:
                    post["engagement"]["shares"] = shares
                if reach:
                    post["engagement"]["reach"] = reach
                if impressions:
                    post["engagement"]["impressions"] = impressions
                post["engagement"]["updated_at"] = date.today().isoformat()
                break
        save_posts(data)
        return data
    except Exception as exc:
        return {"error": str(exc)}


def get_analytics_status(config: dict) -> dict:
    """Return current analytics integration readiness."""
    return {
        "x": {
            "label": "X Analytics",
            "configured": bool(config.get("x_bearer_token")),
            "status": "placeholder",
            "description": "X API v2でインプレッション・エンゲージメントを取得予定",
        },
        "instagram": {
            "label": "Instagram Insights",
            "configured": bool(config.get("instagram_access_token")),
            "status": "placeholder",
            "description": "Meta Graph APIでリーチ・エンゲージメントを取得予定",
        },
        "youtube": {
            "label": "YouTube Analytics",
            "configured": bool(config.get("youtube_api_key")),
            "status": "placeholder",
            "description": "YouTube Data API v3で再生数・いいねを取得予定",
        },
        "threads": {
            "label": "Threads Analytics",
            "configured": False,
            "status": "coming_soon",
            "description": "Threads APIが公開され次第対応予定",
        },
    }
