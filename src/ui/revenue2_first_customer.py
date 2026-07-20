"""REVENUE-2 first-customer presentation projections; no persistence or execution."""

from __future__ import annotations

import streamlit as st


SAFETY = {"dry_run": True, "projection_only": True, "review_required": True,
          "approval_required": True, "execute_allowed": False, "production_allowed": False}

SALES = {
    "Inquiry Checklist": ("問い合わせ経路確認", "対象顧客確認", "同意確認", "返信案レビュー"),
    "Estimate Checklist": ("要件確認", "価格・税確認", "納期確認", "見積Ownerレビュー"),
    "Order Checklist": ("契約主体確認", "注文内容確認", "支払条件確認", "受注Evidence確認"),
}
DELIVERY = ("必要資料", "制作範囲", "納品形式", "受領確認", "Rollback")
REVIEW = ("Publication Review", "Delivery Review", "Customer Review")
BLOCKERS = ("Owner final review", "Legal review", "Price/tax/payment evidence", "Customer consent")


def _pending(items: tuple[str, ...]) -> list[dict[str, str]]:
    return [{"Item": item, "Status": "PENDING REVIEW", "Mode": "PROPOSAL ONLY"} for item in items]


def render_business_home() -> None:
    st.subheader("REVENUE-2 First Customer Execution / Projection")
    cols = st.columns(3)
    values = (
        ("Today's Revenue Mission", "First customer package review"),
        ("Today's First Customer", "TEMPLATE / 0 actual"),
        ("Today's Publish Package", "REVIEW REQUIRED"),
    )
    for col, (label, value) in zip(cols, values): col.metric(label, value)
    tabs = st.tabs(["Today's Sales Checklist", "Today's Delivery Checklist", "Today's Review Checklist"])
    with tabs[0]: st.dataframe(_pending(tuple(SALES)), hide_index=True, use_container_width=True)
    with tabs[1]: st.dataframe(_pending(DELIVERY), hide_index=True, use_container_width=True)
    with tabs[2]: st.dataframe(_pending(REVIEW), hide_index=True, use_container_width=True)
    st.caption("Business Home is the only entry point / DryRun / Production NO-GO")


def render_customer_workspace() -> None:
    st.subheader("REVENUE-2 First Customer Workspace / Template")
    st.dataframe([
        {"Field": "First Customer Progress", "Value": "0% / NOT STARTED"},
        {"Field": "Required Documents", "Value": "PENDING"},
        {"Field": "Delivery Status", "Value": "NOT STARTED"},
        {"Field": "Review Status", "Value": "NOT STARTED"},
        {"Field": "Verified Revenue Status", "Value": "¥0 / NO EVIDENCE"},
    ], hide_index=True, use_container_width=True)


def render_commander() -> None:
    st.subheader("REVENUE-2 Commander / Proposal Only")
    st.info("Today's Mission: 初回案件パッケージをOwnerがレビューする")
    st.write("**Next Action:** Owner ChecklistとEvidenceを確認")
    st.write("**Remaining Blockers:** " + " / ".join(BLOCKERS))
    st.warning("Owner Review: REQUIRED / command execution disabled")


def render_sales() -> None:
    st.subheader("REVENUE-2 Sales / First Customer")
    tabs = st.tabs(list(SALES))
    for tab, items in zip(tabs, SALES.values()):
        with tab: st.dataframe(_pending(items), hide_index=True, use_container_width=True)


def render_marketing() -> None:
    st.subheader("REVENUE-2 Marketing / Today's Package")
    st.dataframe([{"Channel": channel, "Status": "PROPOSAL / NOT PUBLISHED"} for channel in
                  ("Today's Content", "Today's Website", "Today's note", "Today's Threads")],
                 hide_index=True, use_container_width=True)


def render_review_hub() -> None:
    st.subheader("REVENUE-2 Review Hub / Read Only")
    st.dataframe(_pending(REVIEW), hide_index=True, use_container_width=True)


def render_executive() -> None:
    st.subheader("REVENUE-2 Executive")
    cols = st.columns(3)
    for col, (label, value) in zip(cols, (("Today's KPI", "0 verified events"),
        ("Today's Revenue", "¥0 VERIFIED ACTUAL"), ("Today's Progress", "0%"))):
        col.metric(label, value)


def render_revenue() -> None:
    st.subheader("REVENUE-2 Revenue / Projection")
    cols = st.columns(4)
    for col, (label, value) in zip(cols, (("Verified Actual", "¥0"), ("Pending", "¥0"),
        ("Projection", "¥0"), ("Completion Rate", "0%"))): col.metric(label, value)
    st.caption("Proposal is never counted as revenue / verified evidence only")


def render_website() -> None:
    st.subheader("REVENUE-2 Website / Proposal")
    st.dataframe([
        {"Item": "Current Offer", "Value": "note記事制作スターター", "Status": "PROPOSAL"},
        {"Item": "Current Campaign", "Value": "限定β 1名候補", "Status": "NOT PUBLISHED"},
        {"Item": "Current CTA", "Value": "Owner review", "Status": "DISABLED"},
    ], hide_index=True, use_container_width=True)
