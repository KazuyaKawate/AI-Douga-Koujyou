"""REVENUE-5 owner approval package: static local review projections only."""

from __future__ import annotations

import streamlit as st


TBD = "TBD / OWNER REVIEW"
ALLOWED_STATUSES = ("UNDECIDED", "DRAFT", "REVIEW REQUIRED", "APPROVED", "REJECTED", "BLOCKED")
SAFETY = {"local_first": True, "dry_run": True, "approval_required": True,
          "execute_allowed": False, "production_actions_enabled": False,
          "external_request_sent": False, "review_required": True,
          "projection_only": True, "production_allowed": False}

_DECISIONS = (
    ("R5-OD-01", "Service to sell first", "note記事制作スターター（候補）", "Service scope and Owner signature", "Offer cannot be finalized"),
    ("R5-OD-02", "Starter price", TBD, "Approved price and cost basis", "Estimate blocked"),
    ("R5-OD-03", "Standard price", TBD, "Approved price and cost basis", "Estimate blocked"),
    ("R5-OD-04", "Premium price", TBD, "Approved price and cost basis", "Estimate blocked"),
    ("R5-OD-05", "Tax handling", TBD, "Tax review evidence", "Price display blocked"),
    ("R5-OD-06", "Payment timing", TBD, "Owner-approved payment terms", "Contract blocked"),
    ("R5-OD-07", "Accepted payment methods", TBD, "Account and reconciliation readiness", "Payment request blocked"),
    ("R5-OD-08", "Delivery period", TBD, "Capacity and delivery basis", "Offer blocked"),
    ("R5-OD-09", "Revision limit", TBD, "Scope and revision definition", "Contract blocked"),
    ("R5-OD-10", "Cancellation policy", TBD, "Legal review evidence", "Contract blocked"),
    ("R5-OD-11", "Refund policy", TBD, "Legal review evidence", "Contract blocked"),
    ("R5-OD-12", "Customer consent wording", TBD, "Approved wording and version", "Customer acceptance blocked"),
    ("R5-OD-13", "Legal review status", "NOT VERIFIED", "Actual legal review evidence", "Activation blocked"),
    ("R5-OD-14", "Production activation decision", "NO-GO", "Separate explicit Owner approval", "Production remains disabled"),
)

OWNER_DECISIONS = tuple({"Decision ID": did, "Decision Type": dtype, "Current Value": current,
    "Status": "UNDECIDED", "Required Evidence": evidence, "Owner Decision": "NOT PROVIDED",
    "Blocking Impact": impact} for did, dtype, current, evidence, impact in _DECISIONS)

FIRST_OFFER = (
    ("Offer Name", TBD), ("Target Customer", TBD), ("Customer Problem", TBD),
    ("Deliverables", TBD), ("Exclusions", TBD), ("Delivery Days", TBD),
    ("Revision Count", TBD), ("Price", TBD), ("Tax Treatment", TBD),
    ("Payment Timing", TBD), ("Required Customer Materials", TBD),
)

LEGAL_ITEMS = ("Service scope confirmed", "Price confirmed", "Tax treatment confirmed",
    "Payment terms confirmed", "Cancellation terms confirmed", "Refund terms confirmed",
    "Privacy wording confirmed", "Customer consent confirmed", "Estimate wording reviewed",
    "Contract wording reviewed", "Invoice wording reviewed", "Delivery acceptance wording reviewed")

ACTIVATION_ITEMS = ("Owner price approval", "Owner service approval", "Owner payment approval",
    "Owner legal review acknowledgement", "Customer consent wording approval", "First customer identified",
    "Estimate reviewed", "Contract reviewed", "Payment method ready",
    "Production execution separately approved")

EVIDENCE_REGISTRY = tuple({"Decision ID": row["Decision ID"], "Decision Type": row["Decision Type"],
    "Evidence File": "NOT PROVIDED", "Evidence Status": "NOT PROVIDED", "Reviewed By": "NOT PROVIDED",
    "Review Date": "NOT PROVIDED", "Notes": ""} for row in OWNER_DECISIONS)

COMPLETION = {"Display Package Completion": "100%", "Owner Decision Completion": "0/14 = 0%",
              "Legal Evidence Completion": "0/12 = 0%", "Activation Gate Completion": "0/10 = 0%"}


def render_owner_decision_center() -> None:
    st.subheader("REVENUE-5 Owner Decision Center")
    st.dataframe(list(OWNER_DECISIONS), hide_index=True, use_container_width=True)
    st.caption("No automatic approval / allowed statuses: " + " / ".join(ALLOWED_STATUSES))


def render_first_offer() -> None:
    st.subheader("First Offer Definition / Presentation Only")
    st.dataframe([{"Field": field, "Value": value, "Status": "OWNER REVIEW REQUIRED"}
                  for field, value in FIRST_OFFER], hide_index=True, use_container_width=True)


def render_legal_readiness() -> None:
    st.subheader("Legal and Consent Readiness")
    st.error("Legal approval: NOT VERIFIED / No legal compliance claim")
    st.dataframe([{"Item": item, "Status": "NOT VERIFIED", "Evidence": "NOT PROVIDED"}
                  for item in LEGAL_ITEMS], hide_index=True, use_container_width=True)


def render_activation_gate() -> None:
    st.subheader("First Customer Activation Gate / Fail Closed")
    st.dataframe([{"Gate": item, "Status": "BLOCKED", "Evidence": "NOT PROVIDED"}
                  for item in ACTIVATION_ITEMS], hide_index=True, use_container_width=True)
    st.error("FIRST CUSTOMER ACTIVATION BLOCKED")
    st.caption("No activation control is provided")


def render_evidence_registry() -> None:
    st.subheader("Decision Evidence Registry / Local Display Only")
    st.dataframe(list(EVIDENCE_REGISTRY), hide_index=True, use_container_width=True)


def render_business_home() -> None:
    st.subheader("REVENUE-5 Owner Approval Package")
    columns = st.columns(4)
    for column, (label, value) in zip(columns, COMPLETION.items()): column.metric(label, value)
    st.write("**Blocking Items:** 14 Owner decisions / 12 legal evidence items / 10 activation gates")
    st.warning("Recommended Next Owner Action: review Service to sell first and provide traceable evidence")
    render_owner_decision_center()
    render_first_offer()
    render_legal_readiness()
    render_activation_gate()
    render_evidence_registry()


def render_commander() -> None:
    st.subheader("REVENUE-5 Commander / Human Review Only")
    rows = (
        ("Current Revenue Mission", "Complete traceable Owner decisions"),
        ("Highest Priority Owner Decision", "Service to sell first"),
        ("Next Missing Evidence", "Service scope and Owner signature"),
        ("Activation Blocker", "All 10 activation gates incomplete"),
        ("Recommended Human Action", "Review locally; do not contact a customer"),
        ("Production Status", "NO-GO"),
    )
    st.dataframe([{"Field": field, "Value": value} for field, value in rows], hide_index=True, use_container_width=True)


def render_executive() -> None:
    st.subheader("REVENUE-5 Executive / Verified Current Values")
    values = (("Business Decision Readiness", "0%"), ("Offer Readiness", "0%"),
        ("Legal Evidence Readiness", "0%"), ("Activation Readiness", "BLOCKED"),
        ("Real Customers", "0"), ("Verified Revenue", "¥0 ACTUAL"), ("Production Status", "NO-GO"))
    columns = st.columns(4)
    for index, (label, value) in enumerate(values): columns[index % 4].metric(label, value)


def render_review_hub() -> None:
    st.subheader("REVENUE-5 Owner Approval Review Hub")
    sections = ("Pricing Review", "Service Scope Review", "Payment Terms Review",
                "Legal Evidence Review", "Consent Review", "Activation Review")
    st.dataframe([{"Review": item, "Status": "REVIEW REQUIRED", "Action": "DISPLAY ONLY"}
                  for item in sections], hide_index=True, use_container_width=True)
    st.caption("No approval action triggers production behavior")
