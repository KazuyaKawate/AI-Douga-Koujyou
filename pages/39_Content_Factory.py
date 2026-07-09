from __future__ import annotations

import pandas as pd
import streamlit as st

from src.content_factory.content_manager import ContentFactoryManager


st.set_page_config(page_title="AIOS Content Factory", page_icon="Content", layout="wide")

st.markdown(
    """
    <style>
    .cf-card{background:#fff;border:1px solid #e6e9ef;border-radius:8px;padding:16px;min-height:118px;}
    .cf-number{font-size:30px;font-weight:760;color:#0f766e;line-height:1.1;}
    .cf-label{color:#667085;font-size:13px;}
    div.stButton > button{min-height:52px;font-weight:700;border-radius:8px;}
    textarea{font-size:16px!important;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("AIOS Content Factory")
st.caption("初収益に向けて、note・Threads・占い・LP・SEO・A/Bテストをまとめて生成します。")

manager = ContentFactoryManager()
state = manager.load_state()
analytics = state.get("analytics", {})
contents = state.get("contents", [])
schedule = state.get("schedule", [])
last_run = state.get("last_run", {})
ideas = state.get("content_ideas", [])
content_queue = state.get("content_queue", [])
drafts = state.get("drafts", [])
history = state.get("history", [])

metrics = st.columns(5)
metrics[0].markdown(f'<div class="cf-card"><div class="cf-number">{len([c for c in contents if c.get("type") == "note"])}</div><div class="cf-label">今日生成した記事</div></div>', unsafe_allow_html=True)
metrics[1].markdown(f'<div class="cf-card"><div class="cf-number">{len([s for s in schedule if s.get("status") == "scheduled"])}</div><div class="cf-label">今日投稿予定</div></div>', unsafe_allow_html=True)
metrics[2].markdown(f'<div class="cf-card"><div class="cf-number">{analytics.get("revenue", 0):,}</div><div class="cf-label">収益予測</div></div>', unsafe_allow_html=True)
metrics[3].markdown(f'<div class="cf-card"><div class="cf-number">{analytics.get("pv", 0):,}</div><div class="cf-label">PV</div></div>', unsafe_allow_html=True)
metrics[4].markdown(f'<div class="cf-card"><div class="cf-number">{analytics.get("roi", 0)}</div><div class="cf-label">ROI</div></div>', unsafe_allow_html=True)

st.subheader("Content Engine Phase1")
st.caption("毎日収益化コンテンツを自動生成するためのLocal-first管理。Business Engine KPIに応じて優先度を調整します。")
phase_cols = st.columns(5)
phase_cols[0].metric("DryRun", "ON" if state.get("dry_run", True) else "OFF")
phase_cols[1].metric("Local First", "ON" if state.get("local_first", True) else "OFF")
phase_cols[2].metric("記事ネタ", len(ideas))
phase_cols[3].metric("コンテンツキュー", len(content_queue))
phase_cols[4].metric("下書き", len(drafts))

phase_topic = st.text_input("Phase1 テーマ", value="AIOS毎日収益化コンテンツ運用", key="ce_phase1_topic")
phase_category = st.selectbox("カテゴリ", ["revenue", "note", "threads", "official_site", "affiliate", "seo"], key="ce_phase1_category")
phase_target = st.text_input("対象読者", value="AIOS users", key="ce_phase1_target")
phase_actions = st.columns([1, 1, 2])
if phase_actions[0].button("Phase1 自動生成", type="primary", use_container_width=True):
    result = manager.generate_phase1_content(topic=phase_topic, category=phase_category, target=phase_target)
    st.success(f"Generated {len(result.get('contents', []))} draft contents in DryRun.")
    st.rerun()
if phase_actions[1].button("記事ネタだけ追加", use_container_width=True):
    manager.add_content_idea(phase_topic, category=phase_category, source="manual_ui", priority="normal")
    st.success("記事ネタを追加しました。")
    st.rerun()

phase_tabs = st.tabs(["記事ネタ管理", "コンテンツキュー", "カテゴリ管理", "履歴管理", "下書き保存"])
with phase_tabs[0]:
    if ideas:
        st.dataframe(pd.DataFrame(ideas[:50]), use_container_width=True, hide_index=True)
    else:
        st.info("記事ネタはまだありません。")
with phase_tabs[1]:
    if content_queue:
        st.dataframe(pd.DataFrame(content_queue[:50]), use_container_width=True, hide_index=True)
    else:
        st.info("コンテンツキューはまだありません。")
with phase_tabs[2]:
    st.dataframe(pd.DataFrame(state.get("categories", [])), use_container_width=True, hide_index=True)
with phase_tabs[3]:
    if history:
        st.dataframe(pd.DataFrame(history[:50]), use_container_width=True, hide_index=True)
    else:
        st.info("履歴はまだありません。")
with phase_tabs[4]:
    if drafts:
        st.dataframe(pd.DataFrame(drafts[:50]), use_container_width=True, hide_index=True)
    else:
        st.info("下書きはまだ保存されていません。")

st.subheader("Daily Pack Generator")
topic = st.text_input("生成テーマ", value="Threads占いで初収益")
youtube_url = st.text_input("YouTube URL", value="")
transcript = st.text_area("字幕 / 要約素材", height=100, placeholder="動画内容の字幕やメモを入力。転載ではなく、要約・独自分析・独自構成へ変換します。")
cols = st.columns([1, 1, 2])
if cols[0].button("収益コンテンツ生成", type="primary", use_container_width=True):
    with st.spinner("Generating revenue content pack..."):
        result = manager.generate_daily_pack(topic=topic, youtube_url=youtube_url, transcript=transcript)
    st.success(f"Generated {len(result.get('contents', []))} contents")
    st.rerun()
if cols[1].button("状態更新", use_container_width=True):
    st.rerun()

st.subheader("次に作るべきコンテンツ")
next_content = last_run.get("next_content", {})
if next_content:
    with st.container(border=True):
        st.write(next_content.get("topic", ""))
        st.caption(f"type={next_content.get('type', '')} reason={next_content.get('reason', '')}")
else:
    st.info("Daily Packを生成すると次の改善候補が表示されます。")

st.subheader("生成コンテンツ")
if contents:
    rows = [
        {
            "type": item.get("type", ""),
            "title": item.get("title") or item.get("topic") or item.get("offer") or item.get("product") or item.get("content_id"),
            "status": item.get("status", "draft"),
            "revenue": item.get("estimated_revenue", 0),
        }
        for item in contents[:30]
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
else:
    st.info("まだ生成コンテンツがありません。")

st.subheader("投稿予定")
if schedule:
    st.dataframe(pd.DataFrame(schedule[:30]), use_container_width=True, hide_index=True)
else:
    st.info("投稿予約はまだありません。")

st.subheader("Analytics / 改善候補")
chart = pd.DataFrame(
    [
        {"metric": "PV", "value": analytics.get("pv", 0)},
        {"metric": "CTR x1000", "value": int(float(analytics.get("ctr", 0)) * 1000)},
        {"metric": "CVR x1000", "value": int(float(analytics.get("cvr", 0)) * 1000)},
        {"metric": "Revenue", "value": analytics.get("revenue", 0)},
        {"metric": "ROI", "value": analytics.get("roi", 0)},
    ]
).set_index("metric")
st.bar_chart(chart)
for idea in analytics.get("improvement_candidates", []):
    st.write(f"- {idea}")

st.subheader("連携 / 品質 / A/B")
tabs = st.tabs(["Business", "Revenue", "Coding", "Quality", "A/B", "Knowledge", "SEO", "Images"])
with tabs[0]:
    st.json(state.get("business_feedback", {}))
with tabs[1]:
    st.json(state.get("revenue_feedback", {}))
with tabs[2]:
    st.json(state.get("coding_feedback", {}))
with tabs[3]:
    st.json(state.get("quality_reviews", [])[:20])
with tabs[4]:
    st.json(state.get("ab_tests", [])[:20])
with tabs[5]:
    st.json(state.get("knowledge_history", [])[:20])
with tabs[6]:
    st.json(last_run.get("seo", {}))
with tabs[7]:
    st.json(last_run.get("image_prompts", {}))
