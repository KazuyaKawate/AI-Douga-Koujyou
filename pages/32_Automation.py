from __future__ import annotations

from datetime import datetime

import streamlit as st

from src.automation.automation_manager import AUTOMATION_TYPES, SCHEDULE_TYPES, AutomationManager
from src.core.version import get_version_label
from src.creator_factory.factory_manager import CreatorFactoryManager

st.set_page_config(page_title="Automation Engine", page_icon="⏱️", layout="wide")

manager = AutomationManager()
creator = CreatorFactoryManager()
summary = manager.dashboard_summary()

st.title("⏱️ Automation Engine")
st.caption(f"Local-first scheduler for Creator Factory production | {get_version_label()} | External services disabled")
st.info("Local-first mode: automation creates local pipeline jobs only. No cloud AI API, Google Workspace, external publishing, or upload is used.")

m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
m1.metric("Running automations", summary["running_automations"])
m2.metric("Today's runs", summary["today_runs"])
m3.metric("Failures", summary["failures"])
m4.metric("Retries", summary["retries"])
m5.metric("Average runtime", f"{summary['average_runtime']}ms")
m6.metric("Upcoming jobs", summary["upcoming_jobs"])
m7.metric("Disabled jobs", summary["disabled_jobs"])

tabs = st.tabs(["Rules", "Create Rule", "Scheduler", "Execution History", "Execution Log", "Local Safety"])

with tabs[0]:
    st.subheader("Automation Rules")
    rules = manager.list_rules()
    if not rules:
        st.info("No automation rules yet.")
    for rule in rules:
        with st.container(border=True):
            c1, c2, c3, c4, c5, c6 = st.columns([3, 1, 1, 1, 1, 1])
            c1.markdown(f"**{rule.get('name', '')}**  \n`{rule.get('automation_type', '')}`")
            c2.metric("Status", rule.get("status", ""))
            c3.metric("Schedule", rule.get("schedule_type", ""))
            c4.metric("Next Run", rule.get("next_run") or "Manual")
            c5.metric("Last Run", rule.get("last_run") or "None")
            c6.metric("Missed", rule.get("missed_runs", 0))
            b1, b2, b3, b4, b5, b6 = st.columns(6)
            if b1.button("Run Now", key=f"run_{rule['rule_id']}"):
                manager.manual_run(rule["rule_id"])
                st.success("Automation executed locally.")
                st.rerun()
            if b2.button("Enable", key=f"enable_{rule['rule_id']}"):
                manager.enable_rule(rule["rule_id"])
                st.rerun()
            if b3.button("Disable", key=f"disable_{rule['rule_id']}"):
                manager.disable_rule(rule["rule_id"])
                st.rerun()
            if b4.button("Pause", key=f"pause_{rule['rule_id']}"):
                manager.pause_rule(rule["rule_id"])
                st.rerun()
            if b5.button("Resume", key=f"resume_{rule['rule_id']}"):
                manager.resume_rule(rule["rule_id"])
                st.rerun()
            if b6.button("Delete", key=f"delete_{rule['rule_id']}"):
                manager.delete_rule(rule["rule_id"])
                st.rerun()

with tabs[1]:
    st.subheader("Create Automation Rule")
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Rule name", key="auto_rule_name")
        automation_type = st.selectbox("Automation type", AUTOMATION_TYPES, key="auto_rule_type")
        schedule_type = st.selectbox("Schedule", SCHEDULE_TYPES, key="auto_rule_schedule")
        interval_minutes = st.number_input("Custom interval minutes", min_value=1, value=60, step=5, key="auto_rule_interval")
    with c2:
        projects = creator.list_projects()
        project_options = [""] + [project["id"] for project in projects]
        project_id = st.selectbox("Project", project_options, format_func=lambda value: "None" if not value else next((p["title"] for p in projects if p["id"] == value), value), key="auto_rule_project")
        templates = creator.list_templates()
        template_options = [""] + [template["id"] for template in templates]
        template_id = st.selectbox("Template", template_options, format_func=lambda value: "None" if not value else next((t["name"] for t in templates if t["id"] == value), value), key="auto_rule_template")
        priority = st.selectbox("Priority", ["low", "normal", "high"], index=1, key="auto_rule_priority")
    o1, o2, o3, o4 = st.columns(4)
    auto_queue = o1.checkbox("Auto Queue", value=True, key="auto_rule_auto_queue")
    auto_generate = o2.checkbox("Auto Generate", value=True, key="auto_rule_auto_generate")
    auto_approve = o3.checkbox("Auto Approve + Export", value=False, key="auto_rule_auto_approve")
    manual_override = o4.checkbox("Manual Override", value=True, key="auto_rule_manual_override")
    if st.button("Create automation rule", type="primary"):
        if name:
            manager.create_rule(
                name,
                automation_type,
                schedule_type=schedule_type,
                interval_minutes=int(interval_minutes),
                project_id=project_id,
                template_id=template_id,
                priority=priority,
                auto_queue=auto_queue,
                auto_generate=auto_generate,
                auto_approve=auto_approve,
                manual_override=manual_override,
            )
            st.success("Automation rule created locally.")
            st.rerun()
        else:
            st.warning("Rule name is required.")

with tabs[2]:
    st.subheader("Scheduler")
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Automation Queue", summary["automation_queue"])
    s2.metric("Next Scheduled Job", summary["next_scheduled_job"])
    s3.metric("Upcoming Jobs", summary["upcoming_jobs"])
    s4.metric("Disabled Jobs", summary["disabled_jobs"])
    if st.button("Run due automations now", type="primary"):
        results = manager.run_due(datetime.now())
        st.success(f"Executed {len(results)} due automation(s).")
        st.rerun()
    if st.button("Detect missed runs"):
        missed = manager.detect_missed_runs(datetime.now())
        st.info(f"Missed runs detected: {missed}")
        st.rerun()

with tabs[3]:
    st.subheader("Execution History")
    history = manager.history()
    if not history:
        st.info("No automation executions yet.")
    for execution in history:
        with st.container(border=True):
            h1, h2, h3, h4, h5, h6 = st.columns([2, 1, 1, 1, 1, 1])
            h1.markdown(f"**{execution.get('execution_id', '')}**  \nRule: `{execution.get('rule_id', '')}`")
            h2.metric("Status", execution.get("status", ""))
            h3.metric("Pipeline", execution.get("pipeline_id") or "None")
            h4.metric("Approval", execution.get("approval_id") or "None")
            h5.metric("Export", execution.get("export_id") or "None")
            h6.metric("Checksum", "yes" if execution.get("checksum") else "no")
            if execution.get("status") == "failed" and st.button("Retry", key=f"retry_{execution['execution_id']}"):
                manager.retry_execution(execution["execution_id"])
                st.success("Retry queued and executed locally.")
                st.rerun()

with tabs[4]:
    st.subheader("Execution Log")
    logs = manager.execution_log()
    if not logs:
        st.info("No execution logs yet.")
    for row in logs:
        st.write(f"{row.get('created_at')} — `{row.get('status')}` — {row.get('message')}")

with tabs[5]:
    st.subheader("Local Safety")
    st.json({
        "local_first": summary["local_first"],
        "external_apis_enabled": summary["external_apis_enabled"],
        "openai_api": False,
        "anthropic_api": False,
        "gemini_cloud_api": False,
        "google_workspace": False,
        "external_publishing": False,
    })
