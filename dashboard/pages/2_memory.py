"""Memory Intelligence ページ。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="Memory Intelligence", page_icon="🧠", layout="wide")
st.title("🧠 Memory Intelligence")
st.caption("実行履歴の分析・成功率・Agent ランキング・改善提案")

from src.intelligence.tracker  import get_tracker
from src.intelligence.analyzer import IntelligenceAnalyzer
from dashboard.utils           import init_kernel

@st.cache_resource(ttl=300)
def _kernel():
    return init_kernel()

_kernel()  # agents auto-load

# ── サイドバー: 期間設定 ─────────────────────────────────────────
period = st.sidebar.slider("分析期間 (日)", 1, 90, 30)
analyzer = IntelligenceAnalyzer()

with st.spinner("分析中..."):
    report = analyzer.analyze(period_days=period)

# ── メトリクス ────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("総実行数",    report.total_executions)
col2.metric("全体成功率",  f"{report.overall_success:.1f}%")
col3.metric("分析 Factory数", len(report.factory_stats))
col4.metric("改善提案数",  len(report.suggestions))

st.divider()

# ── タブ ─────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 Workflow統計", "🏭 Factory別", "🤖 Agentランキング", "💡 改善提案", "🗂 実行ログ"]
)

# ── Tab1: Workflow 統計 ──────────────────────────────────────────
with tab1:
    if report.workflow_stats:
        import pandas as pd
        df = pd.DataFrame([w.to_dict() for w in report.workflow_stats])
        df = df[["name","total","success","failure","success_rate","avg_ms","last_run"]]
        df.columns = ["Workflow","実行","成功","失敗","成功率(%)","平均(ms)","最終実行"]
        st.dataframe(df, use_container_width=True, hide_index=True)

        # 棒グラフ: 実行回数
        st.subheader("実行回数ランキング")
        top_wf = report.workflow_stats[:10]
        import pandas as pd
        chart_df = pd.DataFrame({
            "Workflow": [w.name.split(".")[-1] for w in top_wf],
            "実行回数": [w.total for w in top_wf],
        }).set_index("Workflow")
        st.bar_chart(chart_df)
    else:
        st.info(f"直近 {period} 日間の実行履歴がありません。Workflow を実行してください。")

# ── Tab2: Factory 別 ─────────────────────────────────────────────
with tab2:
    if report.factory_stats:
        import pandas as pd
        df = pd.DataFrame([f.to_dict() for f in report.factory_stats])
        df.columns = ["Factory","実行","成功","成功率(%)","Workflow数"]
        st.dataframe(df, use_container_width=True, hide_index=True)

        chart_df = pd.DataFrame({
            "Factory": [f.factory_id for f in report.factory_stats],
            "実行回数": [f.total for f in report.factory_stats],
        }).set_index("Factory")
        st.bar_chart(chart_df)
    else:
        st.info("Factory 実行データがありません。")

# ── Tab3: Agent ランキング ────────────────────────────────────────
with tab3:
    if report.agent_ranking:
        import pandas as pd
        df = pd.DataFrame([a.to_dict() for a in report.agent_ranking])
        df.columns = ["Agent","利用回数","成功率(%)"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Agent 実行記録がありません。Workflow 実行時に agent_ids を記録してください。")

    # 登録済み Agent 一覧
    st.subheader("登録済み Agent 一覧")
    from src.ai_agents.registry import get_agent_registry
    agents = get_agent_registry().list_all()
    if agents:
        import pandas as pd
        agent_df = pd.DataFrame([{
            "ID": a.agent_id,
            "名前": a.name,
            "バージョン": a.version,
            "役割": a.role,
            "タスク": a.task_type,
            "Factory": a.factory_id or "-",
            "有効": "✓" if a.enabled else "✗",
        } for a in agents])
        st.dataframe(agent_df, use_container_width=True, hide_index=True)

# ── Tab4: 改善提案 ────────────────────────────────────────────────
with tab4:
    if report.suggestions:
        for s in report.suggestions:
            icon = "⚠️" if s.level == "warning" else "ℹ️"
            with st.container():
                st.markdown(f"{icon} **{s.target}**")
                st.write(s.message)
                st.caption(f"{s.metric}: {s.value:.1f}")
                st.divider()
    else:
        st.success("改善提案なし — すべての Workflow が良好です！")

    # レポートを Markdown でダウンロード
    if report.total_executions > 0:
        md = report.to_markdown()
        st.download_button(
            "📥 レポートをダウンロード (Markdown)",
            data=md,
            file_name="aios_intelligence_report.md",
            mime="text/markdown",
        )

# ── Tab5: 実行ログ ────────────────────────────────────────────────
with tab5:
    records = get_tracker().load_recent(50)
    if records:
        import pandas as pd
        df = pd.DataFrame([{
            "時刻":       r.timestamp,
            "Workflow":   r.workflow_name,
            "Factory":    r.factory_id,
            "成否":       "✓" if r.success else "✗",
            "時間(ms)":  r.duration_ms,
            "出力(文字)": r.output_chars,
            "エラー":     r.error or "",
        } for r in records])
        st.dataframe(df, use_container_width=True, hide_index=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 ログ更新"):
                st.rerun()
        with col2:
            if st.button("🗑 ログクリア", type="secondary"):
                get_tracker().clear()
                st.success("ログをクリアしました")
                st.rerun()
    else:
        st.info("実行ログがありません。")

# ── AIOS Memory (従来 Memory) ────────────────────────────────────
st.divider()
st.subheader("🗃 AIOS Memory (従来メモリ)")

try:
    mem_path = Path("data/aios_memory.json")
    if mem_path.exists():
        import json
        mem_data = json.loads(mem_path.read_text(encoding="utf-8"))
        entries  = mem_data.get("entries", {})
        if entries:
            import pandas as pd
            rows = []
            for k, v in entries.items():
                rows.append({"キー": k, "値": str(v.get("value",""))[:100], "更新": v.get("updated_at","")})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("Memory は空です。")
    else:
        st.info("Memory ファイルがありません。")
except Exception as e:
    st.error(f"Memory 読み込みエラー: {e}")
