from __future__ import annotations

from typing import Any
from uuid import uuid4


THREADS_LIMIT = 500


def build_threads_text(content: dict[str, Any]) -> str:
    text = str(content.get("threads_text") or content.get("text") or content.get("body") or content.get("title", ""))
    cta = str(content.get("cta", "")).strip()
    hashtags = content.get("hashtags", [])
    if isinstance(hashtags, str):
        hashtags = [tag.strip() for tag in hashtags.replace(",", " ").split() if tag.strip()]
    tag_line = " ".join(tag if str(tag).startswith("#") else f"#{tag}" for tag in hashtags)
    parts = [text.strip(), cta, tag_line]
    return "\n\n".join(part for part in parts if part)[:THREADS_LIMIT]


def build_note_text(content: dict[str, Any]) -> str:
    title = str(content.get("note_title") or content.get("title") or "AIOS Manual Publish").strip()
    body = str(content.get("note_body") or content.get("body") or content.get("text") or "").strip()
    cta = str(content.get("cta", "")).strip()
    tags = content.get("tags") or content.get("hashtags") or []
    if isinstance(tags, str):
        tags = [tag.strip().lstrip("#") for tag in tags.replace(",", " ").split() if tag.strip()]
    tag_line = " ".join(f"#{tag}" for tag in tags)
    sections = [f"# {title}", body, cta, tag_line]
    return "\n\n".join(section for section in sections if section)


class ManualPublisher:
    """Manual publish adapter. It prepares copy-ready text and never calls external APIs."""

    def publish(self, item: dict[str, Any], *, dry_run: bool = True) -> dict[str, Any]:
        platform = str(item.get("platform") or "manual")
        content = item.get("content", {})
        copy_text = build_note_text(content) if platform == "note" else build_threads_text(content)
        if not copy_text.strip():
            return {
                "platform": platform,
                "status": "failed",
                "dry_run": dry_run,
                "manual_mode": True,
                "message": "Manual publish text is empty.",
            }
        return {
            "platform": platform,
            "status": "dry_run" if dry_run else "manual_ready",
            "external_id": f"manual-{uuid4().hex[:10]}",
            "copy_text": copy_text,
            "copy_label": "note本文をコピー" if platform == "note" else "Threads本文をコピー",
            "manual_mode": True,
            "posted": False,
            "dry_run": dry_run,
            "message": "Copy the prepared text and publish manually." if not dry_run else "DryRun: manual publish text prepared.",
        }
