"""
Factory Dashboard — AI基盤の状態を一画面で確認する管理ページ。

表示内容:
  Git状態 / AI Provider状態 / APIキー設定状況
  今日のToken使用量・推定コスト / Memory件数 / Snapshot日時
  Task Queue (将来: Mobile Inbox 接続予定) / 最新エラー
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.dashboard.collector import DashboardCollector

# ---- ページ設定 -------------------------------------------------------

st.set_page_config(
    page_title="Factory Dashboard",
    page_icon="🏭",
    layout="wide",
)

# ---- データ収集 -------------------------------------------------------

@st.cache_data(ttl=30, show_spinner="データを収集中...")
def _collect():
    # logger / memory は将来 st.session_state から注入予定
    logger = st.session_state.get("ai_logger")
    memory = st.session_state.get("ai_memory")
    return DashboardCollector(logger=logger, memory=memory).collect()


# ---- ヘッダー --------------------------------------------------------

hdr_col, btn_col = st.columns([9, 1])
with hdr_col:
    st.title("🏭 Factory Dashboard")
with btn_col:
    st.write("")
    if st.button("🔄 更新", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

data = _collect()
st.caption(f"最終更新: {data.collected_at.strftime('%Y-%m-%d %H:%M:%S')}")
st.divider()

# ---- Row 1: Git / AI Provider ----------------------------------------

col_git, col_prov = st.columns(2)

with col_git:
    st.subheader("Git / Project")
    git = data.git
    if git.error:
        st.error(f"Git エラー: {git.error}")
    else:
        m1, m2 = st.columns(2)
        m1.metric("Branch", git.branch or "---")
        m2.metric("未Push", f"{git.unpushed_count} 件")
        if git.latest_hash:
            st.code(f"{git.latest_hash}  {git.latest_message}", language=None)

with col_prov:
    st.subheader("AI Provider")
    provider_cols = st.columns(max(len(data.providers), 1))
    for col, ps in zip(provider_cols, data.providers):
        with col:
            if ps.enabled and ps.has_api_key:
                badge = "✅"
            elif ps.enabled:
                badge = "⚠️"
            else:
                badge = "⬜"
            st.metric(f"{badge} {ps.name.capitalize()}", ps.model or "---")

    total  = data.api_keys.total_count
    cfgd   = data.api_keys.configured_count
    st.caption(f"APIキー設定済み: {cfgd} / {total}")

st.divider()

# ---- Row 2: 使用量 / インフラ ----------------------------------------

col_usage, col_infra = st.columns(2)

with col_usage:
    st.subheader("今日の使用量")
    u = data.usage_today
    u1, u2, u3 = st.columns(3)
    u1.metric("Tokens",   f"{u.total_tokens:,}")
    u2.metric("Cost",     f"${u.total_cost_usd:.4f}")
    u3.metric("Requests", u.request_count)
    if u.total_tokens == 0:
        st.caption("※ InMemoryLogger を AIRouter に注入すると集計されます")

with col_infra:
    st.subheader("インフラ状態")
    i = data.infra

    i1, i2 = st.columns(2)
    i1.metric("Memory", f"{i.memory_count} 件")
    sheets_label = "✅ 接続" if i.sheets_connected else "⬜ 未接続"
    i2.metric("Sheets", sheets_label)

    snap = i.snapshot
    if snap.exists and snap.created_at:
        st.caption(
            f"Snapshot: {snap.created_at}"
            + (f"  (schema: {snap.schema_version})" if snap.schema_version else "")
        )
    elif snap.error:
        st.caption(f"Snapshot: エラー — {snap.error}")
    else:
        st.caption("Snapshot: なし")

    st.caption(f"Logger: {i.logger_type}")

st.divider()

# ---- Row 3: Task Queue -----------------------------------------------

st.subheader("Task Queue")
tq = data.task_queue
q1, q2, q3 = st.columns(3)
q1.metric("Pending",     tq.pending)
q2.metric("実行中",      tq.running)
q3.metric("完了(今日)",  tq.completed_today)
st.caption("Factory Mobile Inbox 実装後に接続予定")

st.divider()

# ---- Row 4: 最新エラー -----------------------------------------------

with st.expander("最新エラー (直近5件)"):
    errors = data.recent_errors
    if errors:
        for e in errors:
            st.error(f"{e.timestamp}  [{e.provider}]  {e.message}")
    else:
        st.info("エラーなし（InMemoryLogger 未注入時は常に空）")
