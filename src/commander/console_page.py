from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.commander.api import CommanderAPI
from src.commander.queue import STATUS_LABELS, CommanderQueue
from src.commander.templates import list_templates
from src.commander.worker import CommanderWorker


STATUS_COLORS = {
    "pending": "#475467",
    "queued": "#475467",
    "retry_queued": "#7a5af8",
    "dry_run_complete": "#0e9384",
    "approved": "#1570ef",
    "execute_ready": "#b54708",
    "running": "#dc6803",
    "completed": "#039855",
    "failed": "#d92d20",
    "deferred": "#667085",
}


def render_console() -> None:
    st.markdown(
        """
        <style>
        .cmd-card{background:#fff;border:1px solid #e6e9ef;border-radius:8px;padding:16px;min-height:110px;}
        .cmd-number{font-size:28px;font-weight:760;color:#155e75;line-height:1.1;}
        .cmd-label{color:#667085;font-size:13px;}
        .cmd-pill{display:inline-block;border-radius:999px;padding:3px 9px;color:#fff;font-size:12px;font-weight:700;}
        div.stButton > button{min-height:44px;font-weight:700;border-radius:8px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("AIOS Commander Console")
    st.caption("Local First / DryRun / Approve / Execute を分離して、初収益に近い改善だけを処理します。")

    queue = CommanderQueue()
    api = CommanderAPI(queue, worker=CommanderWorker(queue))
    summary = queue.summary()
    state = queue.load()
    provider_health = state.get("provider_health", [])

    _render_metrics(summary)
    _render_enqueue(api, queue)

    current = summary.get("current_job", {})
    st.subheader("現在Job")
    st.json(current) if current else st.info("現在実行中のCommander Jobはありません。")

    tabs = st.tabs(["Queue", "履歴", "Diff Preview", "API", "Provider状態", "Self Improvement"])
    with tabs[0]:
        _render_queue(api.queue_endpoint().get("queue", []), api)
    with tabs[1]:
        _render_history(api.history_endpoint().get("history", []))
    with tabs[2]:
        _render_diff_preview(summary.get("history", []))
    with tabs[3]:
        st.json(
            {
                "/api/commander/queue": api.queue_endpoint(),
                "/api/commander/history": api.history_endpoint(),
                "/api/commander/approve": {"method": "POST", "body": {"job_id": "cmd-..."}},
                "/api/commander/execute": {"method": "POST", "body": {"job_id": "cmd-..."}},
            }
        )
    with tabs[4]:
        st.json(provider_health)
    with tabs[5]:
        st.json(summary.get("metrics", [])[:30])


def _render_metrics(summary: dict[str, Any]) -> None:
    metrics = [
        ("Pending", summary.get("queued", 0)),
        ("DryRun Complete", summary.get("dry_run_complete", 0)),
        ("Approved", summary.get("approved", 0)),
        ("Execute Ready", summary.get("execute_ready", 0)),
        ("Running", summary.get("running", 0)),
        ("Completed", summary.get("completed", 0)),
        ("Failed", summary.get("failed", 0)),
    ]
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        col.markdown(f'<div class="cmd-card"><div class="cmd-number">{value}</div><div class="cmd-label">{label}</div></div>', unsafe_allow_html=True)


def _render_enqueue(api: CommanderAPI, queue: CommanderQueue) -> None:
    st.subheader("Commander Queue")
    templates = list_templates()
    template_labels = {template["label"]: template["template_id"] for template in templates}
    with st.form("commander_enqueue"):
        mode = st.radio("Job作成", ["Template", "Manual"], horizontal=True)
        if mode == "Template":
            label = st.selectbox("Template", list(template_labels.keys()))
            dry_run = st.checkbox("DryRun", value=True)
            submitted = st.form_submit_button("TemplateをQueueへ追加", type="primary")
            if submitted:
                result = api.enqueue_template(template_labels[label], dry_run=dry_run)
                st.success(f"Queued: {result['job']['job_id']}" if result.get("ok") else result.get("error", "Failed"))
                st.rerun()
        else:
            engine = st.selectbox("依頼元Engine", ["business", "revenue", "growth", "content_factory"])
            instruction = st.text_area("収益改善Instruction", value="Threads実投稿からPV取得と初クリックを改善する")
            priority = st.slider("Priority", 0, 100, 80)
            target_files_text = st.text_input("対象ファイル", value="src/business_engine/threads_automation.py")
            dry_run = st.checkbox("DryRun", value=True)
            submitted = st.form_submit_button("Queueへ追加", type="primary")
            if submitted:
                target_files = [item.strip() for item in target_files_text.split(",") if item.strip()]
                job = queue.enqueue(
                    engine=engine,
                    instruction=instruction,
                    priority=priority,
                    dry_run=dry_run,
                    metadata={"target_files": target_files, "pytest_args": ["-q"]},
                    callback={"targets": ["business", "revenue", "growth", "mission_planner", "knowledge", "coding_engine"]},
                )
                st.success(f"Queued: {job['job_id']}")
                st.rerun()

    action_cols = st.columns([1, 1, 2])
    if action_cols[0].button("Worker DryRun 1件実行", type="primary", use_container_width=True):
        with st.spinner("Commander processing one revenue job..."):
            result = CommanderWorker(queue).process_next(dry_run=True)
        st.json(result)
        st.rerun()
    if action_cols[1].button("更新", use_container_width=True):
        st.rerun()


def _render_queue(rows: list[dict[str, Any]], api: CommanderAPI) -> None:
    if not rows:
        st.info("待機Jobなし")
        return
    for job in rows:
        with st.container(border=True):
            cols = st.columns([1.2, 2.2, 1.2, 1.2, 1.4])
            cols[0].markdown(_status_pill(job.get("status", "")), unsafe_allow_html=True)
            cols[1].markdown(f"**{job.get('instruction', '')}**")
            cols[2].caption(f"Engine: {job.get('engine', '')}")
            cols[3].caption(f"Priority: {job.get('priority', 0)}")
            job_id = job.get("job_id", "")
            if job.get("status") == "dry_run_complete":
                if cols[4].button("Approve", key=f"cmd_approve_{job_id}", use_container_width=True):
                    st.json(api.approve_endpoint(job_id))
                    st.rerun()
            elif job.get("status") == "approved":
                if cols[4].button("Execute", key=f"cmd_execute_{job_id}", use_container_width=True):
                    st.json(api.execute_endpoint(job_id))
                    st.rerun()
            else:
                cols[4].caption(job_id)


def _render_history(rows: list[dict[str, Any]]) -> None:
    if not rows:
        st.info("履歴なし")
        return
    table = []
    for job in rows:
        result = job.get("result", {})
        table.append(
            {
                "job_id": job.get("job_id", ""),
                "status": STATUS_LABELS.get(job.get("status", ""), job.get("status", "")),
                "engine": job.get("engine", ""),
                "started_at": job.get("started_at", ""),
                "finished_at": job.get("finished_at", ""),
                "dry_run_saved": bool(job.get("dry_run_result")),
                "diff_preview": bool(job.get("diff_preview", {}).get("unified_diff")),
                "run_status": result.get("coding_run", {}).get("status", ""),
            }
        )
    st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)


def _render_diff_preview(rows: list[dict[str, Any]]) -> None:
    previews = [job for job in rows if job.get("diff_preview", {}).get("unified_diff") or job.get("dry_run_result")]
    if not previews:
        st.info("Diff Previewはまだありません。")
        return
    for job in previews[:20]:
        preview = job.get("diff_preview", {})
        with st.expander(f"{job.get('job_id')} - {STATUS_LABELS.get(job.get('status', ''), job.get('status', ''))}"):
            st.caption(f"Engine: {job.get('engine', '')} | Started: {job.get('started_at', '')} | Finished: {job.get('finished_at', '')}")
            st.json({"target_files": preview.get("target_files", []), "status": preview.get("status", ""), "requires_approval": preview.get("requires_approval", False)})
            diff = preview.get("unified_diff", "")
            st.code(diff or "No unified diff saved.", language="diff")


def _status_pill(status: str) -> str:
    color = STATUS_COLORS.get(status, "#667085")
    label = STATUS_LABELS.get(status, status or "Unknown")
    return f'<span class="cmd-pill" style="background:{color}">{label}</span>'
