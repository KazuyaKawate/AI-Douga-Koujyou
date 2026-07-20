"""REVENUE-1 presentation-only readiness projections.

Static review data only: no persistence, engine calls, queue access, or execution.
"""

from __future__ import annotations

import streamlit as st


SAFETY = {
    "dry_run": True,
    "approval_required": True,
    "execute_allowed": False,
    "projection_only": True,
    "proposal_only": True,
    "production_allowed": False,
}

READINESS = (
    ("Technical Ready", "READY", "Local projection regression available"),
    ("Business Ready", "BLOCKED", "Owner commercial values pending"),
    ("Legal Ready", "BLOCKED", "Terms, Privacy and commercial-law review pending"),
    ("Revenue Ready", "BLOCKED", "Price, tax and payment evidence pending"),
    ("Owner Ready", "BLOCKED", "Owner final review pending"),
    ("Production Ready", "BLOCKED", "Production prohibited"),
)

OWNER_CHECKLIST = (
    "公開範囲と表示内容", "価格・税区分", "正式問い合わせ窓口", "契約主体と条件",
    "納品条件", "レビュー取得同意", "ケース公開許諾",
)
LEGAL_CHECKLIST = (
    "利用規約の法務レビュー", "Privacyとデータフロー確認", "特商法表示のOwner入力",
    "返金条件", "ケース公開・レビュー掲載の明示同意",
)
REVENUE_CHECKLIST = (
    "正式価格", "税込・税別表示", "支払方法", "売上認識Evidence",
    "受付上限", "返金時の精算条件",
)
FIRST_CUSTOMER_CHECKLIST = (
    "匿名Customer ID", "Owner承認Evidence", "契約同意", "連絡先の安全な保管",
)
DELIVERY_CHECKLIST = (
    "必要資料の完全受領", "納期起算点", "成果物レビュー", "受領確認", "Rollback手順",
)
REVIEW_CHECKLIST = (
    "レビュー依頼の同意", "事実確認", "掲載同意の分離", "匿名化確認", "Owner最終確認",
)


def _rows(items: tuple[str, ...]) -> list[dict[str, str]]:
    return [{"Item": item, "Status": "PENDING REVIEW", "Mode": "PROPOSAL ONLY"} for item in items]


def render_business_home_readiness() -> None:
    st.subheader("REVENUE-1 Limited Beta Readiness")
    labels = (
        ("Beta Readiness", "REVIEW READY"), ("Launch Readiness", "16.7%"),
        ("Owner Status", "FINAL REVIEW REQUIRED"), ("Legal Status", "BLOCKED"),
        ("Revenue Status", "BLOCKED"), ("Remaining Tasks", len(OWNER_CHECKLIST)),
    )
    columns = st.columns(3)
    for index, (label, value) in enumerate(labels):
        columns[index % 3].metric(label, value)
    st.caption("Projection only / approval_required=true / execute_allowed=false / Production NO-GO")


def render_executive_readiness() -> None:
    st.subheader("REVENUE-1 Executive / Proposal Only")
    st.dataframe(
        [{"Readiness": name, "Status": status, "Basis": basis} for name, status, basis in READINESS],
        hide_index=True, use_container_width=True,
    )


def render_commander_readiness() -> None:
    st.subheader("REVENUE-1 Commander / Proposal Only")
    st.markdown("**Remaining Tasks**")
    st.dataframe(_rows(OWNER_CHECKLIST), hide_index=True, use_container_width=True)
    st.markdown("**Launch Checklist**")
    st.dataframe(
        [{"Gate": name, "Status": status, "Action": "HUMAN REVIEW"} for name, status, _ in READINESS],
        hide_index=True, use_container_width=True,
    )
    st.caption("No command execution / no queue write / proposal only")


def render_customer_workspace_readiness() -> None:
    st.subheader("REVENUE-1 Customer Workspace / Templates Only")
    tabs = st.tabs(["First Customer Checklist", "Delivery Checklist", "Review Checklist"])
    for tab, items in zip(tabs, (FIRST_CUSTOMER_CHECKLIST, DELIVERY_CHECKLIST, REVIEW_CHECKLIST)):
        with tab:
            st.dataframe(_rows(items), hide_index=True, use_container_width=True)


def render_official_website_readiness() -> None:
    st.subheader("REVENUE-1 Initial Services / Proposal")
    st.dataframe([{
        "Service": "note記事制作スターター", "Status": "FORMAL CANDIDATE",
        "Price": "PENDING OWNER REVIEW", "Publication": "BLOCKED",
    }], hide_index=True, use_container_width=True)
    legal, revenue = st.tabs(["Legal Checklist", "Revenue Checklist"])
    with legal:
        st.dataframe(_rows(LEGAL_CHECKLIST), hide_index=True, use_container_width=True)
    with revenue:
        st.dataframe(_rows(REVENUE_CHECKLIST), hide_index=True, use_container_width=True)


def render_public_preview_readiness() -> None:
    st.subheader("限定β準備状況 / Public Preview")
    st.info("閲覧専用表示です。募集・問い合わせ受付・契約・決済・送信は無効です。")
    st.dataframe(
        [{"Gate": name, "Status": status} for name, status, _ in READINESS],
        hide_index=True, use_container_width=True,
    )
    st.caption("READ ONLY / PROPOSAL ONLY / OWNER FINAL REVIEW REQUIRED")
