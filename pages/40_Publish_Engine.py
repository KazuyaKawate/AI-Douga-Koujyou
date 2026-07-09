from __future__ import annotations

import html
import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from src.publish_engine.publisher import PublishEngine


st.set_page_config(page_title="AIOS Publish Engine", page_icon="Publish", layout="wide")

st.markdown(
    """
    <style>
    .pe-card{background:#fff;border:1px solid #e6e9ef;border-radius:8px;padding:16px;min-height:116px;}
    .pe-number{font-size:30px;font-weight:760;color:#155e75;line-height:1.1;}
    .pe-label{color:#667085;font-size:13px;}
    div.stButton > button{min-height:52px;font-weight:700;border-radius:8px;}
    textarea{font-size:16px!important;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("AIOS Publish Engine")
st.caption("Manual Publish Mode: Threads/note投稿文を生成し、コピーして手動投稿、投稿済みチェックと履歴保存まで行います。")

engine = PublishEngine()
state = engine.load_state()
summary = engine.dashboard_summary()

cols = st.columns(6)
cols[0].markdown(f'<div class="pe-card"><div class="pe-number">{summary["waiting"]}</div><div class="pe-label">投稿待ち</div></div>', unsafe_allow_html=True)
cols[1].markdown(f'<div class="pe-card"><div class="pe-number">{summary["today_scheduled"]}</div><div class="pe-label">今日の公開予定</div></div>', unsafe_allow_html=True)
cols[2].markdown(f'<div class="pe-card"><div class="pe-number">{summary["success_rate"]}%</div><div class="pe-label">公開成功率</div></div>', unsafe_allow_html=True)
cols[3].markdown(f'<div class="pe-card"><div class="pe-number">{summary["errors"]}</div><div class="pe-label">エラー</div></div>', unsafe_allow_html=True)
cols[4].markdown(f'<div class="pe-card"><div class="pe-number">{summary["revenue"]:,}</div><div class="pe-label">収益</div></div>', unsafe_allow_html=True)
cols[5].markdown(f'<div class="pe-card"><div class="pe-number">{summary["roi"]}</div><div class="pe-label">ROI</div></div>', unsafe_allow_html=True)

st.subheader("Manual Publish Mode")
mode_cols = st.columns([1, 1, 2])
manual_mode = state.get("publish_mode", "manual") == "manual"
mode_cols[0].metric("Mode", "Manual" if manual_mode else "API")
mode_cols[1].metric("DryRun", "ON" if state.get("dry_run_default", True) else "OFF")
if mode_cols[2].button("Manual Publish Modeに切替", use_container_width=True):
    engine.set_publish_mode("manual")
    st.rerun()
dry_cols = st.columns(2)
if dry_cols[0].button("DryRun ON", use_container_width=True):
    engine.set_dry_run(True)
    st.rerun()
if dry_cols[1].button("DryRun OFF（手動投稿準備）", use_container_width=True):
    engine.set_dry_run(False)
    st.rerun()

st.subheader("Create Manual Drafts")
title = st.text_input("Title", value="AIOS初収益に向けた今日の投稿")
body = st.text_area("Body/Text", height=130, value="AIOSで生成した収益コンテンツを安全に公開し、分析と学習へ戻します。")
cta = st.text_input("CTA", value="詳しくは本文でまとめます。")
hashtags = st.text_input("Hashtags", value="AIOS 生成AI 副業")
priority = st.slider("Priority", min_value=1, max_value=100, value=80)
create_cols = st.columns(4)
if create_cols[0].button("Threads/note Draft作成", type="primary", use_container_width=True):
    items = engine.create_manual_pack(
        {
            "content_id": "",
            "title": title,
            "body": body,
            "text": body,
            "cta": cta,
            "hashtags": hashtags,
            "estimated_revenue": 12000,
        },
        priority=priority,
    )
    st.success("Draft: " + ", ".join(item.get("publish_id", "") for item in items))
    st.rerun()
if create_cols[1].button("Next Publish", use_container_width=True):
    result = engine.publish_next()
    st.json(result)
    st.rerun()
if create_cols[2].button("Refresh", use_container_width=True):
    st.rerun()

st.subheader("Queue")
queue = state.get("queue", [])
if queue:
    for item in queue[:20]:
        with st.container(border=True):
            row = st.columns([2, 1, 1, 1, 1])
            row[0].write(item.get("content", {}).get("title") or item.get("content", {}).get("text", "")[:60])
            row[0].caption(item.get("publish_id", ""))
            row[1].metric("Platform", item.get("platform", ""))
            row[2].metric("Status", item.get("status", ""))
            row[3].metric("Priority", item.get("priority", 0))
            if row[4].button("Approve", key=f"approve-{item.get('publish_id')}", use_container_width=True):
                engine.approve(item.get("publish_id", ""))
                st.rerun()
            action_row = st.columns([1, 1, 2])
            if action_row[0].button("Schedule", key=f"schedule-{item.get('publish_id')}", use_container_width=True):
                engine.schedule(item.get("publish_id", ""), days_from_now=0)
                st.rerun()
            if action_row[1].button("Publish", key=f"publish-{item.get('publish_id')}", use_container_width=True):
                result = engine.publish(item.get("publish_id", ""))
                st.json(result)
                st.rerun()
            copy_text = item.get("publish_result", {}).get("copy_text", "")
            if copy_text:
                button_id = f"copy-{item.get('publish_id')}"
                escaped_button = html.escape(button_id)
                components.html(
                    f"""
                    <button id="{escaped_button}" style="width:100%;height:44px;border-radius:8px;border:1px solid #0f766e;background:#0f766e;color:white;font-weight:700;cursor:pointer;">
                      {html.escape(item.get("publish_result", {}).get("copy_label", "コピー"))}
                    </button>
                    <script>
                    const button = document.getElementById({json.dumps(button_id)});
                    button.addEventListener("click", async () => {{
                      await navigator.clipboard.writeText({json.dumps(copy_text)});
                      button.textContent = "コピーしました";
                    }});
                    </script>
                    """,
                    height=52,
                )
                st.text_area(
                    item.get("publish_result", {}).get("copy_label", "コピー用テキスト"),
                    value=copy_text,
                    height=180 if item.get("platform") == "note" else 120,
                    key=f"copy-text-{item.get('publish_id')}",
                )
                st.code(copy_text, language="markdown")
                posted_url = st.text_input("投稿URL（任意）", key=f"posted-url-{item.get('publish_id')}")
                if st.checkbox("投稿済", key=f"posted-check-{item.get('publish_id')}"):
                    result = engine.mark_posted(item.get("publish_id", ""), posted_url=posted_url)
                    st.success(f"投稿済として保存しました: {result.get('publish_id')}")
                    st.rerun()
            with st.expander("Review / Result"):
                st.json({"review": item.get("review", {}), "approval": item.get("approval", {}), "publish_result": item.get("publish_result", {})})
else:
    st.info("Queue is empty.")

st.subheader("Analytics / History")
tabs = st.tabs(["History", "Analytics", "Retry", "Rollback", "Logs", "Knowledge", "Last Run"])
with tabs[0]:
    rows = [
        {
            "publish_id": item.get("publish_id", ""),
            "platform": item.get("platform", ""),
            "status": item.get("status", ""),
            "revenue": item.get("analytics", {}).get("revenue", 0),
            "roi": item.get("analytics", {}).get("roi", 0),
        }
        for item in state.get("history", [])
    ]
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
with tabs[1]:
    st.json(state.get("analytics", [])[:20])
with tabs[2]:
    st.json(state.get("retries", [])[:20])
with tabs[3]:
    st.json(state.get("rollbacks", [])[:20])
with tabs[4]:
    st.json(state.get("logs", [])[:30])
with tabs[5]:
    st.json(state.get("knowledge_history", [])[:20])
with tabs[6]:
    st.json(state.get("last_run", {}))
