from __future__ import annotations

from datetime import date

import streamlit as st

from src.core.version import get_version_label
from src.creator_factory.factory_manager import (
    KNOWLEDGE_TYPES,
    PIPELINES,
    PROJECT_STATUSES,
    TEMPLATE_TYPES,
    CreatorFactoryManager,
)
from src.pipeline.pipeline_manager import PipelineManager
from src.automation.automation_manager import AutomationManager

st.set_page_config(page_title="Creator Factory", page_icon="🏭", layout="wide")

manager = CreatorFactoryManager()
pipeline_manager = PipelineManager(creator=manager)
automation_manager = AutomationManager(creator=manager, pipeline=pipeline_manager)
metrics = manager.dashboard_metrics()
pipelines = manager.pipeline_summary()
estimator = manager.revenue_estimator()

st.title("🏭 Creator Factory")
st.caption(f"Local-first content production and revenue operations | {get_version_label()} | External publishing disabled")
st.info("Local-first mode: projects, templates, knowledge, and production state are stored only under data/. No cloud API or external publishing is called.")

top = st.columns(8)
top[0].metric("Active Projects", metrics["active_projects"])
top[1].metric("Production Queue", metrics["production_queue"])
top[2].metric("Review Queue", metrics["review_queue"])
top[3].metric("Export Queue", metrics["export_queue"])
top[4].metric("Today's Output", metrics["today_output"])
top[5].metric("Weekly Output", metrics["weekly_output"])
top[6].metric("Monthly Output", metrics["monthly_output"])
top[7].metric("Avg Runtime", f"{metrics['average_runtime']}m")

tabs = st.tabs([
    "📊 Production Dashboard",
    "🧾 Production Queue",
    "🕓 Production History",
    "📅 Content Calendar",
    "📁 Projects",
    "🧩 Templates",
    "🧠 Knowledge Base",
    "💹 Revenue Dashboard",
])

with tabs[0]:
    st.subheader("Production Pipelines")
    for key, row in pipelines.items():
        with st.container(border=True):
            c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 1, 1, 1, 1, 1, 1])
            c1.markdown(f"**{row['label']}**  \n`{key}`")
            c2.metric("Queue", row["queue"])
            c3.metric("Status", row["status"])
            c4.metric("Output Count", row["output_count"])
            c5.metric("Runtime", f"{row['estimated_runtime']}m")
            c6.metric("Tokens", row["estimated_token_usage"])
            c7.metric("Export", row["export_status"])

with tabs[1]:
    st.subheader("Production Queue")
    with st.expander("Add production item", expanded=False):
        q1, q2 = st.columns(2)
        with q1:
            pipeline = st.selectbox("Pipeline", list(PIPELINES.keys()), format_func=lambda value: PIPELINES[value]["label"], key="cf_queue_pipeline")
            title = st.text_input("Title", key="cf_queue_title")
            priority = st.selectbox("Priority", ["low", "normal", "high"], index=1, key="cf_queue_priority")
        with q2:
            projects = manager.list_projects()
            project_options = [""] + [project["id"] for project in projects]
            project_id = st.selectbox("Project", project_options, format_func=lambda value: "None" if not value else next((p["title"] for p in projects if p["id"] == value), value), key="cf_queue_project")
            templates = manager.list_templates()
            template_options = [""] + [template["id"] for template in templates]
            template_id = st.selectbox("Template", template_options, format_func=lambda value: "None" if not value else next((t["name"] for t in templates if t["id"] == value), value), key="cf_queue_template")
            due_date = st.date_input("Due date", value=date.today(), key="cf_queue_due")
        if st.button("Queue production", type="primary"):
            if title:
                manager.enqueue_production(pipeline, title, project_id=project_id, template_id=template_id, priority=priority, due_date=due_date.isoformat())
                st.success("Production item queued locally.")
                st.rerun()
            else:
                st.warning("Title is required.")

    with st.expander("Automation shortcut", expanded=False):
        st.caption("Create a local automation rule for Creator Factory production. External services stay disabled.")
        a1, a2, a3 = st.columns(3)
        auto_name = a1.text_input("Automation name", key="cf_auto_name")
        auto_pipeline = a2.selectbox("Automation pipeline", list(PIPELINES.keys()), format_func=lambda value: PIPELINES[value]["label"], key="cf_auto_pipeline")
        auto_schedule = a3.selectbox("Schedule", ["manual", "hourly", "daily", "weekly", "monthly", "custom_interval"], key="cf_auto_schedule")
        auto_generate = st.checkbox("Auto Generate", value=True, key="cf_auto_generate")
        auto_queue = st.checkbox("Auto Queue", value=True, key="cf_auto_queue")
        manual_override = st.checkbox("Manual Override", value=True, key="cf_auto_manual_override")
        if st.button("Create Creator Factory automation", key="cf_create_auto"):
            if auto_name:
                automation_manager.create_rule(
                    auto_name,
                    "creator_factory" if auto_pipeline == "note" else auto_pipeline,
                    schedule_type=auto_schedule,
                    auto_generate=auto_generate,
                    auto_queue=auto_queue,
                    manual_override=manual_override,
                )
                st.success("Automation rule created locally.")
                st.rerun()
            else:
                st.warning("Automation name is required.")

    queued = manager.list_production("queued")
    if not queued:
        st.info("Production queue is empty.")
    for item in queued:
        with st.container(border=True):
            c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
            c1.markdown(f"**{item.get('title', '')}**  \n{item.get('pipeline_label', '')}")
            c2.metric("Priority", item.get("priority", "normal"))
            c3.metric("Runtime", f"{item.get('estimated_runtime_minutes', 0)}m")
            c4.metric("Tokens", item.get("estimated_token_usage", 0))
            c5.metric("Approval", item.get("approval_status", ""))
            if st.button("Generate", key=f"cf_generate_{item['id']}"):
                job = pipeline_manager.create_from_production(item["id"])
                pipeline_manager.run_until_review(job["job_id"])
                st.success(f"Generated locally and sent to Approval Center: {job['job_id']}")
                st.rerun()

with tabs[2]:
    st.subheader("Production History")
    history = [item for item in manager.list_production() if item.get("status") in ("completed", "failed", "exported")]
    if not history:
        st.info("No production history yet.")
    for item in history:
        with st.container(border=True):
            h1, h2, h3, h4 = st.columns([3, 1, 1, 1])
            h1.markdown(f"**{item.get('title', '')}**  \n{item.get('pipeline_label', '')}")
            h2.metric("Status", item.get("status", ""))
            h3.metric("Approval", item.get("approval_status", ""))
            h4.metric("Export", item.get("export_status", ""))

with tabs[3]:
    st.subheader("Content Calendar")
    calendar = manager.content_calendar()
    if not calendar:
        st.info("No scheduled production items in the next 30 days.")
    for item in calendar:
        st.write(f"{item['date']} — **{item['title']}** / {item['pipeline']} / {item['status']}")

with tabs[4]:
    st.subheader("Project Management")
    with st.expander("Create project", expanded=False):
        p1, p2 = st.columns(2)
        with p1:
            title = st.text_input("Project title", key="cf_project_title")
            category = st.text_input("Category", value="creator", key="cf_project_category")
            platform = st.text_input("Target platform", value="note", key="cf_project_platform")
        with p2:
            priority = st.selectbox("Priority", ["low", "normal", "high"], index=1, key="cf_project_priority")
            status = st.selectbox("Status", PROJECT_STATUSES, key="cf_project_status")
            description = st.text_area("Description", height=90, key="cf_project_description")
        if st.button("Create project", type="primary"):
            if title:
                manager.create_project(title, description=description, category=category, target_platform=platform, priority=priority, status=status)
                st.success("Project created locally.")
                st.rerun()
            else:
                st.warning("Project title is required.")

    for project in manager.list_projects():
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.markdown(f"**{project.get('title', '')}**  \n{project.get('description', '')}")
            c2.metric("Status", project.get("status", ""))
            c3.metric("Platform", project.get("target_platform", ""))
            c4.metric("Priority", project.get("priority", ""))

with tabs[5]:
    st.subheader("Content Templates")
    with st.expander("Create template", expanded=False):
        t1, t2 = st.columns(2)
        with t1:
            name = st.text_input("Template name", key="cf_template_name")
            template_type = st.selectbox("Template type", list(TEMPLATE_TYPES.keys()), key="cf_template_type")
            description = st.text_input("Description", key="cf_template_description")
        with t2:
            body = st.text_area("Template body", value=TEMPLATE_TYPES["note_article"], height=180, key="cf_template_body")
        if st.button("Save template", type="primary"):
            if name:
                manager.create_template(name, template_type, body, description=description)
                st.success("Template saved locally.")
                st.rerun()
            else:
                st.warning("Template name is required.")

    for template in manager.list_templates():
        with st.container(border=True):
            st.markdown(f"**{template.get('name', '')}** / `{template.get('template_type', '')}` / v{template.get('version', 1)}")
            st.code(template.get("body", ""), language="markdown")
            if st.button("Duplicate template", key=f"dup_{template['id']}"):
                manager.duplicate_template(template["id"])
                st.success("Template duplicated.")
                st.rerun()

with tabs[6]:
    st.subheader("Local Knowledge Base")
    with st.expander("Add knowledge item", expanded=False):
        k1, k2 = st.columns(2)
        with k1:
            title = st.text_input("Knowledge title", key="cf_kb_title")
            knowledge_type = st.selectbox("Knowledge type", KNOWLEDGE_TYPES, key="cf_kb_type")
            tags = st.text_input("Tags comma separated", key="cf_kb_tags")
        with k2:
            content = st.text_area("Content", height=160, key="cf_kb_content")
        if st.button("Save knowledge", type="primary"):
            if title and content:
                manager.add_knowledge_item(title, knowledge_type, content, tags=[tag.strip() for tag in tags.split(",") if tag.strip()])
                st.success("Knowledge item saved locally.")
                st.rerun()
            else:
                st.warning("Title and content are required.")

    for item in manager.list_knowledge():
        with st.container(border=True):
            st.markdown(f"**{item.get('title', '')}** / `{item.get('knowledge_type', '')}`")
            st.write(", ".join(item.get("tags", [])) or "No tags")
            st.code(item.get("content", ""), language="markdown")

with tabs[7]:
    st.subheader("Revenue Dashboard")
    st.warning("Estimates are production metrics only. AIOS does not predict or claim actual income.")
    r1, r2, r3, r4, r5, r6 = st.columns(6)
    r1.metric("Articles Produced", estimator["articles_produced"])
    r2.metric("Exports Completed", estimator["exports_completed"])
    r3.metric("Approval Rate", f"{estimator['approval_rate']}%")
    r4.metric("Rejection Rate", f"{estimator['rejection_rate']}%")
    r5.metric("Avg Production Time", f"{estimator['average_production_time']}m")
    r6.metric("Monthly Volume", estimator["estimated_monthly_production_volume"])

    st.json({
        "local_first": metrics["local_first"],
        "external_apis_enabled": metrics["external_apis_enabled"],
        "income_prediction_enabled": estimator["income_prediction_enabled"],
    })
