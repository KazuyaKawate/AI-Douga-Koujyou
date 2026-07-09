from __future__ import annotations

import pandas as pd
import streamlit as st

from src.revenue_engine.dashboard import RevenueEngineDashboard


st.set_page_config(page_title="AIOS Revenue Engine", page_icon="Revenue", layout="wide")

st.markdown(
    """
    <style>
    .rev-card{background:#fff;border:1px solid #e6e9ef;border-radius:8px;padding:16px;min-height:118px;}
    .rev-number{font-size:30px;font-weight:760;color:#166534;line-height:1.1;}
    .rev-label{color:#667085;font-size:13px;}
    div.stButton > button{min-height:52px;font-weight:700;border-radius:8px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("AIOS Revenue Engine")
st.caption("収益最大化を最優先に、ROIベースで今日実行すべき収益行動を決めます。")

dashboard = RevenueEngineDashboard()
state = dashboard.load_state()

top = state.get("roi_ranking", [state.get("last_run", {}).get("top_action", {})])
top_action = top[0] if top else {}
forecast = state.get("forecasts", {})

metrics = st.columns(5)
metrics[0].markdown(f'<div class="rev-card"><div class="rev-number">{top_action.get("revenue_score", 0)}</div><div class="rev-label">Revenue Score</div></div>', unsafe_allow_html=True)
metrics[1].markdown(f'<div class="rev-card"><div class="rev-number">{forecast.get("today_profit", 0):,}</div><div class="rev-label">今日利益予測</div></div>', unsafe_allow_html=True)
metrics[2].markdown(f'<div class="rev-card"><div class="rev-number">{forecast.get("week_profit", 0):,}</div><div class="rev-label">週利益予測</div></div>', unsafe_allow_html=True)
metrics[3].markdown(f'<div class="rev-card"><div class="rev-number">{forecast.get("month_profit", 0):,}</div><div class="rev-label">月利益予測</div></div>', unsafe_allow_html=True)
metrics[4].markdown(f'<div class="rev-card"><div class="rev-number">{len(state.get("roi_ranking", []))}</div><div class="rev-label">Opportunity</div></div>', unsafe_allow_html=True)

cols = st.columns([1, 1, 2])
if cols[0].button("Revenue Cycle 実行", type="primary", use_container_width=True):
    with st.spinner("Revenue Engine running..."):
        result = dashboard.run_cycle()
    st.success(f"Top Action: {result.get('top_action', {}).get('title', '')}")
    st.rerun()

if cols[1].button("状態更新", use_container_width=True):
    st.rerun()

st.subheader("今日やるべき仕事")
plans = state.get("plans", {})
today_actions = plans.get("today", [])
if today_actions:
    for action in today_actions:
        with st.container(border=True):
            st.write(action.get("title", ""))
            st.caption(
                f"score={action.get('revenue_score', 0)} roi={action.get('roi', 0)} "
                f"profit={action.get('expected_profit', 0):,} channel={action.get('channel', '')}"
            )
            st.write(action.get("next_action", ""))
else:
    st.info("Revenue Cycleを実行すると、今日の最優先収益行動が表示されます。")

st.subheader("ROI順位 / Opportunity")
ranking = state.get("roi_ranking", [])
if ranking:
    df = pd.DataFrame(
        [
            {
                "title": item.get("title", ""),
                "score": item.get("revenue_score", 0),
                "roi": item.get("roi", 0),
                "profit": item.get("expected_profit", 0),
                "payback_days": item.get("payback_days", 0),
                "risk": item.get("risk", ""),
                "channel": item.get("channel", ""),
            }
            for item in ranking
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)
    chart_df = df[["title", "score", "profit"]].set_index("title")
    st.bar_chart(chart_df)
else:
    st.info("まだROIランキングがありません。")

st.subheader("利益予測")
forecast_df = pd.DataFrame(
    [
        {"window": "today", "profit": forecast.get("today_profit", 0)},
        {"window": "week", "profit": forecast.get("week_profit", 0)},
        {"window": "month", "profit": forecast.get("month_profit", 0)},
        {"window": "quarter", "profit": forecast.get("quarter_profit", 0)},
        {"window": "weighted", "profit": forecast.get("weighted_profit", 0)},
    ]
).set_index("window")
st.line_chart(forecast_df)

st.subheader("Agent連携")
tabs = st.tabs(["Mission Plan", "Business Feedback", "Coding Queue", "Channel Queue", "Knowledge"])
with tabs[0]:
    st.json(plans)
with tabs[1]:
    st.json(state.get("business_feedback", []))
with tabs[2]:
    st.json(state.get("coding_queue", []))
with tabs[3]:
    last_run = state.get("last_run", {})
    st.json(last_run.get("channel_queues", {}))
with tabs[4]:
    st.json(state.get("knowledge_history", [])[:10])
