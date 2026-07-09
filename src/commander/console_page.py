from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.commander.api import CommanderAPI
from src.commander.production_connection import ENV_KEYS, ProductionConnectionManager
from src.commander.queue import STATUS_LABELS, CommanderQueue
from src.commander.templates import list_templates
from src.commander.worker import CommanderWorker


STATUS_COLORS = {
    "waiting": "#475467",
    "planning": "#7a5af8",
    "retry_queued": "#7a5af8",
    "dry_run_completed": "#0e9384",
    "approved": "#1570ef",
    "execute_ready": "#b54708",
    "running": "#dc6803",
    "completed": "#039855",
    "failed": "#d92d20",
    "deferred": "#667085",
    "rejected": "#d92d20",
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

    st.title("AIOS CEO Dashboard")
    st.caption("Business Commander: note / Threads / 公式サイトをROI順に実行します。")

    queue = CommanderQueue()
    api = CommanderAPI(queue, worker=CommanderWorker(queue))
    summary = queue.summary()
    state = queue.load()
    provider_health = state.get("provider_health", [])

    _render_metrics(summary)
    _render_production_ready()
    _render_company_cards(summary)
    _render_content_cards(summary)
    _render_execution_cards(summary)
    _render_business_dashboard(summary)
    _render_command_center(api, queue)

    current = summary.get("current_job", {})
    st.subheader("現在Job")
    st.json(current) if current else st.info("現在実行中のCommander Jobはありません。")

    tabs = st.tabs(["Production", "Execution", "Content Ops", "Revenue Queue", "Today", "This Week", "変更予定 / Diff", "Completed", "Failed", "履歴", "API"])
    with tabs[0]:
        _render_production_connection_wizard()
    with tabs[1]:
        _render_execution_ops(summary.get("execution", {}), api)
    with tabs[2]:
        _render_content_ops(summary.get("content_operation", {}), api)
    with tabs[3]:
        _render_queue(api.queue_endpoint().get("queue", []), api)
    with tabs[4]:
        _render_business_rows(summary.get("dashboard", {}).get("today", []), api)
    with tabs[5]:
        _render_business_rows(summary.get("dashboard", {}).get("this_week", []), api)
    with tabs[6]:
        _render_change_preview(summary.get("queue", []) + summary.get("history", []))
    with tabs[7]:
        _render_business_rows(summary.get("dashboard", {}).get("completed", []), api)
    with tabs[8]:
        _render_business_rows(summary.get("dashboard", {}).get("failed", []), api)
    with tabs[9]:
        _render_history(api.history_endpoint().get("history", []))
    with tabs[10]:
        st.json(
            {
                "/api/commander/queue": api.queue_endpoint(),
                "/api/commander/history": api.history_endpoint(),
                "/api/commander/approve": {"method": "POST", "body": {"job_id": "cmd-..."}},
                "/api/commander/execute": {"method": "POST", "body": {"job_id": "cmd-..."}},
                "/api/commander/reject": {"method": "POST", "body": {"job_id": "cmd-...", "reason": "..."}},
            }
        )
        st.caption("Provider状態")
        st.json(provider_health)
        st.caption("Self Improvement")
        st.json(summary.get("metrics", [])[:30])
    st.subheader("Executive AI")
    st.success(summary.get("executive", {}).get("message", "今AIOSが最優先でやる仕事: Revenue Queueを作成する"))
    content = summary.get("content_operation", {}).get("today_content_mission")
    if content:
        st.info(f"今日AIOSが最優先で作るコンテンツ: {content.get('title', '')}")


def _render_metrics(summary: dict[str, Any]) -> None:
    history_metrics = summary.get("history_metrics", {})
    revenue_plan = summary.get("revenue_plan", {})
    knowledge_growth = summary.get("knowledge_growth", {})
    system_health = summary.get("system_health", {})
    highest = summary.get("executive", {}).get("top_priority", {}) or {}
    highest_task = highest.get("business_task", {})
    metrics = [
        ("Today's Mission", len(summary.get("dashboard", {}).get("today", []))),
        ("Highest ROI", highest_task.get("roi", 0)),
        ("Pending Review", len(summary.get("dashboard", {}).get("pending_review", []))),
        ("Revenue Forecast", f"{revenue_plan.get('queue_forecast', 0):,}"),
        ("Knowledge Growth", knowledge_growth.get("records", 0)),
        ("System Health", system_health.get("status", "ok")),
        ("Success", f"{int(history_metrics.get('success_rate', 0) * 100)}%"),
    ]
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        col.markdown(f'<div class="cmd-card"><div class="cmd-number">{value}</div><div class="cmd-label">{label}</div></div>', unsafe_allow_html=True)


def _render_production_ready() -> None:
    status = ProductionConnectionManager().current_status()
    ready = status.get("production_ready", False)
    st.metric("Production Ready", "YES" if ready else "NO")


def _render_production_connection_wizard() -> None:
    manager = ProductionConnectionManager()
    status = manager.current_status()
    st.subheader("Production Connection Wizard")
    st.caption("秘密情報は保存後も表示しません。入力欄と保存済み値はマスク表示のみです。")
    cols = st.columns(3)
    for col, channel in zip(cols, ["note", "threads", "website"]):
        connected = status.get("connections", {}).get(channel, {}).get("connected", False)
        col.metric(channel.title(), "Connected" if connected else "Not Connected")
    with st.form("production_connection_form"):
        payload: dict[str, dict[str, str]] = {}
        for channel, keys in ENV_KEYS.items():
            st.markdown(f"**{channel.title()}**")
            payload[channel] = {}
            saved = status.get("connections", {}).get(channel, {}).get("fields", {})
            for key in keys:
                st.caption(f"{key}: {saved.get(key, '') or '(not set)'}")
                payload[channel][key] = st.text_input(key, value="", type="password", key=f"prod_{channel}_{key}")
        submitted = st.form_submit_button("安全保存してHealth Check", type="primary")
        if submitted:
            result = manager.save_connections(payload)
            if result.get("production_ready"):
                st.success("Production Connected")
            else:
                st.warning("Production Not Connected")
            st.json({"production_ready": result.get("production_ready"), "saved_keys": result.get("saved", []), "health": result.get("health", {})})
            st.rerun()


def _render_business_dashboard(summary: dict[str, Any]) -> None:
    next_job = summary.get("executive", {}).get("next_action")
    st.subheader("今やるべき仕事")
    if not next_job:
        st.info("Revenue Queueは空です。自然言語入力からBusiness Planを作成してください。")
        return
    task = next_job.get("business_task", {})
    cols = st.columns([2.4, 1, 1, 1, 1])
    cols[0].markdown(f"**{task.get('title', next_job.get('instruction', ''))}**")
    cols[1].metric("ROI", task.get("roi", 0))
    cols[2].metric("Revenue", f"{task.get('expected_income', 0):,}")
    cols[3].metric("Hours", task.get("expected_time", 0))
    cols[4].metric("Score", task.get("priority_score", 0))
    st.caption("Executive Decision TOP3")
    top3 = []
    for label, jobs in (("今", summary.get("executive", {}).get("top3", [])), ("今週", summary.get("executive", {}).get("this_week", [])), ("今月", summary.get("executive", {}).get("this_month", []))):
        titles = [job.get("business_task", {}).get("title", job.get("instruction", "")) for job in jobs[:3]]
        top3.append({"scope": label, "top3": titles})
    st.json(top3)


def _render_company_cards(summary: dict[str, Any]) -> None:
    company = summary.get("company", {})
    growth = summary.get("growth_engine", {})
    cols = st.columns(6)
    values = [
        ("Cash", company.get("cash", 0)),
        ("Monthly Cost", company.get("monthly_cost", 0)),
        ("Monthly Income", company.get("monthly_income", 0)),
        ("Profit", company.get("profit", 0)),
        ("Runway", company.get("runway", 0)),
        ("Health", company.get("business_health", "building")),
    ]
    for col, (label, value) in zip(cols, values):
        col.metric(label, value)
    st.caption("Growth Engine")
    st.json({key: growth.get(key, 0) for key in ["traffic", "cv", "cvr", "ctr", "followers", "sales", "growth"]})


def _render_content_cards(summary: dict[str, Any]) -> None:
    content = summary.get("content_operation", {})
    cards = [
        ("Today Content Mission", 1 if content.get("today_content_mission") else 0),
        ("note Drafts", content.get("note_drafts", 0)),
        ("Threads Drafts", content.get("threads_drafts", 0)),
        ("LINE Drafts", content.get("line_drafts", 0)),
        ("Pending Review", len(content.get("pending_review", []))),
        ("Approved Queue", len(content.get("approved_queue", []))),
        ("Revenue CTA", len(content.get("revenue_cta", []))),
    ]
    cols = st.columns(len(cards))
    for col, (label, value) in zip(cols, cards):
        col.metric(label, value)


def _render_execution_cards(summary: dict[str, Any]) -> None:
    execution = summary.get("execution", {})
    cards = [
        ("Execution Queue", len(execution.get("execution_queue", []))),
        ("Scheduled", len(execution.get("scheduled", []))),
        ("Publishing", len(execution.get("publishing", []))),
        ("Published", len(execution.get("published", []))),
        ("Failed", len(execution.get("failed", []))),
        ("Retry Queue", len(execution.get("retry_queue", []))),
        ("Next Publish", 1 if execution.get("next_publish") else 0),
    ]
    cols = st.columns(len(cards))
    for col, (label, value) in zip(cols, cards):
        col.metric(label, value)


def _render_execution_ops(execution: dict[str, Any], api: CommanderAPI) -> None:
    st.subheader("Execution Queue")
    rows = execution.get("execution_queue", [])
    if not rows:
        st.info("Execution Queueは空です。")
        return
    for action in rows:
        with st.container(border=True):
            cols = st.columns([1, 1.4, 2.4, 1.2, 1.2, 1.2])
            cols[0].markdown(_status_pill(action.get("status", "")), unsafe_allow_html=True)
            cols[1].caption(action.get("channel", ""))
            cols[2].markdown(f"**{action.get('title', '')}**")
            action_id = action.get("action_id", "")
            if action.get("status") in {"draft", "review"}:
                if cols[3].button("Approve", key=f"exec_approve_{action_id}"):
                    st.json(api.approve_execution(action_id, review_notes="Approved in Commander"))
                    st.rerun()
            if action.get("status") == "approved":
                if cols[4].button("Schedule", key=f"exec_schedule_{action_id}"):
                    st.json(api.schedule_execution(action_id))
                    st.rerun()
                if cols[5].button("Publish(Mock)", key=f"exec_publish_{action_id}"):
                    st.json(api.publish_execution(action_id))
                    st.rerun()
            elif action.get("status") == "failed":
                if cols[4].button("Retry", key=f"exec_retry_{action_id}"):
                    st.json(api.retry_execution(action_id))
                    st.rerun()


def _render_content_ops(content: dict[str, Any], api: CommanderAPI) -> None:
    st.subheader("Content Operation")
    with st.form("content_draft_form"):
        channel = st.selectbox("Channel", ["note", "threads", "official_line", "website"])
        instruction = st.text_area("Content instruction", value="初収益につながるnote導線を作る")
        expected_revenue = st.number_input("Expected revenue", min_value=0, value=0)
        submitted = st.form_submit_button("Draft生成 / Reviewへ", type="primary")
        if submitted:
            st.json(api.create_content_draft(channel, instruction, expected_revenue=int(expected_revenue)))
            st.rerun()
    rows = content.get("queue", [])
    if not rows:
        st.info("Content Queueは空です。")
        return
    table = [
        {
            "content_id": item.get("content_id", ""),
            "status": item.get("status", ""),
            "channel": item.get("channel", ""),
            "title": item.get("title", ""),
            "expected_revenue": item.get("expected_revenue", 0),
            "priority_score": item.get("priority_score", 0),
            "publish_ready": item.get("publish_ready", False),
            "send_ready": item.get("send_ready", False),
        }
        for item in rows
    ]
    st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)


def _render_command_center(api: CommanderAPI, queue: CommanderQueue) -> None:
    st.subheader("Commander Input / Plan")
    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("**自然言語チャット入力**")
        instruction = st.text_area(
            "Commanderへの指示",
            value="Threads投稿案を改善し、noteへの初クリック導線を強める。DryRunで差分確認まで。",
            height=150,
        )
        priority = st.slider("Priority", 0, 100, 90)
        target_files_text = st.text_input("追加対象ファイル（任意・カンマ区切り）", value="")
        if st.button("Plan生成してQueueへ追加", type="primary", use_container_width=True):
            target_files = [item.strip() for item in target_files_text.split(",") if item.strip()]
            result = api.enqueue_instruction(instruction, priority=priority, target_files=target_files, dry_run=True)
            st.session_state["commander_last_plan"] = result.get("plan", {})
            st.success(f"Queued: {result['job']['job_id']}" if result.get("ok") else result.get("error", "Failed"))
            st.rerun()
    with right:
        st.markdown("**実行計画 Plan**")
        plan = st.session_state.get("commander_last_plan")
        if not plan:
            queued = queue.summary().get("queue", [])
            plan = queued[0].get("plan", {}) if queued else {}
        if plan:
            for step in plan.get("steps", []):
                st.write(f"{step.get('index')}. {step.get('title')}")
            task = plan.get("business_task", {})
            st.caption("ROI")
            st.json(
                {
                    "task_type": task.get("task_type"),
                    "expected_income": task.get("expected_income"),
                    "expected_time": task.get("expected_time"),
                    "deadline": task.get("deadline"),
                    "difficulty": task.get("difficulty"),
                    "roi": task.get("roi"),
                    "priority_score": task.get("priority_score"),
                    "risk": plan.get("risk"),
                    "ai_employee": plan.get("ai_employee"),
                }
            )
            st.caption("Automation Planner")
            st.json(plan.get("automation_plan", {}))
            st.caption("Impacted files")
            st.json(plan.get("impacted_files", []))
        else:
            st.info("指示を入力するとPlanを生成します。")

    st.subheader("Quick Templates")
    templates = list_templates()
    template_labels = {template["label"]: template["template_id"] for template in templates}
    with st.form("commander_enqueue"):
        mode = st.radio("Job作成", ["Template", "Manual"], horizontal=True)
        if mode == "Template":
            label = st.selectbox("Template", list(template_labels.keys()))
            dry_run = st.checkbox("DryRun", value=True, disabled=True)
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
            dry_run = st.checkbox("DryRun", value=True, disabled=True)
            submitted = st.form_submit_button("Queueへ追加", type="primary")
            if submitted:
                target_files = [item.strip() for item in target_files_text.split(",") if item.strip()]
                job = queue.enqueue(
                    engine=engine,
                    instruction=instruction,
                    priority=priority,
                    dry_run=True,
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
                cols[4].caption(job_id)
            elif job.get("status") == "dry_run_completed":
                if cols[4].button("Approve", key=f"cmd_approve_{job_id}", use_container_width=True):
                    st.json(api.approve_endpoint(job_id))
                    st.rerun()
            elif job.get("status") == "approved":
                if cols[4].button("Execute", key=f"cmd_execute_{job_id}", use_container_width=True):
                    st.json(api.execute_endpoint(job_id))
                    st.rerun()
            else:
                cols[4].caption(job_id)
            action_cols = st.columns([1, 1, 4])
            if job.get("status") in {"waiting", "retry_queued"}:
                if action_cols[0].button("DryRun", key=f"cmd_dryrun_{job_id}"):
                    st.json(api.worker.process_job(job, dry_run=True))
                    st.rerun()
            if job.get("status") in {"waiting", "dry_run_completed", "approved"}:
                if action_cols[1].button("Reject", key=f"cmd_reject_{job_id}"):
                    st.json(api.reject_endpoint(job_id, reason="Rejected from Commander UI"))
                    st.rerun()
            if job.get("guard", {}).get("findings"):
                st.error(job.get("guard", {}).get("findings"))


def _render_business_rows(rows: list[dict[str, Any]], api: CommanderAPI) -> None:
    if not rows:
        st.info("対象なし")
        return
    table = []
    for job in rows:
        task = job.get("business_task") or job.get("plan", {}).get("business_task", {})
        table.append(
            {
                "job_id": job.get("job_id", ""),
                "status": STATUS_LABELS.get(job.get("status", ""), job.get("status", "")),
                "task": task.get("task_type", ""),
                "title": task.get("title", job.get("instruction", "")),
                "expected_income": task.get("expected_income", 0),
                "expected_time": task.get("expected_time", 0),
                "deadline": task.get("deadline", ""),
                "roi": task.get("roi", 0),
                "difficulty": task.get("difficulty", 0),
                "priority_score": task.get("priority_score", job.get("priority", 0)),
            }
        )
    st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)


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


def _render_change_preview(rows: list[dict[str, Any]]) -> None:
    previews = [job for job in rows if job.get("diff_preview", {}).get("unified_diff") or job.get("dry_run_result") or job.get("plan")]
    if not previews:
        st.info("変更予定ファイル / Diff Previewはまだありません。")
        return
    for job in previews[:20]:
        preview = job.get("diff_preview", {})
        with st.expander(f"{job.get('job_id')} - {STATUS_LABELS.get(job.get('status', ''), job.get('status', ''))}"):
            st.caption(f"Engine: {job.get('engine', '')} | Started: {job.get('started_at', '')} | Finished: {job.get('finished_at', '')}")
            plan = job.get("plan", {})
            files = preview.get("target_files") or plan.get("impacted_files", [])
            st.json({"target_files": files, "status": preview.get("status", ""), "requires_approval": True, "execute_allowed": job.get("execute_allowed", False)})
            if job.get("result", {}).get("guard", {}).get("findings") or job.get("guard", {}).get("findings"):
                st.error(job.get("result", {}).get("guard", {}).get("findings") or job.get("guard", {}).get("findings"))
            diff = preview.get("unified_diff", "")
            st.code(diff or "No unified diff saved.", language="diff")


def _status_pill(status: str) -> str:
    color = STATUS_COLORS.get(status, "#667085")
    label = STATUS_LABELS.get(status, status or "Unknown")
    return f'<span class="cmd-pill" style="background:{color}">{label}</span>'
