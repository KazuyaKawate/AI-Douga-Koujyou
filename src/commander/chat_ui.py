from __future__ import annotations

from typing import Any

import streamlit as st

from src.commander.api import CommanderAPI
from src.commander.chat_store import (
    CommanderChatStore,
    PROGRESS_STAGES,
    TERMINAL,
    active_stage_index,
    mask_secrets,
    poll_job,
    progress_label,
    progress_value,
    result_text,
    safe_chat_context,
    status_text,
    stream_text_chunks,
)
from src.commander.queue import CommanderQueue


@st.dialog("会話履歴を削除")
def _confirm_delete(store: CommanderChatStore, conversation_id: str) -> None:
    st.warning("この会話だけを削除します。Commander QueueとJob履歴には影響しません。")
    if st.button("削除する", type="primary", key=f"confirm_delete_{conversation_id}"):
        store.delete(conversation_id)
        st.session_state.pop("commander_conversation_id", None)
        st.rerun()


def _render_progress_steps(status: str) -> None:
    active = active_stage_index(status)
    parts = []
    for index, (_, label) in enumerate(PROGRESS_STAGES):
        if index < active:
            parts.append(f"✓ {label}")
        elif index == active:
            parts.append(f"**{label}**")
        else:
            parts.append(label)
    st.caption(" → ".join(parts))


def _stream_saved_response(text: str) -> None:
    """Stream local text only; this function never calls a provider."""
    st.write_stream(iter(stream_text_chunks(text)))


def _render_review_context(api: CommanderAPI, job_id: str = "") -> None:
    context = safe_chat_context(api.commander_chat_context_endpoint(job_id))
    tabs = st.tabs(["Workflow Preview", "Engine Routing", "DryRun Result", "Approval Queue", "Integrations"])
    with tabs[0]:
        preview = context.get("workflow_preview", {})
        st.caption(f"状態: {status_text(preview.get('status', 'idle'))}")
        st.json({"steps": preview.get("steps", []), "impacted_files": preview.get("impacted_files", []), "diff_preview": preview.get("diff_preview", {})})
    with tabs[1]:
        routing = context.get("engine_routing", {})
        st.markdown(" → ".join(routing.get("route", ["commander"])))
        st.caption(f"Selected Engine: {routing.get('selected', 'commander')}")
    with tabs[2]:
        result = context.get("dry_run_result", {})
        st.json(result) if result else st.info("DryRun結果はまだありません。")
        st.caption("dry_run=true / execute_allowed=false / external_request_sent=false")
    with tabs[3]:
        rows = context.get("approval_queue", [])
        if rows:
            for row in rows[:10]:
                st.markdown(f"**{row.get('title') or row.get('queue_id', 'Review item')}**")
                st.caption(f"{row.get('target_platform', '')} · {row.get('status', '')} · Approval Required")
        else:
            st.info("承認待ち項目はありません。")
    with tabs[4]:
        mobile = context.get("mobile_review_hub", {})
        publish = context.get("common_publish_queue", {})
        google = context.get("google_workspace", {})
        revenue = context.get("revenue_engine", {})
        cols = st.columns(4)
        cols[0].metric("Mobile Review", mobile.get("count", 0))
        cols[1].metric("Publish Queue", publish.get("count", 0))
        cols[2].metric("Google Workspace", google.get("label", "未確認"))
        cols[3].metric("Revenue Engine", "Compatible" if isinstance(revenue, dict) else "Unknown")
        st.caption("既存連携の状態を読み取り専用で表示しています。")


def execute_chat_job(
    api: CommanderAPI,
    queue: CommanderQueue,
    store: CommanderChatStore,
    conversation_id: str,
    job: dict[str, Any],
) -> dict[str, Any]:
    """Run one newly queued chat job through the existing Worker in safe DryRun mode."""
    job_id = str(job.get("job_id", ""))
    try:
        result = api.worker.process_job(job, dry_run=True)
        persisted = queue.get_job(job_id) or job
        final_status = str(persisted.get("status", result.get("status", "failed")))
        store.sync_job_status(conversation_id, job_id, final_status)
        body = result_text(persisted.get("result") or result)
        if final_status == "failed":
            body = f"処理に失敗しました。{body}"
        elif final_status == "rejected":
            body = f"安全確認により処理を停止しました。{body}"
        store.add(
            conversation_id,
            role="assistant",
            content=body,
            job_id=job_id,
            engine=persisted.get("engine", job.get("engine", "commander")),
            status=final_status,
            result_reference=job_id,
        )
        return {"ok": final_status not in {"failed", "rejected"}, "job": persisted, "result": result}
    except Exception as exc:
        safe_error = str(mask_secrets(str(exc)))
        failure = {"status": "failed", "error": safe_error, "dry_run": True}
        persisted = queue.get_job(job_id) or job
        if persisted.get("status") not in TERMINAL:
            queue.finish_job(job_id, "failed", failure)
        store.sync_job_status(conversation_id, job_id, "failed")
        store.add(
            conversation_id,
            role="assistant",
            content=f"処理に失敗しました。{safe_error}",
            job_id=job_id,
            engine=job.get("engine", "commander"),
            status="failed",
            result_reference=job_id,
        )
        return {"ok": False, "job": queue.get_job(job_id) or job, "error": safe_error}


@st.fragment(run_every="2s")
def _render_live_progress(queue: CommanderQueue, store: CommanderChatStore, conversation_id: str, job_id: str) -> None:
    """Refresh one job without rerunning the full chat page or executing the job."""
    checked = poll_job(queue.get_job, job_id, timeout=0)
    job = checked.get("job") or {}
    status = job.get("status", "waiting")
    last_key = f"commander_live_status_{job_id}"
    previous = st.session_state.get(last_key)
    if previous != status:
        st.session_state[last_key] = status
        store.sync_job_status(conversation_id, job_id, status)
    st.progress(progress_value(status), text=f"現在工程: {progress_label(status)}")
    _render_progress_steps(status)
    st.caption("待機 → 計画 → 実行 → DryRun完了 → 承認待ち → 完了（2秒間隔・自動再実行なし）")


def render_chat_ui(api: CommanderAPI, queue: CommanderQueue, summary: dict[str, Any]) -> None:
    store = CommanderChatStore()
    conversations = store.list()
    if not conversations:
        conversations = [store.create()]
    active_id = st.session_state.get("commander_conversation_id", conversations[0]["conversation_id"])
    if not store.load(active_id):
        active_id = conversations[0]["conversation_id"]
    st.session_state["commander_conversation_id"] = active_id

    safe = st.columns(4)
    safe[0].metric("Dry Run", "ON")
    safe[1].metric("Review Required", "ON")
    safe[2].metric("Production", "OFF")
    current = summary.get("current_job", {})
    safe[3].metric("Engine", current.get("engine", "Commander"))
    st.markdown('<div class="cmd-command-deck"><strong>Commander Chat MVP</strong><span>Chat → Preview → DryRun → Human Approval</span></div>', unsafe_allow_html=True)

    controls = st.columns([3, 1, 1])
    options = {f"{row.get('title', '会話')} · {row['conversation_id'][-6:]}": row["conversation_id"] for row in conversations}
    labels = list(options)
    selected = controls[0].selectbox("会話履歴", labels, index=labels.index(next(label for label, cid in options.items() if cid == active_id)), key="commander_chat_history")
    selected_id = options[selected]
    if selected_id != active_id:
        st.session_state["commander_conversation_id"] = selected_id
        st.rerun()
    if controls[1].button("新しい会話", key="commander_new_chat", use_container_width=True):
        st.session_state["commander_conversation_id"] = store.create()["conversation_id"]
        st.rerun()
    if controls[2].button("履歴削除", key="commander_delete_chat", use_container_width=True):
        _confirm_delete(store, active_id)

    conversation = store.load(active_id) or store.create()
    if not conversation["messages"]:
        store.add(active_id, role="assistant", content="こんにちは。AIOS Commanderです。初収益に近い作業をDry Runで受け付けます。")
        conversation = store.load(active_id) or conversation

    for message in conversation["messages"]:
        role = "user" if message.get("role") == "user" else "assistant"
        live_status = message.get("status", "")
        job_id = message.get("job_id", "")
        if job_id:
            live_job = queue.get_job(job_id)
            if live_job:
                live_status = live_job.get("status", live_status)
        with st.chat_message(role):
            st.markdown(message.get("content", ""))
            created_at = message.get("created_at", "")
            if live_status:
                approval = "承認済み" if live_status in {"approved", "execute_ready", "completed"} else "承認待ち"
                st.caption(
                    f"{created_at} · 状態: {status_text(live_status)} · Queue: {live_status} · "
                    f"{approval} · Dry Run: ON · Engine: {message.get('engine', 'commander')}"
                )
            elif created_at:
                st.caption(created_at)

    # Reload-safe result recovery. Never retries or executes the job.
    for message in list(conversation["messages"]):
        job_id = message.get("job_id", "")
        if not job_id or message.get("role") != "user":
            continue
        job = queue.get_job(job_id)
        if job and job.get("status") in TERMINAL and not any(row.get("result_reference") == job_id for row in conversation["messages"]):
            body = result_text(job.get("result", {}))
            if job.get("status") == "failed":
                body = f"処理に失敗しました。{body}"
            store.add(active_id, role="assistant", content=body, job_id=job_id, engine=job.get("engine", "commander"), status=job.get("status", ""), result_reference=job_id)
            st.rerun()

    prompt = st.chat_input("AIOSに依頼する（Dry Run・人間レビュー必須）", key="commander_chat_input")
    if prompt:
        release_request = "note" in prompt.lower() and any(word in prompt for word in ("公開準備", "投稿用に整形", "公開パッケージ"))
        publish_record_request = "note" in prompt.lower() and "URLを登録" in prompt
        kpi_request = "note" in prompt.lower() and any(word in prompt for word in ("実績を入力", "KPIを入力"))
        note_request = "note" in prompt.lower() and any(word in prompt for word in ("書いて", "作って", "記事"))
        existing = next((row for row in reversed(conversation["messages"]) if row.get("role") == "user" and row.get("content") == prompt and row.get("status") in {"waiting", "planning", "running"}), None)
        if existing:
            st.warning("同じ依頼は処理中です。二重登録しませんでした。")
        elif release_request:
            response = api.prepare_latest_note_release_endpoint(source_conversation_id=active_id)
            store.add(active_id, role="user", content=prompt, engine="note_workspace", status="completed")
            store.add(active_id, role="assistant", content=response.get("message", "公開準備結果を確認してください。"), engine="note_workspace", status="completed" if response.get("ok") else "failed")
        elif publish_record_request:
            store.add(active_id, role="user", content=prompt, engine="note_workspace", status="completed")
            store.add(active_id, role="assistant", content="Note Workspaceの「公開準備」タブで、公開URL・日時・確認者を入力してください。AIOSはnoteへの投稿を行いません。", engine="note_workspace", status="completed")
        elif kpi_request:
            store.add(active_id, role="user", content=prompt, engine="note_workspace", status="completed")
            store.add(active_id, role="assistant", content="Note Workspaceの「投稿履歴・KPI」タブで実績を手動入力できます。未取得と0は区別して保存します。", engine="note_workspace", status="completed")
        elif note_request:
            response = api.create_note_article_endpoint(prompt)
            article = response["article"]
            store.add(active_id, role="user", content=prompt, engine="note_workspace", status="completed")
            store.add(active_id, role="assistant", content=f"note記事「{article['title']}」を生成し、Review Queueへ追加しました。本番投稿は行いません。", engine="note_workspace", status=article["status"])
        else:
            response = api.enqueue_instruction(prompt, priority=90, target_files=[], dry_run=True)
            if response.get("ok"):
                job = response["job"]
                store.add(active_id, role="user", content=prompt, job_id=job["job_id"], engine=job.get("engine", "commander"), status="waiting")
                store.add(active_id, role="assistant", content="依頼を受け付けました。Dry Run Queueで人間レビュー前まで処理します。", job_id=job["job_id"], engine=job.get("engine", "commander"), status="waiting")
                with st.status("AIOSがDry Runを実行中です", expanded=True) as run_status:
                    st.write(f"Queue: waiting · Job: {job['job_id']}")
                    execution = execute_chat_job(api, queue, store, active_id, job)
                    final_job = execution.get("job", {})
                    final_status = final_job.get("status", "failed")
                    st.write(f"Queue: {final_status} · Approval: {'required' if final_status == 'dry_run_completed' else final_status}")
                    _stream_saved_response(result_text(final_job.get("result", execution.get("result", {}))))
                    run_status.update(
                        label=f"Dry Run: {status_text(final_status)}",
                        state="complete" if execution.get("ok") else "error",
                    )
            else:
                store.add(active_id, role="assistant", content=f"受付に失敗しました。{response.get('error', '')}", status="failed")
        st.rerun()

    jobs = [queue.get_job(row.get("job_id", "")) for row in conversation["messages"] if row.get("job_id")]
    jobs = [job for job in jobs if job]
    if jobs:
        latest = jobs[-1]
        _render_review_context(api, latest["job_id"])
        _render_live_progress(queue, store, active_id, latest["job_id"])
        with st.status(f"現在工程: {progress_label(latest.get('status', ''))}", expanded=False):
            st.write("自動再実行・本番操作は行いません。ブラウザ再読込後もjob_idから復元します。")
        if latest.get("status") == "dry_run_completed":
            st.warning("承認待ちです。内容を確認し、既存Commanderの承認または差し戻しを選択してください。")
            actions = st.columns(2)
            if actions[0].button("承認", key=f"chat_approve_{latest['job_id']}"):
                api.approve_endpoint(latest["job_id"], approved_by="human")
                queue.update_job(latest["job_id"], dry_run=True, execute_allowed=False, production_actions_enabled=False)
                st.rerun()
            if actions[1].button("差し戻し", key=f"chat_reject_{latest['job_id']}"):
                api.reject_endpoint(latest["job_id"], reason="Commander Chatから人間が差し戻し", rejected_by="human")
                st.rerun()
    else:
        _render_review_context(api)

    with st.expander("詳細・デバッグ情報", expanded=False):
        st.json(mask_secrets({"conversation": conversation, "jobs": jobs, "queue_status": summary.get("status_counts", {})}))
