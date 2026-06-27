"""
AI CEO Core — Creator Factory OS v5.0-beta
Executive decision layer. Read-only analysis. Strategic recommendations only.
NOT a Factory. NOT a chatbot. No external APIs. No automatic execution.
"""
import json
import sys
from datetime import date
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

APP_VERSION = "5.0-beta"
TODAY = date.today().isoformat()

st.set_page_config(
    page_title="AI CEO | Creator Factory OS",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 AI CEO Core")
st.caption(
    f"Creator Factory OS v{APP_VERSION} — Executive Decision Layer  |  "
    "Read-only analysis · Strategic recommendations only · No external APIs"
)
st.divider()

# ── Snapshot (cached per session refresh) ─────────────────────────────────────

@st.cache_data(ttl=60, show_spinner=False)
def _load_snapshot() -> dict:
    from src.aiceo.executive_engine import collect_snapshot
    return collect_snapshot()


@st.cache_data(ttl=60, show_spinner=False)
def _run_all_engines(snap_ts: str) -> dict:
    from src.aiceo.priority_engine       import score_priorities
    from src.aiceo.risk_engine           import identify_risks
    from src.aiceo.opportunity_engine    import identify_opportunities
    from src.aiceo.recommendation_engine import generate_recommendations
    from src.aiceo.kpi_engine            import analyze_kpi
    from src.aiceo.executive_dashboard   import compute_overall_health, generate_ceo_brief

    snap  = _load_snapshot()
    pris  = score_priorities(snap)
    risks = identify_risks(snap)
    opps  = identify_opportunities(snap)
    kpi_a = analyze_kpi(snap)
    recs  = generate_recommendations(snap, risks, opps, pris)
    health = compute_overall_health(snap, risks)
    brief  = generate_ceo_brief(snap, health, risks, opps, recs)
    return {
        "snap": snap, "priorities": pris, "risks": risks,
        "opportunities": opps, "kpi_analysis": kpi_a,
        "recommendations": recs, "health": health, "brief": brief,
    }


col_refresh, col_info = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Refresh Analysis", type="primary", key="ceo_refresh"):
        st.cache_data.clear()
        st.rerun()
with col_info:
    st.caption("Analysis runs on demand. Click Refresh to update from current OS data.")

with st.spinner("Collecting OS snapshot…"):
    try:
        snap = _load_snapshot()
        data = _run_all_engines(snap.get("collected_at", ""))
    except Exception as exc:
        st.error(f"Analysis error: {exc}")
        st.stop()

snap          = data["snap"]
priorities    = data["priorities"]
risks         = data["risks"]
opportunities = data["opportunities"]
kpi_analysis  = data["kpi_analysis"]
recommendations = data["recommendations"]
health        = data["health"]
brief         = data["brief"]

# ── Tabs ──────────────────────────────────────────────────────────────────────

tabs = st.tabs([
    "🎯 CEO Daily Brief",
    "📊 KPI Summary",
    "⚡ Priorities",
    "💡 Opportunities",
    "⚠️ Risks",
    "📋 Recommendations",
    "📄 Executive Report",
])

# ── Tab 1: CEO Daily Brief ─────────────────────────────────────────────────────
with tabs[0]:
    st.subheader("🎯 CEO Daily Brief")

    # Overall health banner
    h_score = health["score"]
    h_label = health["label"]
    h_icon  = health["icon"]

    hc1, hc2, hc3, hc4, hc5 = st.columns(5)
    hc1.metric("🧠 OS Health", f"{h_icon} {h_label}", help=f"Score: {h_score}/100")
    hc2.metric("📊 Score", f"{h_score}%")
    hc3.metric("🔴 High Risks", health["high_risks"])
    hc4.metric("💡 Opportunities", len(opportunities))
    hc5.metric("📋 Recommendations", len(recommendations))

    st.divider()

    if h_score >= 80:
        st.success(brief)
    elif h_score >= 60:
        st.info(brief)
    elif h_score >= 40:
        st.warning(brief)
    else:
        st.error(brief)

    st.divider()
    st.subheader("📊 Today's Overview")

    task_stats = snap.get("tasks", {}).get("stats", {})
    month = snap.get("finance", {}).get("month", {})
    reg   = snap.get("registry", {}).get("factories", {})
    ds    = snap.get("devstudio", {})

    oc1, oc2, oc3, oc4 = st.columns(4)
    oc1.metric("✅ Task Completion",   f"{task_stats.get('pct', 0)}%",
               help=f"{task_stats.get('done', 0)}/{task_stats.get('total', 0)} tasks")
    oc2.metric("💹 KPI Achievement",  f"{kpi_analysis.get('avg_pct', 0)}%")
    oc3.metric("🏭 Factory Health",
               f"{snap.get('analytics', {}).get('factories', {}).get('health_pct', reg.get('healthy', 0))}%")
    oc4.metric("💰 Today Revenue",
               f"¥{snap.get('finance', {}).get('today', {}).get('revenue', 0):,}")

    oc5, oc6, oc7, oc8 = st.columns(4)
    oc5.metric("📁 Active Projects",
               snap.get("registry", {}).get("projects", {}).get("active_projects", 0))
    oc6.metric("🗺️ Roadmap In-Progress", ds.get("roadmap", {}).get("in_progress", 0))
    oc7.metric("📋 Open Decisions",      ds.get("open_decisions", 0))
    oc8.metric("⚙️ Active Workflows",
               snap.get("automation", {}).get("workflows", {}).get("enabled", 0))

    _ws = snap.get("workspace_sync", {})
    if _ws:
        st.divider()
        st.subheader("🔄 Workspace Sync Health")
        ws1, ws2, ws3, ws4 = st.columns(4)
        ws1.metric("🔌 接続ステータス",
                   f"{_ws.get('connection_icon', '⚫')} {_ws.get('connection_status', '—')}")
        ws2.metric("🔍 ドライラン",   "✅ ON" if _ws.get("dry_run_default", True) else "⚠️ OFF")
        ws3.metric("📊 同期履歴",     _ws.get("total_syncs", 0))
        ws4.metric("🕐 最終同期",     _ws.get("last_sync", "未実行"))
        st.caption("⚠️ Workspace Sync は手動実行のみ。AI CEO は同期を実行しません。")

    if recommendations:
        st.divider()
        st.subheader("📋 Top Recommended Actions")
        for i, rec in enumerate(recommendations[:3], 1):
            with st.container(border=True):
                rc1, rc2 = st.columns([4, 1])
                rc1.markdown(f"**{i}. {rec['title']}**")
                rc1.caption(rec["reason"])
                rc2.metric("Impact",     rec["expected_impact"])
                rc2.metric("Confidence", f"{rec['confidence']}%")
                st.caption(f"📌 Action: {rec['action']}")

# ── Tab 2: KPI Summary ────────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("📊 KPI Summary")

    kc1, kc2, kc3 = st.columns(3)
    kc1.metric("📊 Average Achievement", f"{kpi_analysis.get('avg_pct', 0)}%")
    kc2.metric("🔴 KPI Alerts", len(kpi_analysis.get("alerts", [])))
    kc3.metric("💹 Revenue KPI", f"{kpi_analysis.get('revenue_pct', 0)}%")

    st.divider()

    kpi_summary = kpi_analysis.get("summary", [])
    if kpi_summary:
        for row in kpi_summary:
            k1, k2, k3, k4 = st.columns([3, 1, 1, 2])
            k1.markdown(f"{row['icon']} **{row['label']}**")
            k2.metric("Actual", f"{row['actual']:,} {row['unit']}")
            k3.metric("Target", f"{row['target']:,} {row['unit']}")
            k4.progress(min(row["pct"], 100) / 100, text=f"{row['pct']}%")
    else:
        st.caption("KPI data not available.")

    st.divider()
    st.subheader("💰 Revenue Summary")
    month = snap.get("finance", {}).get("month", {})
    today_fin = snap.get("finance", {}).get("today", {})
    rev = month.get("revenue", 0)
    exp = month.get("expense", 0)
    be  = month.get("breakeven", 0)

    fm1, fm2, fm3, fm4, fm5 = st.columns(5)
    fm1.metric("今日の売上",   f"¥{today_fin.get('revenue', 0):,}")
    fm2.metric("今月売上",     f"¥{rev:,}")
    fm3.metric("今月費用",     f"¥{exp:,}")
    fm4.metric("今月利益",     f"¥{rev - exp:,}")
    fm5.metric("損益分岐点まで", f"¥{max(0, be - rev):,}")

    acc = snap.get("accounting", {})
    roi_data = acc.get("roi", {})
    if roi_data:
        fc1, fc2, fc3 = st.columns(3)
        fc1.metric("📊 ROI", f"{roi_data.get('roi', 0)}%")
        fc2.metric("🎯 目標達成率", f"{roi_data.get('target_attainment', 0)}%")
        fc3.metric("🔔 監査アラート", acc.get("audit", {}).get("total", 0))

# ── Tab 3: Priorities ─────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("⚡ Top 10 Priorities")
    st.caption("Scored by Impact(40%) + Urgency(30%) + ROI(20%) + Dependencies(10%)")

    if priorities:
        for i, p in enumerate(priorities, 1):
            overdue_badge = " 🔴 OVERDUE" if p.get("overdue") else ""
            src_badge = {"roadmap": "🗺️ Roadmap", "task": "✅ Task", "decision": "📋 Decision"}.get(p["source"], p["source"])
            with st.container(border=True):
                pc1, pc2, pc3 = st.columns([4, 1, 1])
                pc1.markdown(f"**#{i} {p['icon']} {p['title']}**{overdue_badge}")
                pc1.caption(f"{src_badge} | Status: {p['status']} | Priority: {p['priority']}")
                pc2.metric("Score", p["score"])
                pc3.progress(min(int(p["score"]), 100) / 100)
    else:
        st.info("No pending priorities found. All items may be completed or archived.")

# ── Tab 4: Opportunities ──────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("💡 Top Opportunities")

    POT_COLOR = {"high": "🟢", "medium": "🟡", "low": "🔵"}
    CAT_LABEL = {
        "roi": "💰 ROI",
        "unused_factory": "🏭 Unused Factory",
        "automation": "⚙️ Automation",
        "content": "📝 Content",
    }

    if opportunities:
        for opp in opportunities:
            pot = opp.get("potential", "medium")
            with st.container(border=True):
                oc1, oc2 = st.columns([5, 1])
                oc1.markdown(f"{opp['icon']} **{opp['title']}**")
                oc1.caption(opp["detail"])
                oc1.caption(f"Factory: {opp['factory']} | Category: {CAT_LABEL.get(opp['category'], opp['category'])}")
                oc2.metric("Potential", f"{POT_COLOR.get(pot, '⚪')} {pot.capitalize()}")
    else:
        st.success("No major opportunities detected — all factories appear active.")

# ── Tab 5: Risks ──────────────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("⚠️ Risk Assessment")

    high_risks   = [r for r in risks if r.get("severity") == "high"]
    medium_risks = [r for r in risks if r.get("severity") == "medium"]
    low_risks    = [r for r in risks if r.get("severity") == "low"]

    rc1, rc2, rc3 = st.columns(3)
    rc1.metric("🔴 High",   len(high_risks))
    rc2.metric("⚠️ Medium", len(medium_risks))
    rc3.metric("🟡 Low",    len(low_risks))

    st.divider()

    CAT_LABEL_R = {
        "revenue":             "💰 Revenue",
        "project_delay":       "📅 Project Delay",
        "factory_degradation": "🏭 Factory",
        "roadmap":             "🗺️ Roadmap",
        "kpi":                 "📊 KPI",
        "health":              "🏥 Health",
    }

    if risks:
        for r in risks:
            with st.container(border=True):
                r1, r2 = st.columns([5, 1])
                sev = r["severity"]
                r1.markdown(f"{r['icon']} **{r['title']}**")
                r1.caption(r["detail"])
                r1.caption(f"Category: {CAT_LABEL_R.get(r['category'], r['category'])} | Factory: {r['factory']}")
                r2.metric("Severity", sev.capitalize())
    else:
        st.success("No risks identified. OS is operating within normal parameters.")

# ── Tab 6: Recommendations ────────────────────────────────────────────────────
with tabs[5]:
    st.subheader("📋 Recommended Actions")
    st.caption("Recommendations only. No actions are executed automatically.")

    IMP_ICON = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}

    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            imp_icon = IMP_ICON.get(rec["expected_impact"], "⚪")
            conf = rec["confidence"]
            with st.expander(
                f"#{i} {imp_icon} {rec['title']} — {rec['related_factory']}",
                expanded=(i <= 3),
            ):
                st.markdown(f"**Reason:** {rec['reason']}")
                st.markdown(f"**Action:** {rec['action']}")
                rmc1, rmc2, rmc3 = st.columns(3)
                rmc1.metric("Expected Impact", rec["expected_impact"])
                rmc2.metric("Confidence",      f"{conf}%")
                rmc3.metric("Factory",         rec["related_factory"])
    else:
        st.success("No recommendations — OS is operating optimally.")

# ── Tab 7: Executive Report ───────────────────────────────────────────────────
with tabs[6]:
    st.subheader("📄 Executive Report")

    if st.button("📄 Generate Executive Report", type="primary", key="gen_report"):
        from src.aiceo.executive_report import generate_report, export_report
        with st.spinner("Generating report…"):
            content = generate_report(
                snap, health, brief, priorities, risks,
                opportunities, recommendations, kpi_analysis,
            )
        st.session_state["ceo_report_content"] = content
        st.success("Report generated.")

    if "ceo_report_content" in st.session_state:
        content = st.session_state["ceo_report_content"]

        col_exp, col_dl, col_save = st.columns(3)
        with col_dl:
            st.download_button(
                label="⬇️ Download Markdown",
                data=content.encode("utf-8"),
                file_name=f"{TODAY}_executive_report.md",
                mime="text/markdown",
                use_container_width=True,
                key="dl_exec_report",
            )
        with col_save:
            if st.button("💾 Save to reports/aiceo/", use_container_width=True, key="save_exec"):
                from src.aiceo.executive_report import export_report
                path = export_report(content)
                st.success(f"Saved: `{path.relative_to(ROOT)}`")

        with st.expander("Report Preview", expanded=True):
            st.markdown(content)

    st.divider()
    st.subheader("📁 Report History")
    from src.aiceo.executive_report import get_report_history
    history = get_report_history()
    if history:
        for rpt in history:
            with st.expander(f"📄 {rpt['name']} — {rpt['size_kb']} KB — {rpt['modified']}"):
                if rpt["content"]:
                    st.markdown(rpt["content"])
                else:
                    st.caption("File too large to preview.")
    else:
        st.caption("No reports saved yet. Generate and save a report above.")
