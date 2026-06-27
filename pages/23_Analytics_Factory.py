"""
Analytics Factory — Creator Factory OS v4.7
Unified data analysis layer for all factories and projects.
No external API calls. Rule-based insights only.
"""
import sys
from datetime import datetime, date
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.factories.analytics.analytics_collector import collect_snapshot, load_settings
from src.factories.analytics.kpi_analyzer       import analyze_kpi, get_kpi_insights
from src.factories.analytics.factory_analyzer   import analyze_factories, get_factory_insights
from src.factories.analytics.project_analyzer   import analyze_projects, get_project_insights
from src.factories.analytics.roi_analyzer       import analyze_roi, get_roi_insights
from src.factories.analytics.trend_reporter     import (
    synthesize_insights, generate_analytics_report,
    export_analytics_report, save_snapshot, list_reports,
)

st.set_page_config(
    page_title="Analytics Factory | Creator Factory OS",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Analytics Factory")
st.caption("全工場・KPI・ROI・プロジェクト分析 | v4.7 — No external API")

# ── Load data ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def _load_all():
    snap     = collect_snapshot()
    kpi_a    = analyze_kpi(snap.get("kpi", {}))
    fac_a    = analyze_factories()
    proj_a   = analyze_projects()
    settings = load_settings()
    roi_a    = analyze_roi(
        snap.get("accounting_revenue",      {}),
        snap.get("accounting_expenses",     {}),
        snap.get("accounting_subscriptions",{}),
        snap.get("sales_deals",             {}),
    )
    kpi_ins  = get_kpi_insights(kpi_a)
    fac_ins  = get_factory_insights(fac_a)
    proj_ins = get_project_insights(proj_a)
    roi_ins  = get_roi_insights(roi_a, float(settings.get("roi_target_pct", 20)))
    all_ins  = synthesize_insights(kpi_ins, fac_ins, proj_ins, roi_ins)
    return snap, kpi_a, fac_a, proj_a, roi_a, all_ins, kpi_ins, fac_ins, proj_ins, roi_ins

snap, kpi_a, fac_a, proj_a, roi_a, all_ins, kpi_ins, fac_ins, proj_ins, roi_ins = _load_all()

# Top-level summary bar
h1, h2, h3, h4, h5, h6, h7, h8 = st.columns(8)
h1.metric("🏭 工場数",      fac_a["total"])
h2.metric("✅ 正常工場",    fac_a["healthy"])
h3.metric("📊 KPI達成率",   f"{kpi_a['avg_pct']}%")
h4.metric("📁 プロジェクト", proj_a["total"])
h5.metric("💰 今月売上",     f"¥{roi_a['total_revenue']:,}")
h6.metric("💹 今月利益",     f"¥{roi_a['net_profit']:,}")
h7.metric("📈 ROI",          f"{roi_a['roi']}%")
h8.metric("💡 インサイト",   len(all_ins))

st.divider()

errors   = sum(1 for i in all_ins if i.startswith("🔴"))
warnings = sum(1 for i in all_ins if i.startswith("⚠️"))
if errors > 0:
    st.error(f"🔴 {errors} 件のエラーがあります。インサイトを確認してください。")
elif warnings > 0:
    st.warning(f"⚠️ {warnings} 件の警告があります。")
else:
    st.success("✅ システム正常 — 重大な問題はありません")

# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "ダッシュボード", "KPI分析", "工場分析", "プロジェクト分析", "ROI分析", "レポート"
])

# ── Tab 1: Dashboard ──────────────────────────────────────────────────────────

with tab1:
    st.subheader("📊 システムダッシュボード")
    col_a, col_b = st.columns([3, 2])

    with col_a:
        st.markdown("**💡 インサイト一覧**")
        if all_ins:
            for ins in all_ins:
                if ins.startswith("🔴"):
                    st.error(ins)
                elif ins.startswith("⚠️"):
                    st.warning(ins)
                elif ins.startswith("✅"):
                    st.success(ins)
                else:
                    st.info(ins)
        else:
            st.caption("インサイトはありません")

    with col_b:
        st.markdown("**🏭 工場健全性**")
        health_pct = fac_a["health_pct"]
        st.progress(health_pct / 100, text=f"工場健全性: {health_pct}%")
        st.markdown("**📊 KPI達成率**")
        st.progress(kpi_a["avg_pct"] / 100, text=f"KPI平均達成率: {kpi_a['avg_pct']}%")
        st.markdown("**📁 プロジェクト進捗**")
        st.progress(proj_a["avg_progress"] / 100, text=f"平均進捗: {proj_a['avg_progress']}%")

    st.divider()
    st.markdown("**📦 コンテンツサマリー**")
    video_data = snap.get("video", {})
    note_arts  = snap.get("note", {}).get("articles", [])
    sns_posts  = snap.get("sns",  {}).get("posts",    [])

    cs1, cs2, cs3, cs4, cs5 = st.columns(5)
    cs1.metric("🎬 動画エピソード",  video_data.get("total",        0))
    cs2.metric("🎬 書き出し済み",    video_data.get("exported",     0))
    cs3.metric("📝 note記事",        len(note_arts))
    cs4.metric("✅ note公開済",
               sum(1 for a in note_arts if a.get("status") == "published"))
    cs5.metric("📱 SNS投稿",         len(sns_posts))

    st.divider()
    if st.button("🔄 データ更新", use_container_width=True, key="refresh_dash"):
        try:
            save_snapshot(snap)
            st.cache_data.clear()
            st.success("✅ スナップショットを保存しました")
            st.rerun()
        except Exception as e:
            st.error(f"エラー: {e}")

# ── Tab 2: KPI Analysis ───────────────────────────────────────────────────────

with tab2:
    st.subheader("📊 KPI分析")
    if kpi_a["rows"]:
        st.caption(f"集計日: {kpi_a['date'] or date.today().isoformat()}")
        ka1, ka2, ka3 = st.columns(3)
        ka1.metric("📋 KPI項目数",   kpi_a["total"])
        ka2.metric("✅ 達成済み",     kpi_a["achieved"])
        ka3.metric("📊 平均達成率",   f"{kpi_a['avg_pct']}%")
        st.progress(kpi_a["avg_pct"] / 100, text=f"KPI平均: {kpi_a['avg_pct']}%")
        st.divider()
        st.markdown("**KPI 目標 vs 実績**")
        kcols = st.columns(min(len(kpi_a["rows"]), 4))
        for i, r in enumerate(kpi_a["rows"]):
            unit = r["unit"]
            pct  = r["pct"]
            col  = kcols[i % 4]
            delta_str = f"{pct}%"
            delta_color = "normal" if pct >= 100 else "inverse"
            col.metric(
                label=r["label"],
                value=f"{r['actual']:,}{unit}",
                delta=f"目標 {pct}%",
                delta_color=delta_color,
                help=f"目標: {r['target']:,}{unit}",
            )
        st.divider()
        st.markdown("**達成率バー**")
        for r in kpi_a["rows"]:
            pct = min(r["pct"], 100)
            label = f"{r['label']}: {r['actual']:,} / {r['target']:,} ({r['pct']}%)"
            st.progress(pct / 100, text=label)
    else:
        st.info("KPIデータがありません。Mission ControlでKPI目標を設定してください。")
        st.page_link("pages/17_Mission_Control.py", label="🎯 Mission Controlを開く")

    st.divider()
    st.markdown("**💡 KPIインサイト**")
    for ins in kpi_ins:
        st.caption(ins)

# ── Tab 3: Factory Analysis ───────────────────────────────────────────────────

with tab3:
    st.subheader("🏭 工場分析")
    fa1, fa2, fa3, fa4 = st.columns(4)
    fa1.metric("🏭 工場数",     fac_a["total"])
    fa2.metric("✅ 正常",       fac_a["healthy"])
    fa3.metric("🔔 合計警告",   fac_a["total_warnings"])
    fa4.metric("⚡ 稼働アイテム", fac_a["total_active"])
    st.progress(fac_a["health_pct"] / 100, text=f"工場健全性: {fac_a['health_pct']}%")
    st.divider()
    fac_cols = st.columns(3)
    for i, f in enumerate(fac_a["factories"]):
        with fac_cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**{f['health_icon']} {f['name']}**  {f['status_icon']}")
                fc1, fc2 = st.columns(2)
                fc1.metric("稼働中", f["active_items"])
                fc2.metric("完了(今日)", f["completed_today"])
                if f["warning_count"] > 0:
                    st.warning(f"⚠️ {f['warning_count']} 件の警告")
                st.caption(f"📌 {f['next_action']}")
    st.divider()
    st.markdown("**💡 工場インサイト**")
    for ins in fac_ins:
        st.caption(ins)

# ── Tab 4: Project Analysis ───────────────────────────────────────────────────

with tab4:
    st.subheader("📁 プロジェクト分析")
    pa1, pa2, pa3, pa4 = st.columns(4)
    pa1.metric("📁 プロジェクト数",   proj_a["total"])
    pa2.metric("🟢 稼働中",           proj_a["active"])
    pa3.metric("📈 平均進捗",          f"{proj_a['avg_progress']}%")
    pa4.metric("💰 合計売上",          f"¥{proj_a['total_revenue']:,}")
    st.divider()
    if proj_a["summaries"]:
        pcols = st.columns(min(len(proj_a["summaries"]), 3))
        for i, p in enumerate(proj_a["summaries"]):
            with pcols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**{p['status_icon']} {p['name']}**")
                    st.caption(f"👤 {p['owner']}  |  優先度: {p['priority']}")
                    st.progress(
                        min(p["progress"] / 100, 1.0),
                        text=f"進捗: {p['progress']:.0f}%",
                    )
                    st.caption(f"工場数: {p['factory_count']}  |  売上: ¥{p['revenue']:,}")
                    if p.get("description"):
                        st.caption(p["description"])
    else:
        st.info("プロジェクトがありません。")
        st.page_link("pages/17_Mission_Control.py", label="🎯 Mission Controlを開く")

    if proj_a["factory_usage"]:
        st.divider()
        st.markdown("**🏭 工場使用分布**")
        for factory_name, count in sorted(
            proj_a["factory_usage"].items(), key=lambda x: -x[1]
        ):
            st.progress(
                count / max(proj_a["factory_usage"].values()),
                text=f"{factory_name}: {count} プロジェクト",
            )
    st.divider()
    st.markdown("**💡 プロジェクトインサイト**")
    for ins in proj_ins:
        st.caption(ins)

# ── Tab 5: ROI Analysis ───────────────────────────────────────────────────────

with tab5:
    st.subheader(f"💹 ROI分析 — {roi_a['year_month']}")
    ra1, ra2, ra3, ra4, ra5 = st.columns(5)
    ra1.metric("📈 今月売上",  f"¥{roi_a['total_revenue']:,}")
    ra2.metric("📉 今月経費",  f"¥{roi_a['month_expense']:,}")
    ra3.metric("🔄 サブスク",  f"¥{roi_a['sub_cost']:,}/月",
               help=f"{roi_a['active_subs']}サービス")
    ra4.metric("💹 今月利益",  f"¥{roi_a['net_profit']:,}",
               delta=("黒字" if roi_a["is_profitable"] else "赤字"),
               delta_color=("normal" if roi_a["is_profitable"] else "inverse"))
    ra5.metric("📊 ROI",       f"{roi_a['roi']}%")
    st.divider()
    if roi_a["revenue_by_source"]:
        st.markdown("**📈 収入源別売上**")
        total_r = roi_a["total_revenue"] or 1
        for src, amt in sorted(roi_a["revenue_by_source"].items(), key=lambda x: -x[1]):
            pct = round(amt / total_r * 100)
            st.progress(amt / total_r, text=f"{src}: ¥{amt:,} ({pct}%)")
    if roi_a["expense_by_category"]:
        st.divider()
        st.markdown("**📉 経費カテゴリ別**")
        total_e = roi_a["total_expense"] or 1
        for cat, amt in sorted(roi_a["expense_by_category"].items(), key=lambda x: -x[1]):
            pct = round(amt / total_e * 100)
            st.progress(amt / total_e, text=f"{cat}: ¥{amt:,} ({pct}%)")
    if roi_a["total_revenue"] == 0:
        st.info("今月の収支データがありません。会計監査工場でデータを入力してください。")
        st.page_link("pages/22_Accounting_Factory.py", label="💰 会計監査工場を開く")
    st.divider()
    st.markdown("**💡 ROIインサイト**")
    for ins in roi_ins:
        st.caption(ins)

# ── Tab 6: Reports ────────────────────────────────────────────────────────────

with tab6:
    st.subheader("📝 Analytics Report")
    rc1, rc2 = st.columns([2, 1])
    with rc1:
        report_date = st.date_input("レポート日付", value=date.today(), key="report_date")
    with rc2:
        st.write("")
        generate_btn = st.button("📊 レポート生成", type="primary",
                                 use_container_width=True, key="gen_report")

    if generate_btn:
        with st.spinner("レポート生成中..."):
            content = generate_analytics_report(
                snap, kpi_a, fac_a, proj_a, roi_a, all_ins
            )
            st.session_state["analytics_report"] = content
            st.session_state["analytics_report_date"] = report_date.isoformat()
        st.success("✅ レポートを生成しました")

    report_content = st.session_state.get("analytics_report", "")
    if report_content:
        with st.expander("📄 レポートプレビュー", expanded=False):
            st.markdown(report_content)
        expcol1, expcol2 = st.columns(2)
        with expcol1:
            if st.button("💾 ファイルに保存", use_container_width=True, key="export_report"):
                try:
                    date_str = st.session_state.get("analytics_report_date",
                                                     date.today().isoformat())
                    out_path = export_analytics_report(report_content, date_str)
                    st.success(f"✅ 保存完了: `reports/analytics/{out_path.name}`")
                    save_snapshot(snap)
                except Exception as exc:
                    st.error(f"エラー: {exc}")
        with expcol2:
            st.download_button(
                label="⬇️ Markdownをダウンロード",
                data=report_content.encode("utf-8"),
                file_name=f"{date.today().isoformat()}_analytics_report.md",
                mime="text/markdown",
                use_container_width=True,
                key="dl_report",
            )

    st.divider()
    st.markdown("**📂 既存レポート**")
    existing = list_reports()
    if existing:
        for rpt in existing[:10]:
            st.caption(f"📄 {rpt.name}  ({rpt.stat().st_size // 1024 + 1} KB)")
    else:
        st.caption("レポートはまだありません。上のボタンで生成・保存してください。")
