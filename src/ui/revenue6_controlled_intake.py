"""REVENUE-6 controlled intake presentation; no customer persistence or execution."""

from __future__ import annotations

import streamlit as st


TBD = "TBD / OWNER REVIEW"
SAFETY = {"local_first": True, "dry_run": True, "approval_required": True,
          "execute_allowed": False, "production_actions_enabled": False,
          "review_required": True, "projection_only": True, "production_allowed": False}

INTAKE_FIELDS = ("Customer Name", "Company", "Contact", "Requested Service", "Budget",
                 "Desired Delivery Date", "Notes")
QUALIFICATION = ("Target customer match", "Required information received", "Scope understood",
                 "Budget confirmed", "Timeline confirmed")
OFFER_REVIEW = (("Selected package", TBD), ("Deliverables", TBD),
                ("Price", TBD), ("Estimated schedule", TBD))
RISK_REVIEW = ("Missing information", "Legal blockers", "Owner blockers", "Customer blockers")


def render_intake_package() -> None:
    st.subheader("REVENUE-6 Controlled First Customer Intake")
    tabs = st.tabs(["Customer Intake Form", "Qualification Checklist", "Offer Review", "Risk Review"])
    with tabs[0]:
        st.dataframe([{"Field": field, "Value": "", "Mode": "DISPLAY ONLY / NO SAVE"}
                      for field in INTAKE_FIELDS], hide_index=True, use_container_width=True)
        st.caption("Empty template / no customer registration")
    with tabs[1]:
        st.dataframe([{"Check": item, "Status": "NOT VERIFIED"} for item in QUALIFICATION],
                     hide_index=True, use_container_width=True)
    with tabs[2]:
        st.dataframe([{"Item": item, "Value": value, "Status": "OWNER REVIEW REQUIRED"}
                      for item, value in OFFER_REVIEW], hide_index=True, use_container_width=True)
    with tabs[3]:
        st.dataframe([{"Risk": item, "Status": "OPEN", "Evidence": "NOT PROVIDED"}
                      for item in RISK_REVIEW], hide_index=True, use_container_width=True)


def render_business_home() -> None:
    st.subheader("REVENUE-6 Intake Status")
    columns = st.columns(3)
    for column, (label, value) in zip(columns, (
        ("Intake Readiness", "REVIEW PACKAGE READY"),
        ("Current Intake Status", "BLOCKED / 0 CUSTOMERS"),
        ("Blocking Items", "4 OPEN"),
    )):
        column.metric(label, value)
    render_intake_package()
    st.caption("Business Home only / DryRun / Activation BLOCKED / Production NO-GO")


def render_commander() -> None:
    st.subheader("REVENUE-6 Commander / Intake Review")
    st.write("**Next Intake Action:** Owner reviews the empty intake package locally")
    st.write("**Highest Priority Blocker:** Owner-approved first offer")
    st.write("**Required Owner Decision:** Service, price, payment, legal acknowledgement")
    st.caption("No customer contact recommendation / no execution")


def render_executive() -> None:
    st.subheader("REVENUE-6 Executive / Verified Values")
    columns = st.columns(4)
    for column, (label, value) in zip(columns, (
        ("Intake Readiness", "REVIEW READY"), ("Qualified Customers", "0"),
        ("Pending Customers", "0"), ("Activation Status", "BLOCKED"),
    )):
        column.metric(label, value)
    st.caption("Real Customers 0 / Verified Revenue ¥0 / Production NO-GO")
