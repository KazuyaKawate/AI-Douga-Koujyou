"""REVENUE-3 first-customer business package presentation; never persists."""

from __future__ import annotations

import streamlit as st


SAFETY = {"local_first": True, "dry_run": True, "approval_required": True,
          "execute_allowed": False, "review_required": True, "projection_only": True,
          "production_allowed": False}

SERVICE_CATALOG = ({
    "Service Name": "note記事制作スターター（候補）",
    "Description": "ヒアリング内容を基にnote記事案を制作する限定β候補",
    "Deliverables": "記事ドラフト / タイトル案 / 公開前チェックリスト",
    "Estimated Days": "必要資料受領後3〜5営業日（Proposal）",
},)

PRICING = tuple({"Package": name, "Price": "TBD / OWNER REVIEW", "Status": "PROPOSAL ONLY"}
                for name in ("Starter", "Standard", "Premium"))

ESTIMATE = (
    ("Estimate ID", "PREVIEW-ONLY"), ("Customer", "未入力"),
    ("Service", "未選択"), ("Package", "未選択"), ("Price/Tax", "未承認"),
    ("Delivery", "未確定"), ("Validity", "未確定"),
)

CONTRACT = (
    ("Scope", "Ownerと顧客の合意対象のみ"),
    ("Deliverables", "見積・契約で確定した成果物"),
    ("Payment", "支払方法・期限・税区分はOwner Review Required"),
    ("Cancellation", "開始点・精算条件はLegal Review Required"),
    ("Review Flow", "Draft → Customer Review → Owner-confirmed Delivery"),
)

CUSTOMER_STEPS = ("Inquiry", "Hearing", "Estimate", "Approval", "Production",
                  "Review", "Delivery", "Completion")


def _summary_rows(items: tuple[tuple[str, str], ...]) -> list[dict[str, str]]:
    return [{"Item": name, "Summary": value, "Status": "REVIEW REQUIRED"} for name, value in items]


def render_first_customer_package() -> None:
    st.subheader("REVENUE-3 First Customer Package")
    completed = 6
    total = 8
    st.progress(completed / total, text=f"Package completion {completed}/{total} = 75%")
    st.caption("Structure prepared; Owner pricing and final approval remain incomplete")
    tabs = st.tabs(["Service Catalog", "Pricing", "Estimate", "Contract", "Invoice", "Customer Checklist"])
    with tabs[0]: st.dataframe(list(SERVICE_CATALOG), hide_index=True, use_container_width=True)
    with tabs[1]: st.dataframe(list(PRICING), hide_index=True, use_container_width=True)
    with tabs[2]:
        st.dataframe(_summary_rows(ESTIMATE), hide_index=True, use_container_width=True)
        st.caption("Display only / Save disabled")
    with tabs[3]: st.dataframe(_summary_rows(CONTRACT), hide_index=True, use_container_width=True)
    with tabs[4]:
        st.dataframe(_summary_rows((("Invoice No.", "PREVIEW"), ("Customer", "未入力"),
            ("Subtotal", "未確定"), ("Tax", "未確定"), ("Total", "未確定"),
            ("Payment Due", "未確定"))), hide_index=True, use_container_width=True)
        st.caption("Invoice Preview / no save / no issue / no send")
    with tabs[5]:
        st.dataframe([{"Step": step, "Status": "NOT STARTED", "Evidence": "NONE"}
                      for step in CUSTOMER_STEPS], hide_index=True, use_container_width=True)


def render_commander_package() -> None:
    st.subheader("REVENUE-3 Commander / Business Package")
    st.metric("Business Package Ready", "75%", "Presentation structure only")
    st.warning("Next Missing Item: Owner-approved pricing and legal evidence")
    st.error("Owner Review Required / execution disabled")


def render_executive_package() -> None:
    st.subheader("REVENUE-3 Executive / Projection Only")
    columns = st.columns(3)
    for column, (label, value) in zip(columns, (
        ("Business Readiness", "75%"), ("Revenue Readiness", "BLOCKED"),
        ("Customer Readiness", "REVIEW REQUIRED"),
    )):
        column.metric(label, value)
    st.caption("No customer accepted / Revenue Actual unchanged / Production NO-GO")
