from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Any

SESSION_MINUTES = 20

def verify_password(candidate: str) -> bool:
    expected = os.getenv("AIOS_MOBILE_REVIEW_PASSWORD", "")
    return bool(expected) and hmac.compare_digest(candidate.encode(), expected.encode())

def new_session() -> dict[str, str]:
    now = datetime.now().astimezone()
    return {"authenticated_at": now.isoformat(), "expires_at": (now + timedelta(minutes=SESSION_MINUTES)).isoformat(), "csrf_token": secrets.token_urlsafe(32)}

def session_valid(session: dict[str, Any] | None) -> bool:
    try: return bool(session and datetime.fromisoformat(str(session["expires_at"])) > datetime.now().astimezone())
    except (KeyError, TypeError, ValueError): return False

def csrf_valid(session: dict[str, Any] | None, supplied: str) -> bool:
    return session_valid(session) and hmac.compare_digest(str(session.get("csrf_token", "")), str(supplied or ""))

def token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:12] if token else ""
