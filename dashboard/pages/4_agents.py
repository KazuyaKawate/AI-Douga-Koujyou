"""Agent 管理ページ。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import streamlit as st

st.set_page_config(page_title="Agent 管理", page_icon="🤖", layout="wide")
st.title("🤖 Agent 管理")
st.caption("Agent の一覧・追加・有効化/無効化・インポート")

from src.ai_agents.registry   import get_agent_registry
from src.ai_agents.definition import AgentDefinition, AgentConfig
from src.agent_store          import AgentImporter
from dashboard.utils          import init_kernel

@st.cache_resource(ttl=300)
def _kernel():
    return init_kernel()

_kernel()
reg = get_agent_registry()

tab1, tab2, tab3, tab4 = st.tabs(["📋 一覧", "➕ 新規追加", "📥 インポート (.apagent)", "🔧 詳細編集"])

# ── Tab1: 一覧 ───────────────────────────────────────────────────
with tab1:
    agents = reg.list_all()

    col1, col2, col3 = st.columns(3)
    col1.metric("登録済み Agent", len(agents))
    col2.metric("有効", sum(1 for a in agents if a.enabled))
    col3.metric("無効", sum(1 for a in agents if not a.enabled))

    # フィルタ
    roles     = sorted({a.role for a in agents})
    factories = sorted({a.factory_id or "-" for a in agents})
    sel_role    = st.selectbox("役割フィルタ", ["すべて"] + roles)
    sel_factory = st.selectbox("Factory フィルタ", ["すべて"] + factories)

    filtered = agents
    if sel_role != "すべて":
        filtered = [a for a in filtered if a.role == sel_role]
    if sel_factory != "すべて":
        filtered = [a for a in filtered if (a.factory_id or "-") == sel_factory]

    import pandas as pd
    df = pd.DataFrame([{
        "ID":          a.agent_id,
        "名前":        a.name,
        "Ver":         a.version,
        "役割":        a.role,
        "タスク":      a.task_type,
        "Factory":     a.factory_id or "-",
        "有効":        "✓" if a.enabled else "✗",
        "タグ":        ", ".join(a.tags[:3]),
    } for a in filtered])
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 有効化/無効化
    st.subheader("有効化 / 無効化")
    agent_ids  = [a.agent_id for a in filtered]
    sel_agent  = st.selectbox("Agent を選択", agent_ids, key="toggle_agent")
    if sel_agent:
        cur_agent = reg.get(sel_agent)
        if cur_agent:
            if cur_agent.enabled:
                if st.button("🔴 無効化", key="disable_btn"):
                    reg.disable(sel_agent)
                    st.success(f"{sel_agent} を無効化しました")
                    st.rerun()
            else:
                if st.button("🟢 有効化", key="enable_btn", type="primary"):
                    reg.enable(sel_agent)
                    st.success(f"{sel_agent} を有効化しました")
                    st.rerun()

# ── Tab2: 新規追加 ───────────────────────────────────────────────
with tab2:
    st.subheader("新しい Agent を作成")
    with st.form("new_agent_form"):
        col1, col2 = st.columns(2)
        with col1:
            agent_id   = st.text_input("Agent ID *", placeholder="my_custom_agent")
            name       = st.text_input("名前 *", placeholder="My Custom Agent")
            version    = st.text_input("バージョン", value="1.0.0")
            role       = st.selectbox("役割", ["writer","analyst","planner","reviewer","general"])
        with col2:
            task_type  = st.selectbox("タスクタイプ", ["writing","analysis","general","creative"])
            provider   = st.selectbox("優先プロバイダー", ["自動(None)","claude","openai","gemini","virtual"])
            max_tokens = st.number_input("最大トークン", value=2048, min_value=256, max_value=8192, step=256)
            temperature= st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)

        description  = st.text_area("説明 *", placeholder="この Agent が何をするかを説明してください", height=80)
        system_prompt= st.text_area("System Prompt *", placeholder="あなたは...専門家です。", height=150)
        tags_str     = st.text_input("タグ (カンマ区切り)", placeholder="writing, japanese, seo")
        factory_id   = st.text_input("Factory ID (任意)", placeholder="my_factory")

        submit = st.form_submit_button("✅ Agent を作成", type="primary")

    if submit:
        if not agent_id or not name or not system_prompt:
            st.error("Agent ID, 名前, System Prompt は必須です。")
        elif reg.exists(agent_id):
            st.error(f"Agent ID '{agent_id}' は既に存在します。")
        else:
            new_agent = AgentDefinition(
                agent_id     = agent_id.strip(),
                name         = name.strip(),
                version      = version.strip(),
                description  = description.strip(),
                role         = role,
                capabilities = [task_type],
                task_type    = task_type,
                system_prompt= system_prompt.strip(),
                config       = AgentConfig(
                    provider_hint = None if provider == "自動(None)" else provider,
                    max_tokens    = int(max_tokens),
                    temperature   = float(temperature),
                ),
                tags         = [t.strip() for t in tags_str.split(",") if t.strip()],
                factory_id   = factory_id.strip() or None,
            )
            reg.register(new_agent)
            reg.save(new_agent)
            st.success(f"✓ Agent '{agent_id}' を作成しました！")
            st.rerun()

# ── Tab3: インポート ─────────────────────────────────────────────
with tab3:
    st.subheader(".apagent ファイルをインポート")
    uploaded = st.file_uploader(
        ".apagent ファイルをアップロード",
        type=["apagent", "zip"],
        help=".apagent は ZIP 形式です。",
    )
    overwrite = st.checkbox("既存 Agent を上書き", value=True)

    if uploaded and st.button("📥 インポート実行", type="primary"):
        import tempfile
        tmp_path = Path(tempfile.mktemp(suffix=".apagent"))
        tmp_path.write_bytes(uploaded.read())
        try:
            result = AgentImporter().import_package(tmp_path, overwrite=overwrite)
            if result.success:
                st.success(f"✓ インポート完了: {result}")
                if result.warnings:
                    st.warning("\n".join(result.warnings))
            else:
                st.error(f"インポート失敗: {result.error}")
        finally:
            tmp_path.unlink(missing_ok=True)

# ── Tab4: 詳細編集 ───────────────────────────────────────────────
with tab4:
    st.subheader("Agent の詳細を編集")
    all_agents = reg.list_all()
    sel = st.selectbox("編集する Agent", [a.agent_id for a in all_agents], key="edit_sel")

    if sel:
        agent = reg.get(sel)
        if agent:
            with st.form("edit_agent_form"):
                new_name   = st.text_input("名前", value=agent.name)
                new_desc   = st.text_area("説明", value=agent.description, height=80)
                new_prompt = st.text_area("System Prompt", value=agent.system_prompt, height=200)
                new_temp   = st.slider("Temperature", 0.0, 1.0, float(agent.config.temperature), 0.1)
                new_tokens = st.number_input("最大トークン", value=agent.config.max_tokens, min_value=256, max_value=8192, step=256)

                save_btn = st.form_submit_button("💾 保存", type="primary")

            if save_btn:
                changes = {
                    "name":          new_name,
                    "description":   new_desc,
                    "system_prompt": new_prompt,
                    "config": {
                        "temperature": new_temp,
                        "max_tokens":  int(new_tokens),
                    },
                }
                try:
                    reg.update_version(sel, changes, version_level="patch")
                    st.success(f"✓ 保存しました（バージョン自動更新）")
                    st.rerun()
                except Exception as e:
                    st.error(f"保存エラー: {e}")

            with st.expander("JSON 表示"):
                st.code(agent.to_json(), language="json")
