from __future__ import annotations

import streamlit as st

from src.core.version import get_version_label
from src.creator_factory.factory_manager import PIPELINES, CreatorFactoryManager
from src.pipeline.pipeline_manager import PipelineManager

st.set_page_config(page_title="Production Pipeline", page_icon="🔁", layout="wide")

creator = CreatorFactoryManager()
pipeline = PipelineManager(creator=creator)
summary = pipeline.dashboard_summary()

st.title("🔁 Production Pipeline")
st.caption(f"Creator Factory → Business Engine → Approval Center → Export Manager → Local Output | {get_version_label()}")
st.info("Local-first mode: this pipeline writes local files only. External publishing, Google Workspace, and cloud AI APIs are disabled.")

c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
c1.metric("Current Jobs", summary["current_jobs"])
c2.metric("Running Jobs", summary["running_jobs"])
c3.metric("Completed Jobs", summary["completed_jobs"])
c4.metric("Approval Waiting", summary["approval_waiting"])
c5.metric("Export Waiting", summary["export_waiting"])
c6.metric("Average Runtime", f"{summary['average_runtime']}s")
c7.metric("Failures", summary["failure_count"])
c8.metric("Success Rate", f"{summary['success_rate']}%")

q1, q2, q3 = st.columns([1, 1, 6])
with q1:
    if st.button("Pause queue", use_container_width=True):
        pipeline.pause()
        st.success("Pipeline queue paused.")
        st.rerun()
with q2:
    if st.button("Resume queue", use_container_width=True):
        pipeline.resume()
        st.success("Pipeline queue resumed.")
        st.rerun()
with q3:
    estimate = pipeline.estimated_completion()
    st.caption(f"Queue length: {estimate['queue_length']} / Estimated completion: {estimate['estimated_minutes']} minutes / Paused: {summary['paused']}")

tabs = st.tabs(["Current Jobs", "Create Job", "Approval Waiting", "Export Waiting", "History", "Local Safety"])

with tabs[0]:
    jobs = [job for job in pipeline.list_jobs() if job.get("status") not in ("completed", "failed", "cancelled")]
    if not jobs:
        st.info("No active pipeline jobs.")
    for job in jobs:
        with st.container(border=True):
            a, b, c, d, e, f = st.columns([3, 1, 1, 1, 1, 1])
            a.markdown(f"**{job.get('title', '')}**  \n`{job.get('job_id', '')}`")
            b.metric("Status", job.get("status", ""))
            c.metric("Pipeline", job.get("pipeline", ""))
            d.metric("Priority", job.get("priority", ""))
            e.metric("Runtime", f"{job.get('estimated_runtime_minutes', 0)}m")
            f.metric("Files", len(job.get("generated_files", [])))
            x1, x2, x3, x4 = st.columns(4)
            if x1.button("Run to review", key=f"run_{job['job_id']}"):
                pipeline.run_until_review(job["job_id"])
                st.success("Generated locally and sent to Approval Center.")
                st.rerun()
            if x2.button("Approve local", key=f"approve_{job['job_id']}"):
                pipeline.approve_pipeline_job(job["job_id"])
                st.success("Marked publish-ready locally.")
                st.rerun()
            if x3.button("Export local", key=f"export_{job['job_id']}"):
                pipeline.export_pipeline_job(job["job_id"])
                st.success("Exported locally.")
                st.rerun()
            if x4.button("Cancel", key=f"cancel_{job['job_id']}"):
                pipeline.cancel(job["job_id"])
                st.warning("Pipeline job cancelled.")
                st.rerun()

with tabs[1]:
    st.subheader("Create Production Job")
    p1, p2 = st.columns(2)
    with p1:
        selected_pipeline = st.selectbox("Pipeline", list(PIPELINES.keys()), format_func=lambda value: PIPELINES[value]["label"], key="pp_pipeline")
        title = st.text_input("Title", key="pp_title")
        priority = st.selectbox("Priority", ["low", "normal", "high"], index=1, key="pp_priority")
    with p2:
        projects = creator.list_projects()
        project_options = [""] + [project["id"] for project in projects]
        project_id = st.selectbox("Project", project_options, format_func=lambda value: "None" if not value else next((p["title"] for p in projects if p["id"] == value), value), key="pp_project")
        templates = creator.list_templates()
        template_options = [""] + [template["id"] for template in templates]
        template_id = st.selectbox("Template", template_options, format_func=lambda value: "None" if not value else next((t["name"] for t in templates if t["id"] == value), value), key="pp_template")
    if st.button("Create pipeline job", type="primary"):
        if title:
            job = pipeline.create_production_job(selected_pipeline, title, project_id=project_id, template_id=template_id, priority=priority)
            st.success(f"Pipeline job created: {job['job_id']}")
            st.rerun()
        else:
            st.warning("Title is required.")

with tabs[2]:
    waiting = pipeline.list_jobs("pending_review")
    if not waiting:
        st.info("No jobs waiting for approval.")
    for job in waiting:
        with st.container(border=True):
            st.markdown(f"**{job.get('title', '')}** / `{job.get('approval_result', {}).get('review_id', '')}`")
            st.write("Review this item in Approval Center, or use local approval for verification.")
            if st.button("Approve and mark publish-ready", key=f"wait_approve_{job['job_id']}"):
                pipeline.approve_pipeline_job(job["job_id"])
                st.success("Approved and marked publish-ready.")
                st.rerun()

with tabs[3]:
    export_waiting = pipeline.list_jobs("publish_ready")
    if not export_waiting:
        st.info("No jobs waiting for export.")
    for job in export_waiting:
        with st.container(border=True):
            st.markdown(f"**{job.get('title', '')}**")
            if st.button("Export locally", key=f"wait_export_{job['job_id']}"):
                pipeline.export_pipeline_job(job["job_id"])
                st.success("Exported locally.")
                st.rerun()

with tabs[4]:
    history = [job for job in pipeline.list_jobs() if job.get("status") in ("completed", "failed", "cancelled")]
    if not history:
        st.info("No pipeline history yet.")
    for job in history:
        with st.container(border=True):
            h1, h2, h3, h4, h5 = st.columns([3, 1, 1, 1, 1])
            h1.markdown(f"**{job.get('title', '')}**  \n`{job.get('job_id', '')}`")
            h2.metric("Status", job.get("status", ""))
            h3.metric("Approval", job.get("approval_result", {}).get("status", ""))
            h4.metric("Export", job.get("export_result", {}).get("export_status", ""))
            h5.metric("Checksum", "yes" if job.get("checksum") else "no")
            if job.get("status") in ("failed", "cancelled") and st.button("Retry", key=f"retry_{job['job_id']}"):
                pipeline.retry(job["job_id"])
                st.success("Queued for retry.")
                st.rerun()

with tabs[5]:
    st.subheader("Local Safety")
    st.json({
        "local_first": summary["local_first"],
        "external_apis_enabled": summary["external_apis_enabled"],
        "external_publishing": False,
        "google_workspace": False,
        "cloud_ai_api": False,
    })
