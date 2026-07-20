"""REVENUE-4 onboarding presentation workflow; no persistence or execution."""

from __future__ import annotations

import streamlit as st


SAFETY = {"local_first": True, "dry_run": True, "approval_required": True,
          "execute_allowed": False, "review_required": True, "projection_only": True,
          "production_allowed": False}

PIPELINE_STAGES = ("New Inquiry", "Hearing", "Estimate", "Waiting Approval",
                   "Production", "Internal Review", "Delivery", "Completed")

CUSTOMER_DETAIL = (
    ("Customer Name", "未入力"), ("Service", "未選択"),
    ("Current Stage", "New Inquiry / TEMPLATE"), ("Next Action", "Owner review"),
    ("Required Documents", "未受領"), ("Internal Notes", "空欄"),
    ("Delivery Status", "NOT STARTED"),
)

DAILY_MISSION = ("Follow-up", "Review", "Delivery Check", "Owner Review")


def _pipeline_rows() -> list[dict[str, object]]:
    return [{"Order": index, "Stage": stage, "Status": "NOT STARTED", "Customer Count": 0}
            for index, stage in enumerate(PIPELINE_STAGES, 1)]


def render_pipeline() -> None:
    st.subheader("REVENUE-4 Customer Pipeline / Display Only")
    st.dataframe(_pipeline_rows(), hide_index=True, use_container_width=True)
    st.caption("0 real customers / no stage mutation / no save")


def render_customer_detail() -> None:
    st.subheader("REVENUE-4 Customer Detail Workspace / Template")
    st.dataframe([{"Field": field, "Value": value, "Mode": "DISPLAY ONLY"}
                  for field, value in CUSTOMER_DETAIL], hide_index=True, use_container_width=True)
    st.caption("No customer data persisted")


def render_business_home() -> None:
    st.subheader("REVENUE-4 Customer Onboarding")
    columns = st.columns(3)
    for column, (label, value) in zip(columns, (
        ("Customer Pipeline", "0 active / 8 stages"),
        ("Current Active Customer", "NONE / TEMPLATE"),
        ("Completion Progress", "0%"),
    )):
        column.metric(label, value)
    render_pipeline()
    st.markdown("**Today's Operational Checklist**")
    st.dataframe([{"Task": item, "Status": "PENDING REVIEW"} for item in DAILY_MISSION],
                 hide_index=True, use_container_width=True)


def render_commander() -> None:
    st.subheader("REVENUE-4 Commander / Onboarding Projection")
    st.write("**Current Customer:** NONE / TEMPLATE")
    st.write("**Next Business Action:** Owner onboarding review")
    st.write("**Pending Owner Decision:** Customer acceptance and commercial terms")
    st.metric("Workflow Progress", "0%", "0/8 stages")
    st.caption("Proposal only / no Queue write / no execution")


def render_executive() -> None:
    st.subheader("REVENUE-4 Executive / Projection Only")
    columns = st.columns(4)
    for column, (label, value) in zip(columns, (
        ("Pipeline Health", "EMPTY / REVIEW READY"), ("Customer Completion", "0%"),
        ("Estimated Revenue", "¥0 PROJECTION"), ("Verified Revenue", "¥0 ACTUAL"),
    )):
        column.metric(label, value)


def render_daily_mission() -> None:
    st.subheader("REVENUE-4 Daily Mission")
    st.dataframe([{"Task": item, "Status": "PENDING", "Owner Review": "REQUIRED"}
                  for item in DAILY_MISSION], hide_index=True, use_container_width=True)


def render_review_hub() -> None:
    st.subheader("REVENUE-4 Onboarding Review Hub")
    st.dataframe([
        {"Readiness": "Onboarding readiness", "Status": "OWNER REVIEW REQUIRED"},
        {"Readiness": "Delivery readiness", "Status": "NOT READY"},
        {"Readiness": "Customer review readiness", "Status": "NOT READY"},
    ], hide_index=True, use_container_width=True)
    st.caption("Read only / Production NO-GO")
