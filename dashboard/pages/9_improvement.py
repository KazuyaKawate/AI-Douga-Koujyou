"""Improvement — ImprovementEngine の分析結果と改善候補一覧。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

st.set_page_config(page_title="Improvement | AIOS", page_icon="📊", layout="wide")

@st.cache_resource(ttl=0)
def _load():
    from src.ai_agents.registry import get_agent_registry
    get_agent_registry().auto_load()
    from src.autonomous.improvement_engine import ImprovementEngine
    from src.autonomous.queue_manager import get_autonomous_queue
    return ImprovementEngine(), get_autonomous_queue()

engine, queue = _load()

st.title("📊 Improvement Engine")
st.caption("実行データを分析して改善候補を自動生成する")

tab_now, tab_history = st.tabs(["🔍 分析実行", "📜 分析履歴"])

# ═══════════════════════════════════════════════════════════════════
with tab_now:
    col1, col2 = st.columns([1, 3])
    period_days = col1.number_input("分析期間 (日)", value=30, min_value=1, max_value=365)

    if col2.button("▶ 改善候補を分析", type="primary"):
        with st.spinner("実行データを分析中..."):
            candidates = engine.analyze(int(period_days))
        st.session_state["candidates"] = [c.to_dict() for c in candidates]
        st.success(f"{len(candidates)} 件の改善候補を検出")

    candidates_raw = st.session_state.get("candidates") or [c.to_dict() for c in engine.load_latest_candidates()]

    if not candidates_raw:
        st.info("まだ分析結果がありません。「▶ 改善候補を分析」を実行してください。")
    else:
        # サマリーカード
        issue_types = {}
        for c in candidates_raw:
            issue_types[c["issue_type"]] = issue_types.get(c["issue_type"], 0) + 1

        cols = st.columns(len(issue_types) + 1 or 1)
        cols[0].metric("合計", len(candidates_raw))
        for i, (k, v) in enumerate(issue_types.items()):
            label = {"low_success_rate":"低成功率","slow_speed":"低速","unused":"未使用",
                     "ai_suggestion":"AI提案"}.get(k, k)
            cols[i+1].metric(label, v)

        st.divider()

        # 候補一覧
        priority_filter = st.slider("優先度フィルター (以上を表示)", 0.0, 1.0, 0.0, 0.1)
        filtered = [c for c in candidates_raw if c["priority"] >= priority_filter]
        st.markdown(f"**{len(filtered)} 件表示**")

        for c in filtered:
            prio_bar  = "🔴" if c["priority"] >= 0.7 else "🟡" if c["priority"] >= 0.4 else "🟢"
            issue_icon= {"low_success_rate":"⚠️","slow_speed":"🐢","unused":"💤","ai_suggestion":"🤖"}.get(c["issue_type"],"❓")

            with st.expander(
                f"{prio_bar} {issue_icon} [{c['priority']:.2f}] {c['title']}",
                expanded=c["priority"] >= 0.7
            ):
                st.markdown(f"**対象:** `{c['target_id']}` ({c['target_type']})")
                st.markdown(f"**問題:** {c['description']}")
                st.markdown(f"**改善案:** {c['suggestion']}")

                evidence = c.get("evidence", {})
                if evidence:
                    ev_text = " | ".join(f"{k}: {v}" for k, v in evidence.items())
                    st.caption(f"根拠: {ev_text}")

                col_q, col_i = st.columns([1, 3])
                if col_q.button("キューに追加", key=f"queue_{c['candidate_id']}"):
                    queue.enqueue(
                        title           = c["title"],
                        task_type       = c["issue_type"],
                        workflow_to_run = c["workflow_hint"],
                        target          = c["target_id"],
                        description     = c["description"] + "\n改善案: " + c["suggestion"],
                        priority        = max(1, int(c["priority"] * 10)),
                        context         = {},
                        source          = "improvement_engine",
                    )
                    col_i.success("キューに追加しました → Autonomous ページで確認")

# ═══════════════════════════════════════════════════════════════════
with tab_history:
    st.subheader("分析履歴")
    history = engine.load_history(20)
    if not history:
        st.info("分析履歴がありません。")
    else:
        for rec in reversed(history):
            with st.expander(f"[{rec['analyzed_at']}] {rec['summary']} ({rec['total_execs']} 実行)"):
                candidates_in_rec = rec.get("candidates", [])
                st.markdown(f"**期間:** {rec['period_days']} 日 | **改善候補:** {len(candidates_in_rec)} 件")
                for c in candidates_in_rec[:5]:
                    st.markdown(f"- [{c['priority']:.2f}] {c['title']}")
                if len(candidates_in_rec) > 5:
                    st.caption(f"... 他 {len(candidates_in_rec)-5} 件")
