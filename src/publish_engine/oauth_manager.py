from __future__ import annotations

import os
from typing import Any


REQUIRED_ENV = {
    "threads": ("THREADS_ACCESS_TOKEN", "THREADS_USER_ID"),
    "note": ("NOTE_ACCESS_TOKEN",),
    "wordpress": ("WORDPRESS_API_URL", "WORDPRESS_USERNAME", "WORDPRESS_APP_PASSWORD"),
    "rss": (),
}


class OAuthManager:
    def status(self, platform: str) -> dict[str, Any]:
        required = REQUIRED_ENV.get(platform, ())
        missing = [name for name in required if not os.getenv(name, "").strip()]
        return {
            "platform": platform,
            "configured": not missing,
            "missing": missing,
            "dry_run": bool(missing),
            "api_key_protected": True,
        }
