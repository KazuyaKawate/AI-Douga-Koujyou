"""Phase 10-2 note workspace. All publish operations stop at DryRun."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.business_engine.manager import BusinessEngineStore
from src.revenue_engine.dashboard import RevenueEngineDashboard
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic
from src.workspace.integration import GoogleWorkspaceIntegration
from src.note_workspace.release import NoteReleaseService, approved_hash_matches, now as release_now, validate_note_url
from src.mobile_review_hub import CommonPublishQueue


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _hash(article: dict[str, Any]) -> str:
    keys = {key: article.get(key) for key in ("title", "body", "tags", "eyecatch", "visibility", "price")}
    return hashlib.sha256(json.dumps(keys, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _normalize_tags(tags: list[str] | None) -> list[str]:
    normalized = (str(tag).strip().lstrip("#").replace(" ", "") for tag in (tags or []))
    return list(dict.fromkeys(tag for tag in normalized if tag))[:10]


class NoteWorkspace:
    def __init__(self, *, root: str | Path = PROJECT_ROOT, path: str | Path | None = None,
                 business: BusinessEngineStore | None = None, revenue: RevenueEngineDashboard | None = None,
                 google: GoogleWorkspaceIntegration | None = None) -> None:
        self.root = Path(root)
        self.path = Path(path or self.root / "data" / "note_workspace.json")
        self.business = business or BusinessEngineStore(self.root / "config" / "business_engine.json")
        self.revenue = revenue or RevenueEngineDashboard(self.root / "config" / "revenue_engine.json")
        self.google = google or GoogleWorkspaceIntegration(root=self.root)
        self.release = NoteReleaseService(self.root)
        self.mobile_review = CommonPublishQueue(self.root / "data" / "mobile_publish_queue.json")

    def load(self) -> dict[str, Any]:
        data = load_json(self.path, default={}) or {}
        data.setdefault("articles", [])
        data.setdefault("history", [])
        for article in data["articles"]:
            article.setdefault("dry_run", True)
            article.setdefault("review_required", True)
            article.setdefault("approval_required", True)
            article.setdefault("execute_allowed", False)
            article.setdefault("production_actions_enabled", False)
        data.update(dry_run=True, review_required=True, approval_required=True, execute_allowed=False, production_actions_enabled=False)
        return data

    def create(self, *, instruction: str, title: str = "", body: str = "", tags: list[str] | None = None,
               eyecatch: str = "", visibility: str = "draft", price: int = 0) -> dict[str, Any]:
        if visibility not in {"draft", "unlisted", "public_after_review"}:
            raise ValueError("公開設定が不正です")
        topic = instruction.strip() or "AIOSで初収益を作る"
        article = {
            "article_id": f"note-{uuid4().hex[:12]}", "instruction": topic,
            "title": title.strip() or f"{topic}を小さく始める実践ガイド",
            "body": body.strip() or self._generate_body(topic),
            "tags": _normalize_tags(tags or ["AIOS", "note", "収益化"]),
            "eyecatch": eyecatch.strip(), "visibility": visibility, "price": max(0, int(price)),
            "status": "review_required", "review": {}, "approval": {}, "scheduled_for": "", "content_version": 1,
            "summary": "", "cta": "", "eyecatch_alt": "", "paid_boundary": "", "planned_publish_at": "",
            "pv": 0, "ctr": 0.0, "revenue_forecast": 0, "actual_revenue": 0,
            "dry_run": True, "review_required": True, "approval_required": True, "execute_allowed": False,
            "production_actions_enabled": False,
            "created_at": _now(), "updated_at": _now(),
        }
        state = self.load(); state["articles"].insert(0, article)
        self._history(state, article, "article_generated")
        self._save(state)
        return article

    def review(self, article_id: str) -> dict[str, Any]:
        state, article = self._find(article_id)
        issues = []
        if not article["title"].strip(): issues.append("title_required")
        if len(article["body"].strip()) < 200: issues.append("body_too_short")
        if not article["tags"]: issues.append("tags_required")
        article["review"] = {"status": "passed" if not issues else "changes_required", "issues": issues, "reviewed_at": _now()}
        article["status"] = "approval_required" if not issues else "changes_required"
        article["updated_at"] = _now(); self._history(state, article, "review_completed"); self._save(state)
        if not issues:
            self._enqueue_mobile_review(article)
        return article

    def approve(self, article_id: str, *, approver: str) -> dict[str, Any]:
        state, article = self._find(article_id)
        if article.get("review", {}).get("status") != "passed" or not approver.strip():
            raise ValueError("レビュー通過と承認者が必要です")
        article["approval"] = {"status": "approved", "approver": approver.strip(), "content_hash": _hash(article), "approved_at": _now(), "approved_content_version": int(article.get("content_version", 1))}
        article["status"] = "approved"; article["updated_at"] = _now()
        self._history(state, article, "human_approved"); self._save(state)
        return article

    def prepare_draft(self, article_id: str) -> dict[str, Any]:
        state, article = self._find(article_id); self._require_approval(article)
        draft_dir = self.root / "output" / "note_drafts"; draft_dir.mkdir(parents=True, exist_ok=True)
        draft_path = draft_dir / f"{article_id}.md"
        draft_path.write_text(self._markdown(article), encoding="utf-8")
        article.update(status="note_post_ready", draft_path=str(draft_path), prepared_at=_now(), updated_at=_now())
        docs = self.google.docs_save(article["title"], article["body"])
        history_path = self._write_history_snapshot(article)
        drive = self.google.drive_upload(str(history_path.relative_to(self.root)))
        article["workspace_actions"] = {"docs": docs["action_id"], "drive": drive["action_id"]}
        self._history(state, article, "draft_prepared"); self._save(state)
        self.revenue.record_note_draft_save({"article_id": article_id, "title": article["title"], "save_url": f"dryrun://note/{article_id}", "status": "note_post_ready", "dry_run": True})
        self._update_metrics(article, posts=1)
        return article

    def schedule(self, article_id: str, scheduled_for: str) -> dict[str, Any]:
        state, article = self._find(article_id); self._require_approval(article)
        if article.get("status") != "note_post_ready": raise ValueError("下書き保存後のみ予約できます")
        article.update(status="scheduled_dry_run", scheduled_for=scheduled_for, updated_at=_now())
        self._history(state, article, "schedule_created"); self._save(state)
        self.revenue.record_publish_history({"article_id": article_id, "channel": "note", "status": "scheduled_dry_run", "scheduled_for": scheduled_for, "external_request_sent": False, "dry_run": True})
        return article

    def record_metrics(self, article_id: str, *, pv: int, ctr: float, revenue_per_click: int = 120) -> dict[str, Any]:
        state, article = self._find(article_id)
        article["pv"] = max(0, int(pv)); article["ctr"] = min(1.0, max(0.0, float(ctr)))
        article["revenue_forecast"] = int(article["pv"] * article["ctr"] * max(0, revenue_per_click))
        article["updated_at"] = _now(); self._history(state, article, "metrics_updated"); self._save(state)
        self._update_metrics(article, posts=1 if article.get("status") in {"note_post_ready", "scheduled_dry_run"} else 0)
        return article

    def update_content(self, article_id: str, **updates: Any) -> dict[str, Any]:
        state, article = self._find(article_id)
        for key in ("title", "body", "tags", "eyecatch", "visibility", "price"):
            if key in updates: article[key] = _normalize_tags(updates[key]) if key == "tags" else updates[key]
        article.update(status="review_required", review={}, approval={}, content_version=int(article.get("content_version", 1)) + 1, updated_at=_now())
        self._history(state, article, "content_changed_approval_invalidated"); self._save(state)
        return article

    def preflight(self, article_id: str) -> dict[str, Any]:
        state, article = self._find(article_id)
        return self.release.check(article, existing_articles=state["articles"])

    def generate_release_package(self, article_id: str, **source: str) -> dict[str, Any]:
        state, article = self._find(article_id)
        package = self.release.generate(article, existing_articles=state["articles"], **source)
        article.update(status="release_package_ready", release_package=package, updated_at=_now())
        self._history(state, article, "release_package_generated"); self._save(state)
        return package

    def accept_mobile_approval(self, queue_item: dict[str, Any]) -> dict[str, Any]:
        if queue_item.get("target_platform") != "note" or queue_item.get("source_engine") != "note_workspace":
            raise ValueError("NoteWorkspace由来のnote承認だけ受け付けます")
        if queue_item.get("status") != "ready_to_publish" or not queue_item.get("approval", {}).get("content_hash"):
            raise ValueError("Mobile Review Hubの承認が必要です")
        article_id = str(queue_item.get("source_id", ""))
        state, article = self._find(article_id)
        article.update(
            title=str(queue_item.get("title", article.get("title", ""))),
            body=str(queue_item.get("body", article.get("body", ""))),
            tags=_normalize_tags(queue_item.get("tags", article.get("tags", []))),
            cta=str(queue_item.get("cta", article.get("cta", ""))),
            price=max(0, int(queue_item.get("price", article.get("price", 0)) or 0)),
            visibility=str(queue_item.get("publication_type", article.get("visibility", "draft"))),
            planned_publish_at=str(queue_item.get("planned_publish_at", article.get("planned_publish_at", ""))),
            eyecatch=str(queue_item.get("image_path", article.get("eyecatch", ""))),
            review={"status": "passed", "issues": [], "reviewed_at": _now(), "source": "mobile_review_hub"},
            status="approval_required",
            approval={},
            content_version=int(queue_item.get("content_version", article.get("content_version", 1))),
            updated_at=_now(),
        )
        self._history(state, article, "mobile_review_accepted"); self._save(state)
        approved = self.approve(article_id, approver=str(queue_item["approval"].get("approver", "mobile-human")))
        package = self.generate_release_package(article_id, source_job_id=str(queue_item.get("queue_id", "")))
        return {"article": approved, "package": package, "dry_run": True, "approval_required": True, "execute_allowed": False}

    def record_manual_publish(self, article_id: str, *, url: str, published_at: str, publication_type: str,
                              price: int, confirmed_by: str, notes: str = "", confirmed: bool = False) -> dict[str, Any]:
        if not confirmed: raise ValueError("公開完了確認が必要です")
        state, article = self._find(article_id)
        if not approved_hash_matches(article): raise ValueError("承認済みcontent_hashと一致しません")
        safe_url, note_id = validate_note_url(url)
        if any(a.get("published_url") == safe_url for a in state["articles"]): raise ValueError("同一URLは登録済みです")
        if article.get("status") != "release_package_ready" or not article.get("release_package"):
            raise ValueError("公開パッケージ生成後のみ公開URLを登録できます")
        if not confirmed_by.strip(): raise ValueError("公開確認者が必要です")
        record = {"published_url": safe_url, "published_at": published_at, "note_article_id": note_id,
                  "publication_type": publication_type, "sale_price": max(0, int(price)), "confirmed_by": confirmed_by.strip(),
                  "notes": notes, "content_hash": article["approval"]["content_hash"], "recorded_at": release_now(),
                  "status": "published_manual", "dry_run": True, "external_request_sent": False}
        article.update(record, status="published_manual", updated_at=_now())
        self._history(state, article, "published_manual_recorded"); self._save(state)
        self.revenue.record_publish_history({"article_id": article_id, "channel": "note", **record})
        self._initialize_local_analytics(state, article)
        self._update_metrics(article, posts=1)
        snapshot = self._write_history_snapshot(article)
        drive = self.google.drive_upload(str(snapshot.relative_to(self.root)))
        sheets = self.google.sheets_write("PREVIEW_ONLY", "NoteKPI!A1", [[article_id, safe_url, published_at, "未取得", "未取得", 0]])
        article["publish_workspace_actions"] = {"drive": drive["action_id"], "sheets": sheets["action_id"]}
        self._save(state); self.release.audit("published_manual_recorded", article_id, {"url": safe_url})
        return article

    def _initialize_local_analytics(self, state: dict[str, Any], article: dict[str, Any]) -> dict[str, Any]:
        published_url = str(article.get("published_url", ""))
        callback_id = hashlib.sha256(f"{article['article_id']}:{published_url}".encode("utf-8")).hexdigest()[:16]
        existing = article.get("analytics_initialization")
        if isinstance(existing, dict) and existing.get("callback_id") == callback_id:
            return existing
        initialization = {
            "callback_id": callback_id,
            "status": "initialized",
            "trigger": "manual_published_url_registered",
            "published_url": published_url,
            "initialized_at": _now(),
            "dry_run": True,
            "approval_required": True,
            "execute_allowed": False,
            "external_request_sent": False,
        }
        article["analytics_initialization"] = initialization
        self._history(state, article, "analytics_initialized_local")
        self._save(state)
        return initialization

    def record_kpi(self, article_id: str, *, metric: str, value: Any, measured_at: str, entered_by: str, source: str = "manual") -> dict[str, Any]:
        if metric not in {"pv", "ctr", "sales", "purchases", "likes", "comments"} or value == "": raise ValueError("KPI入力が不正です")
        state, article = self._find(article_id)
        normalized = None if value is None or value == "未取得" else float(value)
        entry = {"metric": metric, "value": normalized, "value_state": "unavailable" if normalized is None else "measured",
                 "measured_at": measured_at, "entered_at": release_now(), "entered_by": entered_by,
                 "source": source, "note_url": article.get("published_url", "")}
        article.setdefault("kpi_history", []).insert(0, entry)
        self._history(state, article, "kpi_manual_entry"); self._save(state)
        self.release.audit("kpi_manual_entry", article_id, {"metric": metric, "value_state": entry["value_state"]})
        return entry

    def production_publish(self, article_id: str) -> dict[str, Any]:
        return {"ok": False, "article_id": article_id, "status": "production_blocked", "external_request_sent": False,
                "dry_run": True, "review_required": True, "production_actions_enabled": False}

    def summary(self) -> dict[str, Any]:
        state = self.load(); articles = state["articles"]
        return {"articles": articles, "history": state["history"], "counts": {status: sum(a.get("status") == status for a in articles) for status in ("review_required", "approval_required", "approved", "note_post_ready", "scheduled_dry_run")}, "dry_run": True, "review_required": True, "production_actions_enabled": False}

    def _update_metrics(self, article: dict[str, Any], *, posts: int) -> None:
        self.business.record_daily_kpi(revenue=int(article.get("revenue_forecast", 0)), articles=posts, note_articles=posts,
                                       posts=posts, pv=int(article.get("pv", 0)), ctr=float(article.get("ctr", 0)),
                                       notes=f"note workspace: {article['article_id']}")

    def _enqueue_mobile_review(self, article: dict[str, Any]) -> dict[str, Any]:
        return self.mobile_review.add(
            target_platform="note", source_id=article["article_id"], title=article["title"], body=article["body"],
            tags=article.get("tags", []), cta=article.get("cta", ""), price=article.get("price", 0),
            publication_type=article.get("visibility", "draft"), planned_publish_at=article.get("planned_publish_at", ""),
            image_path=article.get("eyecatch", ""), source_engine="note_workspace",
            review_result=article.get("review", {}), warnings=list(article.get("review", {}).get("issues", [])),
        )

    def _find(self, article_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        state = self.load(); article = next((a for a in state["articles"] if a.get("article_id") == article_id), None)
        if article is None: raise KeyError(article_id)
        return state, article

    @staticmethod
    def _require_approval(article: dict[str, Any]) -> None:
        if article.get("approval", {}).get("content_hash") != _hash(article): raise ValueError("承認済み本文と一致しません")

    def _save(self, state: dict[str, Any]) -> None:
        state.update(dry_run=True, review_required=True, approval_required=True, execute_allowed=False,
                     production_actions_enabled=False, updated_at=_now()); save_json_atomic(self.path, state)

    @staticmethod
    def _history(state: dict[str, Any], article: dict[str, Any], event: str) -> None:
        state["history"].insert(0, {"history_id": f"nh-{uuid4().hex[:10]}", "article_id": article["article_id"], "title": article["title"], "event": event, "status": article["status"], "at": _now(), "dry_run": True})

    def _write_history_snapshot(self, article: dict[str, Any]) -> Path:
        directory = self.root / "output" / "note_history"; directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{article['article_id']}.json"; save_json_atomic(path, {"article": article, "saved_at": _now(), "dry_run": True}); return path

    @staticmethod
    def _markdown(article: dict[str, Any]) -> str:
        return f"# {article['title']}\n\n{article['body']}\n\n" + " ".join(f"#{tag}" for tag in article["tags"])

    @staticmethod
    def _generate_body(topic: str) -> str:
        return (f"## はじめに\n{topic}を、公開前レビューを保ちながら小さく検証します。\n\n"
                "## 読者の課題\n記事作成から収益確認までが分断されると継続が難しくなります。\n\n"
                "## AIOSでの進め方\nテーマを決め、本文を作り、レビューし、人間承認後に下書きとして保存します。"
                "投稿予約もDryRunで準備し、本番公開は行いません。\n\n"
                "## 収益導線\nPVとCTRを記録し、反応の良いテーマを次の記事へ反映します。\n\n"
                "## まとめ\nまずは安全に下書きを完成させ、数字を確認できる状態を作りましょう。")
