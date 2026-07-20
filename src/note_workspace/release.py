"""Phase 10-3 manual note release preparation (local only)."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from src.utils.json_store import load_json, save_json_atomic

NOTE_HOSTS = {"note.com", "www.note.com"}
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|password)\s*[:=]\s*\S+"),
    re.compile(r"\b(?:sk|ghp|github_pat)_[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
PII_PATTERNS = (re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), re.compile(r"\b0\d{1,4}-\d{1,4}-\d{3,4}\b"))
ASSERTIVE = ("絶対に", "必ず儲か", "100%", "確実に稼")
FORBIDDEN = ("元本保証", "必ず治る", "絶対安全")
HTML = re.compile(r"</?[A-Za-z][^>]*>")
MARKDOWN_IMAGE = re.compile(r"!\[[^]]*]\(([^)]+)\)")

def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")

def release_content(article: dict[str, Any]) -> dict[str, Any]:
    return {key: article.get(key) for key in ("title", "body", "tags", "eyecatch", "visibility", "price")}

def approved_hash_matches(article: dict[str, Any]) -> bool:
    canonical = json.dumps(release_content(article), ensure_ascii=False, sort_keys=True)
    return article.get("approval", {}).get("content_hash") == hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def validate_note_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url.strip())
    if parsed.scheme != "https" or parsed.hostname not in NOTE_HOSTS:
        raise ValueError("公開URLはhttps://note.comドメインに限定されます")
    match = re.search(r"/n/(n[a-zA-Z0-9]+)(?:[/?#]|$)", parsed.path + "/")
    return url.strip(), match.group(1) if match else ""

class NoteReleaseService:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root); self.package_dir = self.root / "data" / "note_release_packages"
        self.audit_path = self.root / "data" / "note_release_audit.json"

    def check(self, article: dict[str, Any], *, existing_articles: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        title, body = str(article.get("title", "")).strip(), str(article.get("body", "")).strip()
        tags = article.get("tags") if isinstance(article.get("tags"), list) else []
        errors: list[dict[str, str]] = []; warnings: list[dict[str, str]] = []
        def add(target: list[dict[str, str]], code: str, message: str) -> None: target.append({"code": code, "message": message})
        if not title: add(errors, "title_required", "タイトルが未入力です")
        if not body: add(errors, "body_required", "本文が未入力です")
        if len(title) > 100: add(errors, "title_too_long", "タイトルが100文字を超えています")
        if len(body) < 200: add(errors, "body_too_short", "本文が200文字未満です")
        if len(tags) > 10: add(errors, "too_many_tags", "タグは10件以内です")
        combined = f"{title}\n{body}"
        if any(p.search(combined) for p in SECRET_PATTERNS): add(errors, "secret_detected", "秘密情報の疑いがあります")
        if HTML.search(body): add(errors, "unsupported_html", "HTMLタグは使用できません")
        for reference in MARKDOWN_IMAGE.findall(body):
            if reference.startswith(("https://", "http://")):
                continue
            image_path = (self.root / reference).resolve()
            if not image_path.is_relative_to(self.root.resolve()) or not image_path.is_file():
                add(errors, "broken_image_reference", "本文内の画像参照を確認できません")
        if any(word in combined for word in FORBIDDEN): add(errors, "forbidden_expression", "禁止表現が含まれています")
        if any(p.search(combined) for p in PII_PATTERNS): add(warnings, "personal_information", "個人情報の可能性があります")
        if any(word in combined for word in ASSERTIVE): add(warnings, "misleading_assertion", "誤認を招く断定表現の可能性があります")
        urls = re.findall(r"https?://[^\s)\]>]+", combined)
        if urls: add(warnings, "external_urls", f"外部URLを{len(urls)}件検出しました")
        if not str(article.get("cta", "")).strip(): add(warnings, "cta_missing", "CTAが未設定です")
        if article.get("price", 0) and not article.get("paid_boundary"): add(errors, "paid_boundary_required", "有料境界が未設定です")
        if int(article.get("price", 0) or 0) < 0: add(errors, "invalid_price", "価格が不正です")
        if not str(article.get("eyecatch", "")).strip(): add(warnings, "eyecatch_missing", "アイキャッチが未設定です")
        if article.get("approval", {}).get("status") != "approved": add(errors, "not_approved", "記事が承認済みではありません")
        if not approved_hash_matches(article): add(errors, "content_hash_mismatch", "承認後に投稿内容が変更されています")
        if article.get("dry_run", True) is not True or article.get("approval_required", True) is not True or article.get("execute_allowed", False) is not False:
            add(errors, "production_action_requested", "Phase 103では本番操作を実行できません")
        for other in existing_articles or []:
            if other.get("article_id") != article.get("article_id") and other.get("title") == title:
                add(errors, "duplicate_article", "重複記事の可能性があります"); break
        status = "rejected" if errors else ("human_review_required" if warnings else "passed")
        return {"status": status, "errors": errors, "warnings": warnings, "checked_at": now(), "content_hash_matches": approved_hash_matches(article), "external_urls": urls}

    def generate(self, article: dict[str, Any], *, existing_articles: list[dict[str, Any]] | None = None, source_conversation_id: str = "", source_job_id: str = "") -> dict[str, Any]:
        result = self.check(article, existing_articles=existing_articles)
        if result["errors"]: raise ValueError("公開準備を拒否しました: " + ", ".join(row["code"] for row in result["errors"]))
        approval = article["approval"]; package_id = f"nrp-{uuid4().hex[:12]}"; body = str(article.get("body", ""))
        plain = re.sub(r"[#*_>`~-]+", "", re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", body)).strip()
        payload = {"package_id": package_id, "article_id": article["article_id"], "title": article["title"], "body_markdown": body,
            "body_plain_text": plain, "tags": article.get("tags", []), "price": int(article.get("price", 0)),
            "publication_type": article.get("visibility", "draft"), "eyecatch_path": article.get("eyecatch", ""),
            "eyecatch_alt": article.get("eyecatch_alt", ""), "summary": article.get("summary", ""), "CTA": article.get("cta", ""),
            "approved_at": approval.get("approved_at", ""), "approver": approval.get("approver", ""), "content_hash": approval["content_hash"],
            "content_version": int(article.get("content_version", 1)), "created_at": now(), "planned_publish_at": article.get("planned_publish_at", ""),
            "source_conversation_id": source_conversation_id or article.get("source_conversation_id", ""), "source_job_id": source_job_id or article.get("source_job_id", ""),
            "preflight": result, "dry_run": True, "review_required": True, "approval_required": True,
            "production_actions_enabled": False, "execute_allowed": False, "external_request_sent": False}
        self.package_dir.mkdir(parents=True, exist_ok=True); base = self.package_dir / package_id
        save_json_atomic(base.with_suffix(".json"), payload)
        base.with_suffix(".md").write_text(f"# {payload['title']}\n\n{body}\n\n{payload['CTA']}\n\n" + " ".join(f"#{t}" for t in payload["tags"]), encoding="utf-8")
        base.with_suffix(".txt").write_text(f"{payload['title']}\n\n{plain}\n\n{payload['CTA']}\n\n" + " ".join(payload["tags"]), encoding="utf-8")
        payload["files"] = {ext: str(base.with_suffix(f'.{ext}')) for ext in ("json", "md", "txt")}
        self.audit("release_package_generated", article["article_id"], {"package_id": package_id, "status": result["status"]})
        return payload

    def audit(self, event: str, article_id: str, details: dict[str, Any]) -> None:
        data = load_json(self.audit_path, default={"events": []}) or {"events": []}; data.setdefault("events", []).insert(0, {"audit_id": f"nra-{uuid4().hex[:10]}", "event": event, "article_id": article_id, "details": details, "at": now(), "dry_run": True})
        save_json_atomic(self.audit_path, data)
