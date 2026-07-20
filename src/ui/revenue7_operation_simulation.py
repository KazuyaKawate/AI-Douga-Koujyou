"""REVENUE-7 first-revenue operation simulation; presentation-only DryRun."""

from __future__ import annotations

import streamlit as st

SAFETY = {"local_first": True, "dry_run": True, "approval_required": True,
          "execute_allowed": False, "production_actions_enabled": False,
          "review_required": True, "projection_only": True, "production_allowed": False}
MISSION_STEPS = ("Inquiry", "Qualification", "Estimate Review", "Owner Review",
                 "Contract Review", "Production Review", "Delivery Review", "Completion Review")
REVIEW_CHECKPOINTS = ("Estimate", "Contract", "Production", "Delivery", "Completion")
EVIDENCE_SUMMARY = (("Completed Reviews", "0"), ("Missing Reviews", "5"),
    ("Owner Decisions", "0 approved / evidence NOT PROVIDED"),
    ("Legal Evidence", "NOT PROVIDED / NOT VERIFIED"), ("Activation Status", "BLOCKED"))


def render_timeline() -> None:
    st.subheader("REVENUE-7 DryRun Mission Timeline")
    st.dataframe([{"Step": i, "Mission Stage": stage, "Status": "NOT STARTED",
                   "Evidence": "NOT PROVIDED"} for i, stage in enumerate(MISSION_STEPS, 1)],
                 hide_index=True, use_container_width=True)
    st.caption("Presentation only / no persistent mission state")


def render_business_home() -> None:
    st.subheader("REVENUE-7 First Revenue Operation Simulation")
    columns = st.columns(4)
    for column, (label, value) in zip(columns, (("DryRun Revenue Mission", "REVIEW READY"),
        ("Current Mission Stage", "Inquiry / NOT STARTED"), ("Remaining Steps", "8"),
        ("Blocking Items", "Owner + Legal + Activation"))): column.metric(label, value)
    render_timeline()


def render_commander() -> None:
    st.subheader("REVENUE-7 Commander / DryRun Mission")
    rows = (("Current Mission", "First customer workflow simulation"),
            ("Next Step", "Review Inquiry requirements locally"),
            ("Missing Evidence", "Owner decisions and legal evidence NOT PROVIDED"),
            ("Recommended Human Action", "Review the timeline; do not contact a customer"))
    st.dataframe([{"Field": field, "Value": value} for field, value in rows], hide_index=True, use_container_width=True)


def render_executive() -> None:
    st.subheader("REVENUE-7 Executive / Simulation Projection")
    columns = st.columns(4)
    for column, (label, value) in zip(columns, (("Workflow Completion", "0/8 = 0%"),
        ("DryRun Completion", "0%"), ("Estimated Revenue", "¥0 PROJECTION"),
        ("Verified Revenue", "¥0 ACTUAL"))): column.metric(label, value)
    st.caption("No revenue generated / Production NO-GO")


def render_review_hub() -> None:
    st.subheader("REVENUE-7 Simulation Review Checkpoints")
    st.dataframe([{"Checkpoint": item, "Status": "MISSING REVIEW", "Evidence": "NOT PROVIDED"}
                  for item in REVIEW_CHECKPOINTS], hide_index=True, use_container_width=True)


def render_evidence_summary() -> None:
    st.subheader("REVENUE-7 Evidence Summary")
    st.dataframe([{"Evidence Type": item, "Verified Value": value} for item, value in EVIDENCE_SUMMARY],
                 hide_index=True, use_container_width=True)
    st.error("FIRST CUSTOMER ACTIVATION BLOCKED / VERIFIED REVENUE NOT GENERATED / PRODUCTION NO-GO")
