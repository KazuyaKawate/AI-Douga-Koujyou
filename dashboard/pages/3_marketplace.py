"""Marketplace ページ。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="Marketplace", page_icon="🛒", layout="wide")
st.title("🛒 Agent Marketplace")
st.caption("Agent パッケージの検索・インストール・管理")

from src.agent_store import MarketplaceProvider, get_store_registry
from dashboard.utils import init_kernel

@st.cache_resource(ttl=300)
def _kernel():
    return init_kernel()

_kernel()

mp    = MarketplaceProvider(use_mock=True)
store = get_store_registry()

# ── サイドバー: 検索・フィルタ ───────────────────────────────────
st.sidebar.subheader("検索・フィルタ")
query     = st.sidebar.text_input("キーワード検索", placeholder="writing, sns, ...")
categories = ["すべて"] + mp.get_categories()
category  = st.sidebar.selectbox("カテゴリ", categories)
free_only = st.sidebar.checkbox("無料のみ")

# ── タブ ─────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🔍 カタログ", "📦 インストール済み", "📤 エクスポート"])

# ── Tab1: カタログ ────────────────────────────────────────────────
with tab1:
    cat_filter = None if category == "すべて" else category
    items = mp.search(query=query, category=cat_filter, free_only=free_only)

    if not items:
        st.info("条件に一致するパッケージがありません。")
    else:
        st.caption(f"{len(items)} 件のパッケージ")
        cols = st.columns(3)
        for i, item in enumerate(items):
            with cols[i % 3]:
                installed_pkg = store.get_installed(item.package_id)
                is_installed  = installed_pkg is not None

                price_badge = "🆓 無料" if item.price == "free" else f"💰 {item.price}"
                with st.container(border=True):
                    st.markdown(f"**{item.name}** v{item.version}")
                    st.caption(f"👤 {item.author}  |  {price_badge}  |  ⭐ {item.rating}")
                    st.write(item.description[:80] + "...")
                    tags_str = " ".join(f"`{t}`" for t in item.tags[:4])
                    st.markdown(tags_str)
                    st.caption(f"📥 {item.downloads:,} DL  |  📁 {item.category}")

                    if is_installed:
                        st.success(f"✓ インストール済み v{installed_pkg.current_version}")
                        if st.button("アンインストール", key=f"uninstall_{item.package_id}", type="secondary"):
                            store.uninstall(item.package_id)
                            st.rerun()
                    else:
                        if st.button("インストール", key=f"install_{item.package_id}", type="primary"):
                            pkg_path = mp.download(item.package_id)
                            if pkg_path:
                                result = store.install(pkg_path)
                                if result.success:
                                    st.success(f"インストール完了: {result}")
                                    st.rerun()
                                else:
                                    st.error(f"インストール失敗: {result.error}")
                            else:
                                st.warning(
                                    "パッケージをダウンロードできません。\n"
                                    "先に Export タブから Agent をエクスポートしてください。"
                                )

# ── Tab2: インストール済み ────────────────────────────────────────
with tab2:
    installed = store.list_installed()
    if not installed:
        st.info("インストール済みパッケージがありません。")
    else:
        import pandas as pd
        df = pd.DataFrame([{
            "パッケージ":      p.package_id,
            "名前":            p.name,
            "バージョン":      p.current_version,
            "Agent":           p.agent_id,
            "インストール日": p.installed_at,
            "更新日":          p.updated_at,
            "状態":            "✓" if p.enabled else "停止中",
        } for p in installed])
        st.dataframe(df, use_container_width=True, hide_index=True)

        # ロールバック
        st.subheader("バージョン管理")
        pkg_ids = [p.package_id for p in installed]
        sel_pkg = st.selectbox("パッケージを選択", pkg_ids)
        if sel_pkg:
            versions = store.get_versions(sel_pkg)
            cur_pkg  = store.get_installed(sel_pkg)
            st.write(f"現在のバージョン: **v{cur_pkg.current_version}**")
            if versions:
                target_ver = st.selectbox("ロールバック先のバージョン", versions)
                if st.button("ロールバック実行", type="secondary"):
                    rb = store.rollback(sel_pkg, target_ver)
                    if rb.success:
                        st.success(f"ロールバック完了: {rb}")
                        st.rerun()
                    else:
                        st.error(f"ロールバック失敗: {rb.error}")
            else:
                st.info("バックアップバージョンがありません。")

# ── Tab3: エクスポート ────────────────────────────────────────────
with tab3:
    st.subheader("Agent を .apagent でエクスポート")

    from src.ai_agents.registry import get_agent_registry
    from src.agent_store import AgentExporter

    agents = get_agent_registry().list_all(enabled_only=True)
    agent_options = {f"{a.agent_id} ({a.name})": a.agent_id for a in agents}

    with st.form("export_form"):
        sel_agent = st.selectbox("エクスポートする Agent", list(agent_options.keys()))
        author    = st.text_input("作者名", value="AIOS User")
        template  = st.text_area(
            "プロンプトテンプレート (任意)",
            placeholder="テンプレートを入力... {topic} {tone} などの変数が使えます",
            height=80,
        )
        export_btn = st.form_submit_button("📤 エクスポート", type="primary")

    if export_btn and sel_agent:
        agent_id = agent_options[sel_agent]
        with st.spinner("エクスポート中..."):
            result = AgentExporter().export(
                agent_id     = agent_id,
                author       = author,
                template_text= template or None,
                output_dir   = Path("output/store"),
            )
        if result.success:
            pkg_bytes = result.package_path.read_bytes()
            st.success(f"エクスポート完了: {result.package_path.name}")
            st.download_button(
                "📥 .apagent をダウンロード",
                data      = pkg_bytes,
                file_name = result.package_path.name,
                mime      = "application/zip",
            )
        else:
            st.error(f"エクスポート失敗: {result.error}")

    # エクスポート済みファイル一覧
    st.subheader("エクスポート済みパッケージ")
    out_dir = Path("output/store")
    if out_dir.exists():
        pkgs = sorted(out_dir.glob("*.apagent"), key=lambda p: p.stat().st_mtime, reverse=True)
        for pkg in pkgs:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"📦 {pkg.name}")
            with col2:
                pkg_bytes = pkg.read_bytes()
                st.download_button(
                    "DL",
                    data=pkg_bytes,
                    file_name=pkg.name,
                    mime="application/zip",
                    key=f"dl_{pkg.stem}",
                )
    else:
        st.info("エクスポート済みパッケージがありません。")
