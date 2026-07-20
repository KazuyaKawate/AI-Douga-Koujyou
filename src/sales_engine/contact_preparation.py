"""CONTACT-1 inquiry preparation as an immutable local projection."""

from __future__ import annotations

from copy import deepcopy


SAFETY = {
    "dry_run": True,
    "projection_only": True,
    "review_required": True,
    "approval_required": True,
    "execute_allowed": False,
    "input_persistence_allowed": False,
    "mail_send_allowed": False,
    "google_allowed": False,
    "webhook_allowed": False,
    "api_allowed": False,
    "quick_actions_enabled": False,
}

SERVICES = (
    {"service": "note記事制作", "description": "企画・構成・本文・公開前レビュー用原稿を準備します。", "price": "¥15,000〜 / Proposal", "lead_time": "5営業日〜 / Proposal", "available": True},
    {"service": "Threads投稿セット", "description": "独自構成の短文投稿案を5本単位で準備します。", "price": "¥8,000〜 / Proposal", "lead_time": "3営業日〜 / Proposal", "available": True},
    {"service": "公式サイト・LP原稿", "description": "価値提案、ページ構成、本文、FAQ案を準備します。", "price": "¥30,000〜 / Proposal", "lead_time": "10営業日〜 / Proposal", "available": True},
    {"service": "コンテンツ導線レビュー", "description": "note・Threads・公式サイトの導線をレビューします。", "price": "¥10,000〜 / Proposal", "lead_time": "5営業日〜 / Proposal", "available": True},
)

FAQ = (
    {"question": "相談だけでも可能ですか？", "answer": "可能です。正式な受付条件と連絡先はOwner最終レビュー後に確定します。"},
    {"question": "価格と納期は確定ですか？", "answer": "未確定です。表示内容はProposalで、要件確認後に人間が最終決定します。"},
    {"question": "修正は含まれますか？", "answer": "修正回数・範囲は見積時に個別提示します。現時点では未確定です。"},
    {"question": "AI生成物をそのまま公開しますか？", "answer": "いいえ。公開前に人間レビューと承認を必須とします。"},
)


def _template(fields: tuple[str, ...]) -> dict[str, object]:
    return {"template_only": True, "persisted": False, "fields": fields, "values": {key: "" for key in fields}}


def build_contact_preparation() -> dict[str, object]:
    """Return a detached, side-effect-free CONTACT-1 review projection."""
    services = deepcopy(SERVICES)
    return {
        **SAFETY,
        "phase": "CONTACT-1 INQUIRY PREPARATION",
        "entry_point": "Business Home",
        "public_preview": {
            "status": "REVIEW_REQUIRED",
            "service_catalog": services,
            "production_published": False,
            "contact_submission_available": False,
        },
        "services": services,
        "production_flow": ("問い合わせ方法を確認", "人間による受付", "ヒアリング", "見積・条件提示", "承認", "制作", "レビュー", "納品"),
        "inquiry_method": "Owner最終レビュー後に公式サイト上で案内予定。現在は閲覧のみで受付停止中。",
        "onboarding_flow": ("サービス確認", "問い合わせ", "ヒアリング", "見積確認", "双方合意", "制作開始"),
        "unsupported": ("無断転載", "権利侵害を伴う制作", "虚偽・違法・有害コンテンツ", "無審査の自動公開", "成果保証", "緊急即日対応"),
        "faq": deepcopy(FAQ),
        "customer_workspace": {
            "inquiry": _template(("name", "organization", "reply_to", "service", "purpose", "budget", "desired_date", "details")),
            "estimate": _template(("service", "scope", "deliverables", "price_proposal", "lead_time_proposal", "revision_terms", "valid_until")),
            "hearing": _template(("background", "goal", "audience", "requirements", "references", "constraints", "success_criteria")),
        },
        "business_home": {"inquiry_preparation": 100, "service_readiness": 100, "price_decision": 0, "publication_readiness": 0, "display_mode": "PROPOSAL ONLY"},
        "executive": {"Service Ready": "READY", "Contact Ready": "READY", "Launch Ready": "NO-GO", "Owner Ready": "REVIEW REQUIRED", "Legal Ready": "REVIEW REQUIRED", "Revenue Ready": "NO-GO"},
        "final_judgement": ("CONTACT READY", "OWNER FINAL REVIEW REQUIRED", "PRODUCTION NO-GO"),
    }
