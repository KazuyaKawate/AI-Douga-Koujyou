"""AIOS Dashboard — メインエントリポイント。

起動方法:
    streamlit run dashboard/app.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

# ページ設定（最初に呼ぶ必要あり）
st.set_page_config(
    page_title = "AIOS Dashboard",
    page_icon  = "🤖",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

from dashboard.utils import init_kernel, FACTORY_ICONS

# ── CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: #1e1e2e;
    border: 1px solid #313244;
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
}
.metric-value { font-size: 2.2rem; font-weight: 700; color: #cba6f7; }
.metric-label { font-size: 0.85rem; color: #a6adc8; margin-top: 0.3rem; }
.factory-badge {
    display: inline-block;
    background: #313244;
    border-radius: 6px;
    padding: 0.2rem 0.6rem;
    margin: 0.15rem;
    font-size: 0.8rem;
    color: #cdd6f4;
}
</style>
""", unsafe_allow_html=True)

# ── Kernel 初期化 ────────────────────────────────────────────────
@st.cache_resource(ttl=300)
def _kernel():
    return init_kernel()

try:
    kernel = _kernel()
    kernel_ok = True
except Exception as e:
    kernel_ok = False
    st.error(f"Kernel 初期化エラー: {e}")

# ── ホーム画面 ───────────────────────────────────────────────────
st.title("🤖 AIOS Dashboard")
st.caption("AI Operating System — 自己成長するAI基盤")

if not kernel_ok:
    st.stop()

col1, col2, col3, col4 = st.columns(4)

factories  = kernel.registry.list_factories()
workflows  = kernel.registry.list_workflows()

from src.ai_agents.registry import get_agent_registry
agents = get_agent_registry().list_all()

from src.intelligence.tracker import get_tracker
records = get_tracker().load_all()
success_count = sum(1 for r in records if r.success)
success_rate  = (success_count / len(records) * 100) if records else 0.0

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{len(factories)}</div>
        <div class="metric-label">🏭 Factories</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{len(workflows)}</div>
        <div class="metric-label">⚡ Workflows</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{len(agents)}</div>
        <div class="metric-label">🤖 Agents</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{len(records)}</div>
        <div class="metric-label">📊 実行履歴</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── Factory 一覧カード ───────────────────────────────────────────
st.subheader("登録済み Factory")
cols = st.columns(5)
for i, fid in enumerate(sorted(factories)):
    icon = FACTORY_ICONS.get(fid, "🔧")
    wf_count = sum(1 for w in workflows if w.startswith(fid + "."))
    with cols[i % 5]:
        st.markdown(f"""
        <div class="metric-card" style="padding:0.8rem;">
            <div style="font-size:1.5rem;">{icon}</div>
            <div style="font-weight:600;color:#cdd6f4;font-size:0.9rem;margin-top:0.3rem;">{fid}</div>
            <div style="color:#a6adc8;font-size:0.75rem;">{wf_count} workflows</div>
        </div>""", unsafe_allow_html=True)

st.divider()

# ── 最近の実行履歴 ────────────────────────────────────────────────
st.subheader("最近の実行履歴")
recent = get_tracker().load_recent(10)
if recent:
    import pandas as pd
    df = pd.DataFrame([{
        "時刻":    r.timestamp,
        "Workflow": r.workflow_name,
        "Factory":  r.factory_id,
        "成否":     "✓" if r.success else "✗",
        "時間(ms)": r.duration_ms,
        "出力(文字)": r.output_chars,
    } for r in recent])
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("まだ実行履歴がありません。左のメニューから Workflow を実行してください。")

# ── ナビゲーション案内 ────────────────────────────────────────────
st.divider()
st.caption("左のサイドバーからページを選択してください: Workflow実行 / Memory / Marketplace / Agents / Scheduler / Composer")
