from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.publish_engine.note_publisher import NotePublisher
from src.publish_engine.safe_publish_queue import (
    APPROVAL_REQUIRED,
    APPROVED,
    DRY_RUN_FAILED,
    DRY_RUN_QUEUED,
    DRY_RUN_SUCCEEDED,
    REVIEW,
    SafePublishQueue,
)
from src.publish_engine.safety_guard import LocalAuditLog, PublishSafetyError, PublishSafetyGuard, content_hash, mask_secrets, now
from src.publish_engine.threads_publisher import ThreadsPublisher
from src.utils.config import PROJECT_ROOT
from src.utils.json_store import load_json, save_json_atomic


FORBIDDEN = ("必ず儲かる", "絶対に稼げる", "的中保証", "治ります", "法律上問題ない", "個人情報")
PERSONAL = re.compile(r"(?:\d{3}-\d{4}-\d{4}|\b\d{3}-\d{2}-\d{4}\b|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})")
ASSERTIVE = ("絶対", "確実に", "100%", "断言します")
URL = re.compile(r"https?://[^\s)\]]+")


class CommanderMonetizationFlow:
    """Local-first, two-stage note -> Threads revenue workflow."""

    def __init__(
        self,
        *,
        root: str | Path = PROJECT_ROOT,
        note_publisher: Any | None = None,
        threads_publisher: Any | None = None,
    ) -> None:
        self.root = Path(root)
        self.path = self.root / "config" / "commander_monetization.json"
        self.audit = LocalAuditLog(self.root / "config" / "monetization_audit.json")
        self.queue = SafePublishQueue(self.root / "config" / "monetization_publish_queue.json")
        self.guard = PublishSafetyGuard()
        self.note_publisher = note_publisher or NotePublisher()
        self.threads_publisher = threads_publisher or ThreadsPublisher()

    def load(self) -> dict[str, Any]:
        state = load_json(self.path, default={}) or {}
        state.setdefault("workflows", [])
        state.setdefault("local_first", True)
        state.setdefault("dry_run", True)
        state.setdefault("review_required", True)
        state.setdefault("production_actions_enabled", False)
        return state

    def create_and_review(self, *, instruction: str, cta_url: str = "") -> dict[str, Any]:
        state = self.load()
        note = self._build_note(instruction, cta_url)
        threads = self._build_threads(note)
        signature = content_hash({"instruction": instruction, "note": note, "threads": threads})
        existing = next((w for w in state["workflows"] if w.get("request_hash") == signature and w.get("stage") != "DryRunFailed"), None)
        if existing:
            return existing
        note_review = self._review_note(note, state)
        threads_review = self._review_threads(threads, note, state)
        workflow = {
            "workflow_id": f"money-{uuid4().hex[:12]}",
            "request_hash": signature,
            "stage": "ApprovalRequired",
            "current_step": "人間レビュー待ち",
            "instruction": instruction,
            "content_version": 1,
            "note": note,
            "threads": threads,
            "reviews": {"note": note_review, "threads": threads_review},
            "approval": {},
            "dry_run_result": {},
            "next_action": "本文と警告を確認し、人間承認を実行",
            "audit_log_path": str(self.audit.path),
            "created_at": now(),
            "updated_at": now(),
        }
        for channel, content in (("note", note), ("threads", threads)):
            queued = self.queue.create(channel=channel, content_id=content["content_id"], content_version=1, digest=content_hash(content))
            self.queue.transition(queued["queue_id"], REVIEW)
            self.queue.transition(queued["queue_id"], APPROVAL_REQUIRED)
            workflow[f"{channel}_queue_id"] = queued["queue_id"]
        state["workflows"].insert(0, workflow)
        self._save(state)
        self.audit.append("workflow_created_reviewed", self._audit_payload(workflow))
        return workflow

    def approve(self, workflow_id: str, *, approver: str) -> dict[str, Any]:
        if not approver.strip():
            raise ValueError("approver is required")
        state, workflow = self._find(workflow_id)
        if not all(review.get("passed") for review in workflow["reviews"].values()):
            raise ValueError("review warnings must be resolved before approval")
        approval_id = f"approval-{uuid4().hex[:12]}"
        approval = {
            "approval_id": approval_id,
            "status": "approved",
            "content_hash": content_hash({"note": workflow["note"], "threads": workflow["threads"]}),
            "content_hashes": {"note": content_hash(workflow["note"]), "threads": content_hash(workflow["threads"])},
            "approver": approver.strip(),
            "approved_at": now(),
            "approved_content_version": workflow["content_version"],
        }
        workflow["approval"] = approval
        workflow["stage"] = "Approved"
        workflow["current_step"] = "Dry Run投稿待ち"
        workflow["next_action"] = "承認済みnote／ThreadsをDry Run投稿"
        workflow["updated_at"] = now()
        self.queue.transition(workflow["note_queue_id"], APPROVED, approval_id=approval_id)
        self.queue.transition(workflow["threads_queue_id"], APPROVED, approval_id=approval_id)
        self._save(state)
        self.audit.append("workflow_human_approved", self._audit_payload(workflow))
        return workflow

    def update_content(self, workflow_id: str, *, channel: str, content: dict[str, Any]) -> dict[str, Any]:
        state, workflow = self._find(workflow_id)
        if channel not in {"note", "threads"}:
            raise ValueError("unsupported channel")
        workflow[channel] = dict(content)
        workflow["content_version"] = int(workflow.get("content_version", 1)) + 1
        workflow["approval"] = {}
        workflow["stage"] = "ApprovalRequired"
        workflow["current_step"] = "本文変更により再承認待ち"
        workflow["next_action"] = "変更内容を再レビューして承認"
        workflow["reviews"][channel] = self._review_note(content, state) if channel == "note" else self._review_threads(content, workflow["note"], state)
        for queue_channel in ("note", "threads"):
            queue_content = workflow[queue_channel]
            queued = self.queue.create(
                channel=queue_channel,
                content_id=queue_content["content_id"],
                content_version=workflow["content_version"],
                digest=content_hash(queue_content),
            )
            self.queue.transition(queued["queue_id"], REVIEW)
            self.queue.transition(queued["queue_id"], APPROVAL_REQUIRED)
            workflow[f"{queue_channel}_queue_id"] = queued["queue_id"]
        workflow["updated_at"] = now()
        self._save(state)
        self.audit.append("approval_invalidated_content_changed", self._audit_payload(workflow))
        return workflow

    def dry_run_publish(self, workflow_id: str) -> dict[str, Any]:
        state, workflow = self._find(workflow_id)
        if workflow.get("stage") == "DryRunSucceeded":
            return workflow
        approval = workflow.get("approval", {})
        combined = content_hash({"note": workflow["note"], "threads": workflow["threads"]})
        if approval.get("content_hash") != combined:
            workflow["approval"] = {}
            workflow["stage"] = "ApprovalRequired"
            workflow["next_action"] = "本文変更を検出。再承認が必要"
            self._save(state)
            raise PublishSafetyError("approval_invalidated_by_content_change")

        results: dict[str, Any] = {}
        for channel, publisher in (("note", self.note_publisher), ("threads", self.threads_publisher)):
            content = workflow[channel]
            channel_approval = {**approval, "content_hash": approval["content_hashes"][channel]}
            self.guard.enforce(
                channel=channel,
                dry_run=True,
                production_actions_enabled=False,
                review_required=True,
                approval=channel_approval,
                content=content,
                content_version=workflow["content_version"],
            )
            queue_id = workflow[f"{channel}_queue_id"]
            queued = self.queue.transition(queue_id, DRY_RUN_QUEUED, approval_id=approval["approval_id"])
            cached = self.queue.result_for(queued["idempotency_key"])
            if cached:
                results[channel] = {**cached, "idempotent_replay": True}
                self.queue.transition(queue_id, DRY_RUN_SUCCEEDED)
                continue
            planned = self._planned_request(channel, content)
            try:
                publish_result = publisher.publish({"content": content, "approval": channel_approval}, dry_run=True)
                result = {
                    "status": "dry_run",
                    "channel": channel,
                    "planned_request": planned,
                    "publisher_result": mask_secrets(publish_result),
                    "external_request_sent": False,
                    "retry_scheduled": False,
                }
                self.queue.save_result(queued["idempotency_key"], result)
                self.queue.transition(queue_id, DRY_RUN_SUCCEEDED)
                results[channel] = result
            except Exception as exc:
                self.queue.transition(queue_id, DRY_RUN_FAILED, error_summary=type(exc).__name__)
                results[channel] = {"status": "dry_run_failed", "error_summary": type(exc).__name__, "retry_scheduled": False, "external_request_sent": False}
                workflow["stage"] = "DryRunFailed"
                workflow["dry_run_result"] = results
                workflow["next_action"] = "安全停止。内容と設定を確認（自動再試行なし）"
                self._save(state)
                self.audit.append("workflow_dry_run_failed", self._audit_payload(workflow))
                return workflow

        workflow["stage"] = "DryRunSucceeded"
        workflow["current_step"] = "Dry Run完了"
        workflow["dry_run_result"] = results
        workflow["next_action"] = "人間がDry Run結果を確認。本番公開には進まない"
        workflow["updated_at"] = now()
        self._save(state)
        self.audit.append("workflow_dry_run_succeeded", self._audit_payload(workflow))
        return workflow

    def summary(self) -> dict[str, Any]:
        workflows = self.load()["workflows"]
        return {"workflows": workflows, "latest": workflows[0] if workflows else {}, "audit_log_path": str(self.audit.path)}

    def _find(self, workflow_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        state = self.load()
        workflow = next((row for row in state["workflows"] if row.get("workflow_id") == workflow_id), None)
        if workflow is None:
            raise KeyError(workflow_id)
        return state, workflow

    def _save(self, state: dict[str, Any]) -> None:
        state.update({"local_first": True, "dry_run": True, "review_required": True, "production_actions_enabled": False, "updated_at": now()})
        save_json_atomic(self.path, state)

    @staticmethod
    def _build_note(instruction: str, cta_url: str) -> dict[str, Any]:
        topic = instruction.strip() or "AIOSで初収益を作る実践手順"
        sections = [
            "## はじめに\nこの記録は、AIOSを使って小さな収益導線を検証する過程をまとめたものです。成果は環境や実行条件で変わり、収益を保証するものではありません。",
            "## 今回の課題\n作業を増やすのではなく、読者の悩みを一つに絞り、noteとThreadsを同じテーマで接続します。事実として確認できた操作と、今後検証する仮説を分けて記録します。",
            "## 実践手順\n1. 読者の課題を一文で定義します。\n2. 無料部分で判断材料を提供します。\n3. 続きに具体的なテンプレートやチェックリストを置きます。\n4. Threadsでは要点だけを紹介し、記事へ自然に案内します。",
            "## 事実と仮説\n事実: 本フローはDry Runと人間レビューを必須にしています。仮説: 同じテーマを継続的に検証することで、読者反応の高い導線を見つけやすくなります。",
            "## 次の検証\n閲覧数、CTA反応、読了後の行動を記録し、反応がない場合はタイトルと導入を一つずつ変更します。複数要素を同時に変えず、結果を比較できる状態にします。",
            "## まとめ\n大きな自動化より、レビュー可能な小さな公開単位を積み重ねます。内容を確認したうえで、次のDry Runへ進みます。",
        ]
        body = f"# {topic[:60]}\n\n" + "\n\n".join(sections)
        if cta_url:
            body += f"\n\n詳しいチェックリスト: {cta_url}"
        return {"content_id": f"note-{uuid4().hex[:10]}", "type": "note", "title": topic[:60], "body": body, "cta": "実践チェックリストを確認する", "cta_url": cta_url, "revenue_purpose": "初収益につながるnote導線の検証"}

    @staticmethod
    def _build_threads(note: dict[str, Any]) -> dict[str, Any]:
        text = (
            f"{note['title']}\n\n"
            "収益化で先に自動化すべきなのは、投稿ボタンではなくレビュー可能な導線でした。\n"
            "・事実と仮説を分ける\n・CTAを一つに絞る\n・反応を記録して一要素ずつ改善する\n\n"
            "詳しい手順は承認済みnote記事にまとめます。"
        )[:500]
        return {"content_id": f"threads-{uuid4().hex[:10]}", "type": "threads", "title": note["title"], "text": text, "cta": "詳しい手順はnoteへ", "source_note_id": note["content_id"], "revenue_purpose": note["revenue_purpose"]}

    def _review_note(self, note: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        body = str(note.get("body", ""))
        title = str(note.get("title", ""))
        warnings = []
        self._check_common(title + " " + body, warnings)
        if not 8 <= len(title) <= 80: warnings.append("タイトル長を確認")
        if len(body) < 500: warnings.append("本文が短すぎます")
        if "事実" not in body or "仮説" not in body: warnings.append("事実と推測の区別が不足")
        if not note.get("cta"): warnings.append("CTAがありません")
        if note.get("revenue_purpose") == "": warnings.append("収益化目的がありません")
        for link in URL.findall(body):
            if not link.startswith("https://"): warnings.append("外部リンクはHTTPS必須")
        duplicates = [w for w in state.get("workflows", []) if w.get("note", {}).get("title") == title]
        if duplicates: warnings.append("重複記事タイトル")
        return {"passed": not warnings, "warnings": warnings, "checks": ["title", "body_quality", "fact_vs_inference", "forbidden", "personal_data", "misleading", "cta", "length", "revenue_alignment", "duplicate", "external_links"]}

    def _review_threads(self, threads: dict[str, Any], note: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        text = str(threads.get("text", ""))
        warnings = []
        self._check_common(text, warnings)
        if not text.strip(): warnings.append("空本文")
        if len(text) > 500: warnings.append("Threads文字数超過")
        if not threads.get("cta"): warnings.append("CTAがありません")
        if threads.get("source_note_id") != note.get("content_id"): warnings.append("元記事との整合不良")
        duplicates = [w for w in state.get("workflows", []) if w.get("threads", {}).get("text") == text]
        if duplicates: warnings.append("重複投稿")
        return {"passed": not warnings, "warnings": warnings, "checks": ["length", "empty", "forbidden", "personal_data", "overclaim", "duplicate", "cta", "source_alignment"]}

    @staticmethod
    def _check_common(text: str, warnings: list[str]) -> None:
        if any(token in text for token in FORBIDDEN): warnings.append("禁止表現を検出")
        if PERSONAL.search(text): warnings.append("個人情報らしき文字列を検出")
        if any(token in text for token in ASSERTIVE): warnings.append("過度な断定表現")

    @staticmethod
    def _planned_request(channel: str, content: dict[str, Any]) -> dict[str, Any]:
        if channel == "note":
            return {"adapter": "note_local_dry_run", "operation": "create_draft_preview", "title": content.get("title", ""), "body_length": len(content.get("body", "")), "external_send": False}
        return {"adapter": "meta_official_threads_api", "operations": ["create_container_planned", "publish_container_planned"], "text_length": len(content.get("text", "")), "external_send": False}

    @staticmethod
    def _audit_payload(workflow: dict[str, Any]) -> dict[str, Any]:
        return {"workflow_id": workflow.get("workflow_id"), "stage": workflow.get("stage"), "content_version": workflow.get("content_version"), "note_hash": content_hash(workflow.get("note", {})), "threads_hash": content_hash(workflow.get("threads", {})), "approval": workflow.get("approval", {}), "dry_run_result": workflow.get("dry_run_result", {})}
