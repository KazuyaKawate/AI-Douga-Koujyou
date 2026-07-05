"""Auto Agent Composer ページ。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="Auto Composer", page_icon="🎵", layout="wide")
st.title("🎵 Auto Agent Composer")
st.caption("目的を入力するだけで既存 Agent を組み合わせた Workflow を自動生成します")

from src.composer.auto_composer import AutoAgentComposer
from dashboard.utils            import init_kernel

@st.cache_resource(ttl=300)
def _kernel():
    return init_kernel()

kernel = _kernel()

# ── 使い方 ───────────────────────────────────────────────────────
with st.expander("💡 使い方"):
    st.markdown("""
**目的を日本語で入力** → AI がエージェント組み合わせを設計 → Workflow が自動登録されます。

**入力例:**
- `YouTubeを伸ばしたい` → Research + Video + Social + Analytics を自動接続
- `毎週競合他社の動向を調べてレポートにまとめたい` → Research + Writing を組み合わせ
- `新商品のSNS告知を自動化したい` → SNS Strategist + Writing + Social を連携
- `ブログ記事を書いてSEO最適化したい` → Research + Writing + SEO を組み合わせ
""")

# ── メイン入力 ────────────────────────────────────────────────────
col1, col2 = st.columns([2, 1])

with col1:
    goal = st.text_area(
        "目的・やりたいこと",
        placeholder="例: YouTubeチャンネルを成長させるために、競合調査→台本制作→SNS告知までを自動化したい",
        height=120,
    )

with col2:
    st.subheader("利用可能リソース")
    factories  = kernel.registry.list_factories()
    workflows  = kernel.registry.list_workflows()
    from src.ai_agents.registry import get_agent_registry
    agents = get_agent_registry().list_all(enabled_only=True)

    st.metric("Agent",    len(agents))
    st.metric("Workflow", len(workflows))
    st.metric("Factory",  len(factories))

# ── 素早いプリセット ─────────────────────────────────────────────
st.subheader("よく使われる目的 (クリックで入力)")
presets = [
    "YouTubeを伸ばしたい",
    "毎日のSNS投稿を自動化したい",
    "競合分析レポートを自動作成したい",
    "商品説明文を大量生成したい",
    "週次ビジネスレポートを自動生成したい",
]
cols = st.columns(len(presets))
for i, preset in enumerate(presets):
    if cols[i].button(preset, key=f"preset_{i}"):
        st.session_state["composer_goal"] = preset
        st.rerun()

if "composer_goal" in st.session_state and not goal:
    goal = st.session_state["composer_goal"]

# ── 生成実行 ─────────────────────────────────────────────────────
if st.button("🪄 Workflow を自動生成", type="primary", disabled=not goal):
    composer = AutoAgentComposer()
    with st.spinner(f"AI が設計中... 目的: {goal[:50]}"):
        result = composer.compose(goal)

    if result.success:
        st.success(f"✓ Workflow 生成完了: `{result.workflow_name}`")

        col1, col2, col3 = st.columns(3)
        col1.metric("ステップ数", result.step_count)
        col2.metric("登録状態", "✓ ホット登録済み" if result.registered else "未登録")
        col3.metric("保存先", str(result.saved_path.name) if result.saved_path else "-")

        st.markdown(f"**説明:** {result.description}")

        with st.expander("生成された Workflow JSON"):
            st.code(result.workflow_json, language="json")

        st.info(f"⚡ 「Workflow 実行」ページで `{result.workflow_name}` を実行できます。")

        # Scheduler への追加ボタン
        if st.button("📅 このワークフローをスケジュール登録する"):
            from src.job_scheduler.engine import get_job_engine, JobEngine
            from src.job_scheduler.job    import TriggerType
            engine = get_job_engine()
            job    = JobEngine.create_job(
                name         = goal[:30],
                workflow_name= result.workflow_name,
                trigger_type = TriggerType.MANUAL,
            )
            engine.add_job(job)
            st.success("Scheduler に追加しました！⏰ Scheduler ページで設定してください。")
    else:
        st.error(f"生成失敗: {result.error}")
        st.info("AI プロバイダーが利用可能か確認してください（.env の API キー）。")

# ── 保存済み Composed Workflows ───────────────────────────────────
st.divider()
st.subheader("📂 保存済みの自動生成 Workflow")

composer_tmp = AutoAgentComposer()
composed_files = composer_tmp.list_composed()

if not composed_files:
    st.info("まだ自動生成された Workflow がありません。")
else:
    import json
    for f in composed_files[:10]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            wf_name = data.get("name","")
            wf_desc = data.get("description","")
            step_n  = len(data.get("steps",[]))
            mtime   = f.stat().st_mtime
            from datetime import datetime
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**`{wf_name}`**")
                    st.caption(wf_desc[:80] if wf_desc else "")
                with col2:
                    st.write(f"{step_n} ステップ")
                    st.caption(mtime_str)
                with col3:
                    # ホット登録（カーネル再起動後）
                    if st.button("🔌 再登録", key=f"rereg_{f.stem}"):
                        from src.workflow.models import WorkflowDefinition
                        wf_def = WorkflowDefinition.from_dict(data)
                        kernel.registry.register_workflow(wf_def)
                        st.success("登録しました")
        except Exception as e:
            st.warning(f"{f.name}: 読み込みエラー {e}")
