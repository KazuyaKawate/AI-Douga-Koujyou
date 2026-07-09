from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from src.api_connectors.manager import APIConnectorManager


st.set_page_config(page_title="AIOS API Connectors", page_icon="API", layout="wide")

st.markdown(
    """
    <style>
    .api-card{background:#fff;border:1px solid #e6e9ef;border-radius:8px;padding:16px;min-height:116px;}
    .api-number{font-size:30px;font-weight:760;color:#0f766e;line-height:1.1;}
    .api-label{color:#667085;font-size:13px;}
    div.stButton > button{min-height:52px;font-weight:700;border-radius:8px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("AIOS API Connectors")
st.caption("Meta公式Threads API / note / WordPress / Webhookへ接続するための安全なConnector Layerです。DryRun既定、投稿前Review必須です。")

manager = APIConnectorManager()
summary = manager.dashboard_summary()

cols = st.columns(5)
cols[0].markdown(f'<div class="api-card"><div class="api-number">{summary["connected"]}</div><div class="api-label">接続状態</div></div>', unsafe_allow_html=True)
cols[1].markdown(f'<div class="api-card"><div class="api-number">{summary["auth_ready"]}</div><div class="api-label">認証状態</div></div>', unsafe_allow_html=True)
cols[2].markdown(f'<div class="api-card"><div class="api-number">{summary["api_remaining"]}</div><div class="api-label">API残量</div></div>', unsafe_allow_html=True)
cols[3].markdown(f'<div class="api-card"><div class="api-number">{summary["success_rate"]}</div><div class="api-label">投稿成功率</div></div>', unsafe_allow_html=True)
cols[4].markdown(f'<div class="api-card"><div class="api-number">{summary["history_count"]}</div><div class="api-label">投稿履歴</div></div>', unsafe_allow_html=True)

st.subheader("Connector Status")
status_df = pd.DataFrame(summary["connectors"])
st.dataframe(status_df, use_container_width=True, hide_index=True)

tabs = st.tabs(["Threads OAuth", "Manual設定", "DryRun", "実投稿", "Analytics準備", "最終投稿"])

with tabs[0]:
    st.subheader("Threads OAuth認証")
    st.caption("Meta公式 Threads API OAuth のみを使用します。ブラウザ自動投稿は使用しません。")
    client_id = st.text_input("Threads App ID / Client ID", value=os.getenv("THREADS_APP_ID", ""), type="password")
    client_secret = st.text_input("Threads App Secret", value=os.getenv("THREADS_APP_SECRET", ""), type="password")
    redirect_uri = st.text_input("Redirect URI", value=os.getenv("THREADS_REDIRECT_URI", "http://localhost:8501/44_API_Connectors"))
    state = st.text_input("OAuth State", value="aios-threads")
    if st.button("OAuth認証URLを生成", type="primary"):
        if not client_id or not redirect_uri:
            st.error("Client ID と Redirect URI を入力してください。")
        else:
            st.code(manager.threads_oauth_url(client_id=client_id, redirect_uri=redirect_uri, state=state))
    code = st.text_input("Callback code", type="password")
    if st.button("AccessToken / ThreadsUserID を自動取得して .env 保存"):
        if not all([code, client_id, client_secret, redirect_uri]):
            st.error("code / Client ID / Client Secret / Redirect URI が必要です。")
        else:
            result = manager.complete_threads_oauth(code=code, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri)
            if result.get("ok"):
                st.success(f"Threads OAuth complete: user_id={result.get('threads_user_id')} username={result.get('username')}")
                st.rerun()
            else:
                st.error("OAuth failed")
                st.json(result)
    if st.button("test_connection()"):
        st.json(manager.test_connection("threads"))

with tabs[1]:
    connector = st.selectbox("Connector", ["threads", "note", "wordpress", "webhook"])
    st.caption("秘密情報は暗号化保存され、画面には平文表示しません。Threads は OAuth 自動取得を推奨します。")
    if connector == "threads":
        token = st.text_input("Threads Access Token", type="password")
        user_id = st.text_input("Threads User ID", type="password")
        api_base = st.text_input("Threads API Base", value="https://graph.threads.net/v1.0")
        credentials = {"access_token": token, "user_id": user_id, "api_base": api_base}
    elif connector == "wordpress":
        api_url = st.text_input("WordPress URL", placeholder="https://example.com")
        username = st.text_input("Username", type="password")
        app_password = st.text_input("Application Password", type="password")
        credentials = {"api_url": api_url, "username": username, "app_password": app_password}
    elif connector == "webhook":
        url = st.text_input("Webhook URL", type="password")
        credentials = {"url": url}
    else:
        token = st.text_input("note Access Token / Webhook Token", type="password")
        credentials = {"access_token": token}
    enabled = st.checkbox("Connector有効化", value=False)
    if st.button("OAuth設定を保存", type="primary"):
        result = manager.configure_oauth(connector, credentials, enabled=enabled)
        st.success(f"Saved: {result['connector']} {result['auth_status']}")
        st.rerun()

with tabs[2]:
    title = st.text_input("Title", value="AIOS API Connector DryRun")
    text = st.text_area("Text", value="初収益に向けたAPI Connector DryRun投稿です。")
    review_ok = st.checkbox("投稿前Review承認済み", value=False)
    if st.button("DryRun投稿", type="primary"):
        result = manager.publish(
            "threads",
            {"title": title, "text": text, "content": {"title": title, "body": text, "text": text}},
            dry_run=True,
            approved=review_ok,
        )
        st.json(result)

with tabs[3]:
    st.subheader("Threads 実投稿")
    st.warning("実投稿は Meta公式 Threads API の create_post() → publish_post() のみを使用します。")
    live_text = st.text_area("Live Text", value="AIOS Threads API Connector Phase4 live test")
    live_confirm = st.checkbox("実投稿を承認します")
    if st.button("create_post() + publish_post() 実行", type="primary"):
        if not live_confirm:
            st.error("実投稿承認チェックが必要です。")
        else:
            created = manager.create_post("threads", live_text, dry_run=False)
            creation_id = created.get("body", {}).get("id", "") if isinstance(created.get("body"), dict) else ""
            published = manager.publish_post("threads", creation_id, dry_run=False) if creation_id else {"ok": False, "error": "creation_id missing"}
            st.json({"create_post": created, "publish_post": published})

with tabs[4]:
    analytics_connector = st.selectbox("Analytics Connector", ["threads", "note", "wordpress", "webhook"], key="analytics_connector")
    external_id = st.text_input("External ID", value="dry-test")
    if st.button("Analytics取得準備"):
        st.json(manager.analytics_prepare(analytics_connector, external_id))

with tabs[5]:
    st.json(summary.get("last_post", []))

