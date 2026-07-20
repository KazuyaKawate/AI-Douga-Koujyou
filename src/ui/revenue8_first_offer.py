"""REVENUE-8 first-offer review presentation; no commercial execution."""

from __future__ import annotations

import streamlit as st


TBD = "TBD / OWNER REVIEW"
SAFETY = {"local_first": True, "dry_run": True, "approval_required": True,
          "execute_allowed": False, "production_actions_enabled": False,
          "review_required": True, "projection_only": True, "production_allowed": False}

OFFER_FIELDS = ("Offer Name", "Target Customer", "Customer Problems", "Deliverables",
                "Exclusions", "Estimated Delivery Days", "Revision Policy", "Price Status",
                "Approval Status")

PRICING_BOARD = tuple({"Package": name, "Status": "UNDECIDED",
    "Required Decision": "Owner-approved price, tax and scope",
    "Blocking Reason": "Commercial terms not approved"} for name in ("Starter", "Standard", "Premium"))

REVIEW_CARDS = ("Offer", "Pricing", "Deliverables", "Customer Value", "Activation")
SUMMARY = (("Completed Decisions", "0"), ("Remaining Decisions", "12"),
           ("Blocking Items", "Offer 9 + Pricing 3"), ("Production Status", "NO-GO"))


def render_offer_dashboard() -> None:
    st.subheader("REVENUE-8 First Offer Dashboard / Display Only")
    st.dataframe([{"Field": field, "Value": TBD, "Status": "OWNER REVIEW REQUIRED"}
                  for field in OFFER_FIELDS], hide_index=True, use_container_width=True)


def render_pricing_board() -> None:
    st.subheader("REVENUE-8 Pricing Review Board")
    st.dataframe(list(PRICING_BOARD), hide_index=True, use_container_width=True)
    st.caption("No editable values / no automatic approval")


def render_business_home() -> None:
    st.subheader("REVENUE-8 First Offer Readiness")
    columns = st.columns(4)
    for column, (label, value) in zip(columns, (
        ("First Offer Readiness", "DISPLAY READY / 0 APPROVED"),
        ("Pricing Readiness", "0/3 APPROVED"),
        ("Commercial Readiness", "BLOCKED"), ("Remaining Decisions", "12"),
    )):
        column.metric(label, value)
    render_offer_dashboard()
    render_pricing_board()


def render_commander() -> None:
    st.subheader("REVENUE-8 Commander / Offer Review")
    rows = (("Current Revenue Goal", "Complete the first commercial offer review"),
            ("Highest Priority Decision", "Offer Name and service scope"),
            ("Missing Approval", "12 Owner decisions"),
            ("Recommended Owner Action", "Review Offer Name and scope locally"))
    st.dataframe([{"Field": field, "Value": value} for field, value in rows],
                 hide_index=True, use_container_width=True)
    st.caption("No external execution recommendation")


def render_executive() -> None:
    st.subheader("REVENUE-8 Executive / Verified Readiness")
    columns = st.columns(4)
    for column, (label, value) in zip(columns, (
        ("Commercial Readiness", "BLOCKED"), ("Business Readiness", "OWNER REVIEW REQUIRED"),
        ("Revenue Readiness", "¥0 ACTUAL"), ("Activation Readiness", "BLOCKED"),
    )):
        column.metric(label, value)


def render_review_hub() -> None:
    st.subheader("REVENUE-8 First Offer Review Hub")
    st.dataframe([{"Review Card": item, "Status": "REVIEW REQUIRED", "Evidence": "NOT PROVIDED"}
                  for item in REVIEW_CARDS], hide_index=True, use_container_width=True)


def render_readiness_summary() -> None:
    st.subheader("REVENUE-8 Readiness Summary")
    st.dataframe([{"Metric": label, "Verified Value": value} for label, value in SUMMARY],
                 hide_index=True, use_container_width=True)
    st.error("FIRST CUSTOMER ACTIVATION BLOCKED / PRODUCTION NO-GO")
