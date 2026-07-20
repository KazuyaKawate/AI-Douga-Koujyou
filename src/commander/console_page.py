from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from src.commander.api import CommanderAPI
from src.commander.chat_ui import render_chat_ui
from src.commander.production_connection import ENV_KEYS, ProductionConnectionManager
from src.commander.queue import STATUS_LABELS, CommanderQueue
from src.commander.templates import list_templates
from src.commander.worker import CommanderWorker
from src.hq.task_manager import STATUS_LABEL, load_tasks, update_task_status
from src.operations.phase9_revenue import Phase9RevenueManager
from src.ui import apply_design_system, page_header, safety_status_strip


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
    apply_design_system()
    # Keep the native heading for accessibility and Streamlit/AppTest compatibility.
    st.markdown('<p class="aios-eyebrow">AIOS / CHAT COMMAND</p>', unsafe_allow_html=True)
    st.title("AIOS Commander")
    st.caption("AIOSの正式な操作入口。自然文からWorkflow Preview、Engine Routing、DryRun、承認、結果まで追跡します。")
    safety_status_strip()

    queue = CommanderQueue()
    api = CommanderAPI(queue, worker=CommanderWorker(queue))
    summary = queue.summary()
    state = queue.load()
    provider_health = state.get("provider_health", [])

    render_chat_ui(api, queue, summary)
    _render_metrics(summary)
    _render_google_workspace(api)
    _render_monetization_flow(api)
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
                "/api/commander/google-workspace/check": {"method": "POST", "body": {"dry_run": True}},
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


def _render_google_workspace(api: CommanderAPI) -> None:
    status = api.queue_endpoint().get("google_workspace", {})
    st.subheader("Google Workspace")
    cols = st.columns([1, 1, 1, 2])
    for col, service in zip(cols[:3], ("sheets", "drive", "gmail")):
        col.metric(service.title(), "Enabled" if status.get("services", {}).get(service) else "Disabled")
    cols[3].metric("Connection", status.get("label", "認証情報が必要です"))
    st.caption("Local First / DryRun必須 / Review Required / Production操作禁止")
    if st.button("Google Workspace接続確認（DryRun）", key="commander_google_workspace_check"):
        result = api.google_workspace_connection_endpoint(dry_run=True)
        st.session_state["google_workspace_check"] = result
    result = st.session_state.get("google_workspace_check")
    if result:
        if result.get("ok"):
            st.success(result.get("label", "接続確認済み"))
        else:
            st.warning(result.get("label", "認証情報が必要です"))
        st.json(result)


def _render_monetization_flow(api: CommanderAPI) -> None:
    st.subheader("Phase 9 初収益フロー: 記事作成 → レビュー → 承認 → 投稿確認")
    st.caption("Local First / Dry Run固定 / Review Required / Production OFF / 外部公開禁止")
    
    phase9 = Phase9RevenueManager()
    phase9_summary = phase9.revenue_summary()
    steps = st.columns(4)
    steps[0].metric("1. 記事作成", "READY")
    steps[1].metric("2. レビュー", phase9_summary["review_waiting"])
    steps[2].metric("3. 承認", phase9_summary["approved"])
    steps[3].metric("4. 投稿確認", phase9_summary["publish_waiting"])
    
    instruction = st.text_area(
        "記事テーマ・読者の課題",
        value="AIOSで初収益につなげるため、noteとThreadsの導線を小さく検証する",
        key="monetization_instruction",
    )
    cta_url = st.text_input("CTAリンク（任意・HTTPS）", key="monetization_cta_url")
    if st.button("1. 記事作成 → 自動レビュー → 承認待ち", type="primary", key="monetization_create_review"):
        workflow = api.create_monetization_package_endpoint(instruction=instruction, cta_url=cta_url)
        st.session_state["monetization_workflow_id"] = workflow.get("workflow_id", "")
        st.success("記事とThreads案を作成し、人間承認待ちで停止しました。")
        st.rerun()

    summary = api.monetization.summary()
    workflows = summary.get("workflows", [])
    
    if not workflows:
        st.info("収益化ワークフローはまだありません。")
        return
        
    st.markdown("---")
    st.markdown("### 収益化ワークフロー詳細編集・承認・投稿 (1画面完結)")
    
    wf_options = {f"{wf['workflow_id']} | {wf['note']['title'][:30]} | {wf['stage']}": wf['workflow_id'] for wf in workflows}
    selected_id = st.session_state.get("monetization_workflow_id", "")
    default_index = 0
    if selected_id:
        for idx, key in enumerate(wf_options.keys()):
            if wf_options[key] == selected_id:
                default_index = idx
                break
                
    selected_label = st.selectbox("編集・承認・投稿対象のワークフロー", list(wf_options.keys()), index=default_index)
    selected_wf_id = wf_options[selected_label]
    st.session_state["monetization_workflow_id"] = selected_wf_id
    
    workflow = next(w for w in workflows if w["workflow_id"] == selected_wf_id)
    
    st.markdown(f"**現在の工程:** {workflow.get('current_step', workflow.get('stage', ''))} (コンテンツ版数: {workflow.get('content_version', 1)})")
    
    # Render inline editable fields
    edit_note_title = st.text_input("noteタイトル", value=workflow["note"]["title"], key=f"edit_title_{workflow['workflow_id']}")
    edit_note_body = st.text_area("note本文", value=workflow["note"]["body"], height=250, key=f"edit_body_{workflow['workflow_id']}")
    edit_threads_text = st.text_area("Threads投稿内容", value=workflow["threads"]["text"], height=150, key=f"edit_text_{workflow['workflow_id']}")
    
    if st.button("編集内容を保存して再レビュー", key=f"save_edit_{workflow['workflow_id']}"):
        updated_note = {
            "content_id": workflow["note"]["content_id"],
            "type": "note",
            "title": edit_note_title,
            "body": edit_note_body,
            "cta": workflow["note"].get("cta", ""),
            "cta_url": workflow["note"].get("cta_url", ""),
            "revenue_purpose": workflow["note"].get("revenue_purpose", "")
        }
        updated_threads = {
            "content_id": workflow["threads"]["content_id"],
            "type": "threads",
            "title": edit_note_title,
            "text": edit_threads_text,
            "cta": workflow["threads"].get("cta", ""),
            "source_note_id": workflow["note"]["content_id"],
            "revenue_purpose": workflow["threads"].get("revenue_purpose", "")
        }
        with st.spinner("コンテンツ更新および再レビューの検証中..."):
            api.monetization.update_content(workflow["workflow_id"], channel="note", content=updated_note)
            api.monetization.update_content(workflow["workflow_id"], channel="threads", content=updated_threads)
            st.success("コンテンツが更新され、自動再レビューが完了しました。")
            st.rerun()
            
    # Review results
    note_review = workflow["reviews"]["note"]
    threads_review = workflow["reviews"]["threads"]
    
    st.markdown("#### 自動レビュー結果")
    c_rev1, c_rev2 = st.columns(2)
    with c_rev1:
        if note_review.get("passed"):
            st.success("note自動レビュー: 合格")
        else:
            st.warning("note自動レビュー: 警告あり")
            for warning in note_review.get("warnings", []):
                st.write(f"- ⚠️ {warning}")
    with c_rev2:
        if threads_review.get("passed"):
            st.success("Threads自動レビュー: 合格")
        else:
            st.warning("Threads自動レビュー: 警告あり")
            for warning in threads_review.get("warnings", []):
                st.write(f"- ⚠️ {warning}")
                
    st.markdown("#### 人間承認と投稿実行")
    approver = st.text_input("承認者名（人間による明示入力）", key=f"approver_{workflow['workflow_id']}")
    approval = workflow.get("approval", {})
    
    col_btn1, col_btn2 = st.columns(2)
    
    # Enable approve only if review warnings are resolved
    can_approve = note_review.get("passed") and threads_review.get("passed")
    if not can_approve:
        st.warning("自動レビュー警告を解消（編集・保存）するまで承認は行えません。")
        
    if col_btn1.button("人間レビュー完了・承認", disabled=bool(approval) or not approver.strip() or not can_approve, key=f"approve_money_{workflow['workflow_id']}", use_container_width=True):
        api.approve_monetization_package_endpoint(workflow["workflow_id"], approver=approver)
        st.success("本文ハッシュと版数を固定して承認しました。")
        st.rerun()
        
    if approval:
        st.json({
            "approval_id": approval.get("approval_id"),
            "content_hash": approval.get("content_hash"),
            "approver": approval.get("approver"),
            "approved_at": approval.get("approved_at"),
            "approved_content_version": approval.get("approved_content_version"),
        })
        
    if col_btn2.button("承認済み記事をnote／ThreadsへDry Run投稿", disabled=not bool(approval) or workflow.get("stage") == "DryRunSucceeded", key=f"dryrun_money_{workflow['workflow_id']}", use_container_width=True):
        result = api.dry_run_monetization_package_endpoint(workflow["workflow_id"])
        st.success("Dry Runを完了しました。外部公開は0件です。") if result.get("stage") == "DryRunSucceeded" else st.error("安全停止しました。自動再試行は行いません。")
        st.rerun()
        
    if workflow.get("dry_run_result"):
        st.json({"Dry Run結果": workflow.get("dry_run_result", {}), "監査ログ参照先": workflow.get("audit_log_path", summary.get("audit_log_path", ""))})
    st.page_link("pages/48_Phase9_Revenue.py", label="Phase 9 投稿確認・共通履歴", icon="💴", use_container_width=True)


def _render_chat_workspace(api: CommanderAPI, queue: CommanderQueue, summary: dict[str, Any]) -> None:
    st.markdown('<div class="cmd-shell">', unsafe_allow_html=True)
    st.markdown("#### Commander Workspace")
    st.markdown('<div class="cmd-route">Dashboardで今日のタスク確認 → Commanderで作業開始 → DryRun → Review → 完了 → Dashboardで進捗確認</div>', unsafe_allow_html=True)

    current = summary.get("current_job", {})
    next_action = summary.get("executive", {}).get("next_action") or {}
    next_task = next_action.get("business_task", {})
    pending_review = summary.get("dashboard", {}).get("pending_review", [])
    queued = summary.get("queue", [])
    history = summary.get("history", [])

    context_cols = st.columns([1.4, 1, 1, 1])
    context_cols[0].markdown(
        f"""
        <div class="cmd-context">
          <strong>現在の作業コンテキスト</strong><br>
          {next_task.get('title') or next_action.get('instruction') or current.get('instruction') or '今日の収益導線タスクを開始できます。'}
        </div>
        """,
        unsafe_allow_html=True,
    )
    context_cols[1].metric("Queue", len(queued))
    context_cols[2].metric("Review待ち", len(pending_review))
    context_cols[3].metric("DryRun", "ON")

    if "commander_messages" not in st.session_state:
        st.session_state["commander_messages"] = [
            {"role": "ai", "content": summary.get("executive", {}).get("message", "今日のタスクを選んで作業を開始できます。")}
        ]

    for message in st.session_state["commander_messages"][-6:]:
        role_class = "cmd-user" if message.get("role") == "user" else "cmd-ai"
        label = "You" if message.get("role") == "user" else "AIOS"
        st.markdown(
            f'<div class="cmd-chat {role_class}"><strong>{label}</strong><br>{message.get("content", "")}</div>',
            unsafe_allow_html=True,
        )

    default_prompt = st.session_state.pop(
        "commander_prefill",
        "AIOS開発記録をnote、Threads、公式サイトへ展開する。DryRunでレビュー可能な形まで進める。",
    )
    st.markdown('<div class="cmd-fixed-input">', unsafe_allow_html=True)
    instruction = st.text_area("Commanderへの自然文指示", value=default_prompt, height=105, key="commander_chat_instruction")
    target_files_text = st.text_input("対象ファイル（任意・カンマ区切り）", value="", key="commander_chat_targets")

    action_cols = st.columns([1, 1, 1, 1, 1, 1])
    if action_cols[0].button("作業開始", type="primary", use_container_width=True, key="chat_start_work"):
        target_files = [item.strip() for item in target_files_text.split(",") if item.strip()]
        result = api.enqueue_instruction(instruction, priority=90, target_files=target_files, dry_run=True)
        if result.get("ok"):
            st.session_state["commander_messages"].append({"role": "user", "content": instruction})
            st.session_state["commander_messages"].append({"role": "ai", "content": f"Jobを作成しました: {result['job']['job_id']}。次はDryRunで安全確認します。"})
            st.success(f"Queued: {result['job']['job_id']}")
        else:
            st.error(result.get("error", "Job作成に失敗しました"))
        st.rerun()

    if action_cols[1].button("Mission実行", type="primary", use_container_width=True, key="chat_run_mission"):
        mission_instruction = instruction or "今日の初収益ミッションをnote、Threads、公式サイトへ展開する。DryRunでレビュー可能な形まで進める。"
        result = api.enqueue_instruction(mission_instruction, engine="revenue", priority=95, target_files=[], dry_run=True)
        if result.get("ok"):
            st.session_state["commander_messages"].append({"role": "user", "content": mission_instruction})
            st.session_state["commander_messages"].append({"role": "ai", "content": f"Missionを開始しました: {result['job']['job_id']}。次にDryRun実行を押してください。"})
            st.success(f"Mission queued: {result['job']['job_id']}")
        else:
            st.error(result.get("error", "Mission作成に失敗しました"))
        st.rerun()

    dryrun_disabled = not bool(queue.next_job())
    if action_cols[2].button("DryRun実行", use_container_width=True, disabled=dryrun_disabled, key="chat_dryrun"):
        with st.spinner("DryRunを実行中です。実ファイル適用や本番投稿は行いません。"):
            result = CommanderWorker(queue).process_next(dry_run=True)
        st.session_state["commander_messages"].append({"role": "ai", "content": f"DryRun結果: {result.get('status', 'unknown')}。レビュー待ちに進められるか確認してください。"})
        st.json(result)
        st.rerun()

    review_job = next((job for job in queued + history if job.get("status") == "dry_run_completed"), None)
    if action_cols[3].button("レビュー送信", use_container_width=True, disabled=review_job is None, key="chat_review"):
        result = api.approve_endpoint(review_job["job_id"], approved_by="human_review")
        st.session_state["commander_messages"].append({"role": "ai", "content": f"レビュー結果: {result.get('job', {}).get('job_id', review_job['job_id'])} をApprovedへ更新しました。"})
        st.json(result)
        st.rerun()

    task_data = load_tasks()
    task_options = [task for task in task_data.get("tasks", []) if task.get("status") != "done"]
    selected_label = ""
    if task_options:
        labels = [f"{STATUS_LABEL.get(task.get('status', ''), task.get('status', ''))} / {task.get('title', '')}" for task in task_options]
        selected_label = st.selectbox("完了にする当日タスク", labels, key="chat_task_complete_select")
    if action_cols[4].button("タスク完了", use_container_width=True, disabled=not task_options, key="chat_complete_task"):
        index = labels.index(selected_label)
        update_task_status(task_options[index]["id"], "done")
        st.session_state["commander_messages"].append({"role": "ai", "content": f"タスク完了にしました: {task_options[index].get('title', '')}。Dashboardで進捗を確認してください。"})
        st.rerun()

    action_cols[5].page_link("pages/8_Dashboard.py", label="Dashboardへ戻る", icon="📊", use_container_width=True)

    chat_prompt = st.chat_input("AIOSに自然文で依頼する")
    if chat_prompt:
        result = api.enqueue_instruction(chat_prompt, priority=90, target_files=[], dry_run=True)
        st.session_state["commander_messages"].append({"role": "user", "content": chat_prompt})
        st.session_state["commander_messages"].append({"role": "ai", "content": f"受け取りました。DryRun前提のJobとしてQueueへ追加しました: {result.get('job', {}).get('job_id', '')}"})
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    log_rows = []
    for job in (queued + history)[:6]:
        log_rows.append(
            {
                "job_id": job.get("job_id", ""),
                "status": STATUS_LABELS.get(job.get("status", ""), job.get("status", "")),
                "instruction": job.get("instruction", "")[:80],
                "dry_run": job.get("dry_run", True),
                "updated_at": job.get("updated_at", job.get("finished_at", "")),
            }
        )
    st.markdown("##### 実行ログ")
    if log_rows:
        st.dataframe(pd.DataFrame(log_rows), use_container_width=True, hide_index=True)
    else:
        st.info("まだCommander実行ログはありません。自然文で作業を開始してください。")
    st.markdown("</div>", unsafe_allow_html=True)


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
