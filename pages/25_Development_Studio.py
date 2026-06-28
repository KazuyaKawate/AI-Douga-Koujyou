"""
Creator Factory Development Studio — v5.0 Beta
OS development headquarters: roadmap, decisions, releases, health check, git status, exports.
No external API calls.
"""
import json
import sys
from datetime import date
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.devstudio.roadmap_manager import (
    get_all_items as get_roadmap, create_item as create_roadmap_item,
    update_item as update_roadmap_item, delete_item as delete_roadmap_item,
    get_summary as get_roadmap_summary, STATUSES as ROADMAP_STATUSES,
    TYPES as ROADMAP_TYPES, PRIORITIES,
)
from src.devstudio.release_manager import (
    get_all_releases, create_release, update_release, delete_release,
    get_latest_release, HEALTH_STATUSES,
)
from src.devstudio.decision_log_manager import (
    get_all_decisions, create_decision, update_decision, delete_decision,
    get_open_count, STATUSES as DEC_STATUSES, IMPACTS,
)
from src.devstudio.meeting_log_manager import (
    get_all_meetings, create_meeting, update_meeting, delete_meeting,
    get_recent_meetings,
)
from src.devstudio.git_status_reader import get_git_status
from src.devstudio.healthcheck_reader import run_healthcheck, get_script_exists
from src.devstudio.spreadsheet_exporter import export_all, get_export_history

APP_VERSION = "5.0-beta"
TODAY = date.today().isoformat()

st.set_page_config(
    page_title="Development Studio | Creator Factory OS",
    page_icon="🛠️",
    layout="wide",
)

st.title("🛠️ Creator Factory Development Studio")
st.caption(f"OS Development Headquarters | v{APP_VERSION} Beta")

st.divider()

tabs = st.tabs([
    "📊 Overview",
    "🗺️ Roadmap",
    "🚀 Releases",
    "📋 Decision Log",
    "📝 Meeting Notes",
    "🏥 Health Check",
    "🔀 Git Status",
    "📤 Spreadsheet Export",
    "📦 Module SDK",
    "🔄 Workspace Sync",
])

# ── Tab 1: Overview ────────────────────────────────────────────────────────────
with tabs[0]:
    st.subheader("📊 Overview")

    settings_path = ROOT / "config" / "devstudio_settings.json"
    ds_settings: dict = {}
    if settings_path.exists():
        try:
            ds_settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    latest_rel = get_latest_release()
    roadmap_sum = get_roadmap_summary()
    open_decisions = get_open_count()
    recent_meetings = get_recent_meetings(3)

    factory_count = 0
    project_count = 0
    try:
        from src.core.factory_registry import FactoryRegistry
        from src.core.project_manager import get_all_projects
        factory_count = FactoryRegistry.get_summary().get("total", 0)
        project_count = len(get_all_projects())
    except Exception:
        pass

    health_status = "unknown"
    if get_script_exists():
        health_status = "script available"

    ov1, ov2, ov3, ov4 = st.columns(4)
    ov1.metric("🏷️ Current Version", APP_VERSION)
    ov2.metric("🚀 Latest Release", latest_rel["version"] if latest_rel else "—")
    ov3.metric("🏭 FactoryRegistry", factory_count)
    ov4.metric("📁 ProjectRegistry", project_count)

    ov5, ov6, ov7, ov8 = st.columns(4)
    ov5.metric("🗺️ Roadmap Items", roadmap_sum["total"])
    ov6.metric("🔄 In Progress", roadmap_sum["in_progress"])
    ov7.metric("📋 Open Decisions", open_decisions)
    ov8.metric("📝 Meetings", len(get_all_meetings()))

    st.divider()

    col_road, col_meet = st.columns(2)

    with col_road:
        st.markdown("**🗺️ Roadmap — In Progress**")
        in_prog = [r for r in get_roadmap() if r.get("status") == "in_progress"]
        if in_prog:
            for item in in_prog:
                st.markdown(
                    f"- `{item['roadmap_id']}` **{item['title']}** "
                    f"(v{item['version']} · {item['priority']})"
                )
        else:
            st.caption("No items in progress.")

    with col_meet:
        st.markdown("**📝 Recent Meetings**")
        if recent_meetings:
            for mtg in recent_meetings:
                st.markdown(f"- `{mtg['date']}` **{mtg['title']}**")
                if mtg.get("next_actions"):
                    st.caption(f"  Next: {mtg['next_actions'][:80]}")
        else:
            st.caption("No meetings logged yet.")

    st.divider()
    st.markdown("**🎯 Next Milestone**")
    next_ms = ds_settings.get("next_milestone", "—")
    st.info(f"**{next_ms}**")

# ── Tab 2: Roadmap ─────────────────────────────────────────────────────────────
with tabs[1]:
    st.subheader("🗺️ Roadmap Manager")

    roadmap_items = get_roadmap()

    status_filter = st.selectbox(
        "Filter by status", ["all"] + ROADMAP_STATUSES, key="rm_filter"
    )
    filtered_rm = roadmap_items if status_filter == "all" else [
        r for r in roadmap_items if r.get("status") == status_filter
    ]

    if filtered_rm:
        STATUS_ICONS = {
            "planned": "⏳", "in_progress": "🔄", "completed": "✅",
            "blocked": "🔴", "archived": "📦",
        }
        for item in filtered_rm:
            icon = STATUS_ICONS.get(item.get("status", ""), "⚪")
            with st.expander(
                f"{icon} `{item['roadmap_id']}` — {item['title']} (v{item['version']})",
                expanded=False,
            ):
                c1, c2 = st.columns(2)
                c1.markdown(f"**Type:** {item.get('type', '—')}")
                c1.markdown(f"**Priority:** {item.get('priority', '—')}")
                c1.markdown(f"**Status:** {item.get('status', '—')}")
                c2.markdown(f"**Planned:** {item.get('planned_date', '—')}")
                c2.markdown(f"**Completed:** {item.get('completed_date') or '—'}")
                if item.get("notes"):
                    st.caption(item["notes"])

                btn_c1, btn_c2 = st.columns(2)
                with btn_c1:
                    new_status = st.selectbox(
                        "Update status",
                        ROADMAP_STATUSES,
                        index=ROADMAP_STATUSES.index(item.get("status", "planned")),
                        key=f"rm_status_{item['roadmap_id']}",
                    )
                    if st.button("💾 Save Status", key=f"rm_save_{item['roadmap_id']}"):
                        update_roadmap_item(item["roadmap_id"], status=new_status)
                        st.success("Saved.")
                        st.rerun()
                with btn_c2:
                    if st.button("🗑️ Delete", key=f"rm_del_{item['roadmap_id']}",
                                 type="secondary"):
                        delete_roadmap_item(item["roadmap_id"])
                        st.rerun()
    else:
        st.caption("No roadmap items found.")

    st.divider()
    with st.expander("➕ Add Roadmap Item", expanded=False):
        nc1, nc2 = st.columns(2)
        with nc1:
            n_version  = st.text_input("Version",      value=APP_VERSION, key="rm_n_ver")
            n_title    = st.text_input("Title",         key="rm_n_title")
            n_type     = st.selectbox("Type",           ROADMAP_TYPES, key="rm_n_type")
            n_priority = st.selectbox("Priority",       PRIORITIES, index=2, key="rm_n_pri")
        with nc2:
            n_status   = st.selectbox("Status",         ROADMAP_STATUSES, key="rm_n_stat")
            n_planned  = st.text_input("Planned Date",  value=TODAY, key="rm_n_plan")
            n_complete = st.text_input("Completed Date", value="", key="rm_n_comp")
            n_notes    = st.text_area("Notes",          key="rm_n_notes", height=80)
        if st.button("➕ Add Item", type="primary", key="rm_add"):
            if n_title:
                create_roadmap_item(
                    n_version, n_title, n_type, n_priority,
                    n_status, n_planned, n_complete, n_notes,
                )
                st.success("Added.")
                st.rerun()
            else:
                st.warning("Title is required.")

# ── Tab 3: Releases ────────────────────────────────────────────────────────────
with tabs[2]:
    st.subheader("🚀 Release Manager")

    releases = sorted(get_all_releases(), key=lambda r: r.get("date", ""), reverse=True)

    HEALTH_ICONS = {"green": "✅", "yellow": "🟡", "red": "🔴", "unknown": "⚪"}

    if releases:
        for rel in releases:
            hicon = HEALTH_ICONS.get(rel.get("health_status", "unknown"), "⚪")
            with st.expander(
                f"{hicon} v{rel['version']} — {rel['title']} ({rel.get('date', '—')})",
                expanded=False,
            ):
                rc1, rc2 = st.columns(2)
                rc1.markdown(f"**Release ID:** `{rel['release_id']}`")
                rc1.markdown(f"**Version:** {rel['version']}")
                rc1.markdown(f"**Date:** {rel.get('date', '—')}")
                rc2.markdown(f"**Commit:** `{rel.get('commit_id') or '—'}`")
                rc2.markdown(f"**Health:** {hicon} {rel.get('health_status', '—')}")
                if rel.get("summary"):
                    st.markdown(f"**Summary:** {rel['summary']}")
                if rel.get("notes"):
                    st.caption(rel["notes"])

                db1, db2 = st.columns(2)
                with db1:
                    new_health = st.selectbox(
                        "Update health",
                        HEALTH_STATUSES,
                        index=HEALTH_STATUSES.index(rel.get("health_status", "unknown")),
                        key=f"rel_health_{rel['release_id']}",
                    )
                    if st.button("💾 Save", key=f"rel_save_{rel['release_id']}"):
                        update_release(rel["release_id"], health_status=new_health)
                        st.success("Saved.")
                        st.rerun()
                with db2:
                    if st.button("🗑️ Delete", key=f"rel_del_{rel['release_id']}",
                                 type="secondary"):
                        delete_release(rel["release_id"])
                        st.rerun()
    else:
        st.caption("No releases logged yet.")

    st.divider()
    with st.expander("➕ Add Release", expanded=False):
        rfc1, rfc2 = st.columns(2)
        with rfc1:
            r_ver    = st.text_input("Version",     value=APP_VERSION, key="rel_n_ver")
            r_title  = st.text_input("Title",       key="rel_n_title")
            r_date   = st.text_input("Date",        value=TODAY, key="rel_n_date")
            r_commit = st.text_input("Commit ID",   key="rel_n_commit")
        with rfc2:
            r_health  = st.selectbox("Health Status", HEALTH_STATUSES, key="rel_n_health")
            r_summary = st.text_area("Summary",       key="rel_n_sum", height=60)
            r_notes   = st.text_area("Notes",         key="rel_n_notes", height=60)
        if st.button("➕ Add Release", type="primary", key="rel_add"):
            if r_ver and r_title:
                create_release(r_ver, r_title, r_date, r_commit, r_health, r_summary, r_notes)
                st.success("Added.")
                st.rerun()
            else:
                st.warning("Version and Title are required.")

# ── Tab 4: Decision Log ────────────────────────────────────────────────────────
with tabs[3]:
    st.subheader("📋 Decision Log")

    decisions = sorted(get_all_decisions(), key=lambda d: d.get("date", ""), reverse=True)

    STATUS_DOT = {"open": "🔵", "accepted": "✅", "rejected": "❌", "superseded": "📦"}
    IMPACT_DOT = {"high": "🔴", "medium": "🟡", "low": "🟢"}

    if decisions:
        for dec in decisions:
            sdot = STATUS_DOT.get(dec.get("status", "open"), "⚪")
            idot = IMPACT_DOT.get(dec.get("impact", "medium"), "⚪")
            with st.expander(
                f"{sdot} `{dec['decision_id']}` — {dec.get('theme', '—')} | {idot} {dec.get('impact', '—')} | {dec.get('date', '—')}",
                expanded=False,
            ):
                st.markdown(f"**Decision:** {dec.get('decision', '—')}")
                st.markdown(f"**Reason:** {dec.get('reason', '—')}")
                st.markdown(f"**Expected Effect:** {dec.get('expected_effect', '—')}")
                dc1, dc2 = st.columns(2)
                dc1.caption(f"Version: {dec.get('version', '—')}")
                dc2.caption(f"Status: {dec.get('status', '—')}")

                db1, db2 = st.columns(2)
                with db1:
                    new_dstatus = st.selectbox(
                        "Update status",
                        DEC_STATUSES,
                        index=DEC_STATUSES.index(dec.get("status", "open")),
                        key=f"dec_stat_{dec['decision_id']}",
                    )
                    if st.button("💾 Save", key=f"dec_save_{dec['decision_id']}"):
                        update_decision(dec["decision_id"], status=new_dstatus)
                        st.success("Saved.")
                        st.rerun()
                with db2:
                    if st.button("🗑️ Delete", key=f"dec_del_{dec['decision_id']}",
                                 type="secondary"):
                        delete_decision(dec["decision_id"])
                        st.rerun()
    else:
        st.caption("No decisions logged yet.")

    st.divider()
    with st.expander("➕ Add Decision", expanded=False):
        dfc1, dfc2 = st.columns(2)
        with dfc1:
            d_date   = st.text_input("Date",            value=TODAY, key="dec_n_date")
            d_ver    = st.text_input("Version",          value=APP_VERSION, key="dec_n_ver")
            d_theme  = st.text_input("Theme",            key="dec_n_theme")
            d_impact = st.selectbox("Impact",            IMPACTS, index=1, key="dec_n_imp")
        with dfc2:
            d_status = st.selectbox("Status",            DEC_STATUSES, key="dec_n_stat")
            d_dec    = st.text_area("Decision",          key="dec_n_dec", height=60)
            d_reason = st.text_area("Reason",            key="dec_n_reas", height=60)
            d_effect = st.text_area("Expected Effect",   key="dec_n_eff", height=60)
        if st.button("➕ Add Decision", type="primary", key="dec_add"):
            if d_dec and d_theme:
                create_decision(d_date, d_ver, d_theme, d_dec, d_reason, d_effect, d_impact, d_status)
                st.success("Added.")
                st.rerun()
            else:
                st.warning("Theme and Decision are required.")

# ── Tab 5: Meeting Notes ───────────────────────────────────────────────────────
with tabs[4]:
    st.subheader("📝 Meeting Notes")

    meetings = get_all_meetings()

    if meetings:
        for mtg in meetings:
            with st.expander(
                f"📅 {mtg.get('date', '—')} — {mtg.get('title', '—')}",
                expanded=False,
            ):
                mc1, mc2 = st.columns(2)
                mc1.markdown(f"**Agenda:** {mtg.get('agenda', '—')}")
                mc2.markdown(f"**Decisions:** {mtg.get('decisions', '—')}")
                st.markdown(f"**Notes:**  \n{mtg.get('notes', '—')}")
                if mtg.get("next_actions"):
                    st.info(f"**Next Actions:** {mtg['next_actions']}")

                mb1, mb2 = st.columns(2)
                with mb1:
                    new_na = st.text_input(
                        "Update Next Actions",
                        value=mtg.get("next_actions", ""),
                        key=f"mtg_na_{mtg['meeting_id']}",
                    )
                    if st.button("💾 Save", key=f"mtg_save_{mtg['meeting_id']}"):
                        update_meeting(mtg["meeting_id"], next_actions=new_na)
                        st.success("Saved.")
                        st.rerun()
                with mb2:
                    if st.button("🗑️ Delete", key=f"mtg_del_{mtg['meeting_id']}",
                                 type="secondary"):
                        delete_meeting(mtg["meeting_id"])
                        st.rerun()
    else:
        st.caption("No meeting notes yet.")

    st.divider()
    with st.expander("➕ Add Meeting Note", expanded=False):
        mfc1, mfc2 = st.columns(2)
        with mfc1:
            m_date   = st.text_input("Date",         value=TODAY, key="mtg_n_date")
            m_title  = st.text_input("Title",         key="mtg_n_title")
            m_agenda = st.text_area("Agenda",         key="mtg_n_agenda", height=60)
        with mfc2:
            m_notes  = st.text_area("Notes",          key="mtg_n_notes", height=60)
            m_decs   = st.text_area("Decisions Made", key="mtg_n_decs", height=60)
            m_next   = st.text_area("Next Actions",   key="mtg_n_next", height=60)
        if st.button("➕ Add Meeting", type="primary", key="mtg_add"):
            if m_title:
                create_meeting(m_date, m_title, m_agenda, m_notes, m_decs, m_next)
                st.success("Added.")
                st.rerun()
            else:
                st.warning("Title is required.")

# ── Tab 6: Health Check ────────────────────────────────────────────────────────
with tabs[5]:
    st.subheader("🏥 Health Check")

    if not get_script_exists():
        st.error("scripts/check_project.py not found.")
    else:
        st.info(
            "Health check reads the project file structure. "
            "Click the button below to run it — it is not run automatically."
        )
        if st.button("▶️ Run Health Check", type="primary", key="hc_run"):
            with st.spinner("Running health check..."):
                result = run_healthcheck()
            if result["ok"]:
                st.success(f"✅ STATUS: OK (exit code {result.get('returncode', 0)})")
            else:
                st.error(f"❌ STATUS: {result['status_label']}")
            with st.expander("Full output", expanded=True):
                st.code(result["output"], language=None)

        st.divider()
        st.caption("**Manual Status Fields** — update if health check is not available")
        mc1, mc2, mc3 = st.columns(3)
        mc1.text_input("Manual Status", value="OK", key="hc_man_status")
        mc2.text_input("Checked On", value=TODAY, key="hc_man_date")
        mc3.text_input("Notes", key="hc_man_notes")

# ── Tab 7: Git Status ──────────────────────────────────────────────────────────
with tabs[6]:
    st.subheader("🔀 Git Status")
    st.caption("Read-only. No destructive operations.")

    git = get_git_status()

    if not git["in_git_repo"]:
        st.warning("Not in a git repository or git is not available.")
    else:
        gc1, gc2, gc3 = st.columns(3)
        gc1.metric("🌿 Branch", git["branch"])
        gc2.metric("📝 Latest Commit", git["commit_hash"] or "—")
        gc3.metric("🗂️ Status", "🔴 Dirty" if git["is_dirty"] else "✅ Clean")

        if git["commit_subject"]:
            st.markdown(f"**Commit Message:** {git['commit_subject']}")
        if git["commit_date"]:
            st.caption(f"**Commit Date:** {git['commit_date']}")

        if git["is_dirty"]:
            with st.expander(f"Modified files ({git['dirty_count']})", expanded=True):
                for line in git["dirty_files"]:
                    st.code(line, language=None)
        else:
            st.success("Working tree is clean.")

    if st.button("🔄 Refresh", key="git_refresh"):
        st.rerun()

# ── Tab 8: Spreadsheet Export ──────────────────────────────────────────────────
with tabs[7]:
    st.subheader("📤 Spreadsheet Export")
    st.caption("CSV export compatible with spreadsheet management ledger.")

    if st.button("📤 Export All to CSV", type="primary", key="exp_all"):
        with st.spinner("Exporting..."):
            try:
                paths = export_all(
                    get_roadmap(),
                    get_all_releases(),
                    get_all_decisions(),
                    get_all_meetings(),
                )
                for key, path in paths.items():
                    st.success(f"✅ {key}: `{path.relative_to(ROOT)}`")
            except Exception as exc:
                st.error(f"Export error: {exc}")

    st.divider()

    ec1, ec2, ec3, ec4 = st.columns(4)
    with ec1:
        if st.button("📋 Export Roadmap", key="exp_road"):
            from src.devstudio.spreadsheet_exporter import export_roadmap
            p = export_roadmap(get_roadmap())
            st.success(f"✅ `{p.relative_to(ROOT)}`")
    with ec2:
        if st.button("🚀 Export Releases", key="exp_rel"):
            from src.devstudio.spreadsheet_exporter import export_releases
            p = export_releases(get_all_releases())
            st.success(f"✅ `{p.relative_to(ROOT)}`")
    with ec3:
        if st.button("📋 Export Decisions", key="exp_dec"):
            from src.devstudio.spreadsheet_exporter import export_decisions
            p = export_decisions(get_all_decisions())
            st.success(f"✅ `{p.relative_to(ROOT)}`")
    with ec4:
        if st.button("📝 Export Meetings", key="exp_mtg"):
            from src.devstudio.spreadsheet_exporter import export_meetings
            p = export_meetings(get_all_meetings())
            st.success(f"✅ `{p.relative_to(ROOT)}`")

    st.divider()
    st.markdown("**Export History** (`reports/devstudio/`)")
    history = get_export_history()
    if history:
        for f in history:
            st.caption(f"• `{f['name']}` — {f['size_kb']} KB — {f['modified']}")
    else:
        st.caption("No exports yet. Click Export to generate CSV files.")

# ── Tab 9: Module SDK ──────────────────────────────────────────────────────────
with tabs[8]:
    st.subheader("📦 Module SDK — Self-Registration Registry")
    st.caption("v5.1 · すべてのモジュールのMANIFEST情報を一覧表示。外部API不使用。読み取り専用。")

    try:
        from src.sdk.registry_builder import ModuleRegistry, TYPE_ICONS, STATUS_ICONS
        from src.sdk.module_loader import load_all_with_errors
        from src.sdk.module_manifest import SDK_VERSION, MODULE_TYPES

        sdk_sum = ModuleRegistry.get_summary()

        # Summary metrics
        sm1, sm2, sm3, sm4, sm5, sm6 = st.columns(6)
        sm1.metric("📦 SDK Version",    f"v{sdk_sum['sdk_version']}")
        sm2.metric("🗂️ Total Modules",  sdk_sum["total"])
        sm3.metric("✅ Valid",           sdk_sum["valid"])
        sm4.metric("❌ Invalid",         sdk_sum["invalid"])
        sm5.metric("🏭 Factories",       sdk_sum["factories"])
        sm6.metric("📤 Registry Export", "✅" if sdk_sum["registry_exported"] else "—",
                   help=f"最終エクスポート: {sdk_sum.get('registry_age', '—')}")

        st.divider()

        # Type breakdown
        st.markdown("**モジュールタイプ別**")
        tc1, tc2, tc3, tc4 = st.columns(4)
        tc1.metric("🏭 Factory",     sdk_sum["factories"])
        tc2.metric("🧠 Executive",   sdk_sum["executive"])
        tc3.metric("🛠️ Development", sdk_sum["development"])
        tc4.metric("🔧 Utility",     sdk_sum["utilities"])

        st.divider()

        # Registry export button
        exp_col, _ = st.columns([1, 3])
        with exp_col:
            if st.button("📤 config/module_registry.json を生成", type="primary", use_container_width=True,
                         key="sdk_export_registry"):
                try:
                    out = ModuleRegistry.export_registry()
                    st.success(f"✅ エクスポート完了: `{out.relative_to(ROOT)}`")
                except Exception as exc:
                    st.error(f"エクスポートエラー: {exc}")

        st.divider()

        # Module cards
        st.markdown("**登録モジュール一覧**")
        pairs = load_all_with_errors()
        for manifest, errors in pairs:
            is_valid = len(errors) == 0
            type_icon = TYPE_ICONS.get(manifest.get("module_type", ""), "📦")
            status_icon = STATUS_ICONS.get(manifest.get("status", "stable"), "✅")
            valid_badge = "✅" if is_valid else f"❌ {len(errors)} エラー"
            label = (
                f"{type_icon} **{manifest.get('module_name', '?')}** "
                f"v{manifest.get('version', '?')} · "
                f"{status_icon} {manifest.get('status', '?')} · {valid_badge}"
            )
            with st.expander(label, expanded=False):
                c_left, c_right = st.columns(2)
                with c_left:
                    st.markdown(f"**module_id**: `{manifest.get('module_id', '—')}`")
                    st.markdown(f"**display_name**: {manifest.get('display_name', '—')}")
                    st.markdown(f"**module_type**: {manifest.get('module_type', '—')}")
                    st.markdown(f"**version**: {manifest.get('version', '—')}")
                    st.markdown(f"**sdk_version**: {manifest.get('sdk_version', '—')}")
                    st.markdown(f"**min_os**: {manifest.get('minimum_os_version', '—')}")
                    st.markdown(f"**status**: {manifest.get('status', '—')}")
                with c_right:
                    st.markdown(f"**page_path**: `{manifest.get('page_path', '—')}`")
                    st.markdown(f"**package_path**: `{manifest.get('package_path', '—')}`")
                    st.markdown(f"**entrypoint**: `{manifest.get('entrypoint', '—')}`")
                    st.markdown(f"**dashboard_widget**: {manifest.get('dashboard_widget', False)}")
                    st.markdown(f"**mc_widget**: {manifest.get('mission_control_widget', False)}")
                    cfg = manifest.get("config_files", [])
                    st.markdown(f"**config_files**: {len(cfg)} 件")
                desc = manifest.get("description", "")
                if desc:
                    st.caption(f"説明: {desc}")
                tags = manifest.get("tags", [])
                if tags:
                    st.caption("Tags: " + " · ".join(f"`{t}`" for t in tags))
                if errors:
                    st.error("バリデーションエラー:\n" + "\n".join(f"• {e}" for e in errors))

    except Exception as exc:
        st.error(f"Module SDK の読み込みに失敗しました: {exc}")

# ── Tab 10: Workspace Sync ────────────────────────────────────────────────────
with tabs[9]:
    st.subheader("🔄 Google Workspace Sync")
    st.caption(
        "v5.2 Phase 3 · gspread 準備完了チェック。"
        "**手動同期のみ。自動実行なし。ドライランデフォルト。認証情報はリポジトリに保存しない。**"
    )

    st.error(
        "🔒 **セキュリティ警告: 認証情報はリポジトリに保存しないでください。**  \n"
        "`service_account_file` / `oauth_client_file` はローカルパスのみ設定可能。"
        "実際のJSONファイルは `.gitignore` に追加し、コミットしないでください。"
    )

    try:
        from src.workspace.sync_validator import (
            load_settings as _ws_load_settings,
            load_merged_settings as _ws_load_merged,
            get_local_config_status as _ws_local_status,
            validate_settings as _ws_validate,
            get_connection_status as _ws_conn_status,
            get_enabled_targets as _ws_targets,
            validate_connector_settings as _ws_validate_conn,
            check_no_credentials_committed as _ws_cred_check,
            get_phase3_readiness as _ws_phase3_ready,
        )
        from src.workspace.sync_engine import (
            generate_preview as _ws_preview,
            run_dry_run as _ws_dry_run,
            get_sync_health as _ws_sync_health,
        )
        from src.workspace.sync_executor import (
            run_preview as _ex_preview,
            get_connector_health as _ex_health,
            test_read_connection as _ex_test_read,
            run_test_write as _ex_test_write,
            run_production_sync as _ex_prod_sync,
        )
        from src.workspace.google_auth import (
            get_auth_config as _ws_auth_cfg,
            get_credential_status as _ws_cred_status,
            get_dependency_status as _ws_dep_status,
        )
        from src.workspace.sync_history import get_summary as _ws_hist_sum, get_recent as _ws_hist_recent
        from src.workspace.sync_models import STATUS_ICONS as _ws_status_icons

        _ws_settings    = _ws_load_settings()     # committed (auth_mode always disabled)
        _ws_merged      = _ws_load_merged()        # committed + local workspace_local.json
        _ws_local       = _ws_local_status()       # workspace_local.json summary
        _ws_conn        = _ws_conn_status(_ws_settings)
        _ws_hist        = _ws_hist_sum()
        _ws_auth        = _ws_auth_cfg(_ws_merged)  # use merged for effective auth_mode
        _ws_cred        = _ws_cred_status(_ws_merged)
        _ex_hlth        = _ex_health(_ws_settings)

        # ── Auth mode + credential status ─────────────────────────────────────
        st.divider()
        st.markdown("**🔑 認証モード & クレデンシャルステータス**")

        am1, am2, am3 = st.columns(3)
        am1.metric("🔑 Auth Mode",       _ws_auth["auth_mode"])
        am2.metric("🔐 Credential",      f"{_ws_cred['icon']} {_ws_cred['label']}")
        am3.metric("🔍 Dry-Run Default", "✅ ON" if _ws_settings.get("dry_run_default", True) else "⚠️ OFF")

        _cred_safe, _cred_warns = _ws_cred_check()
        if not _cred_safe:
            for w in _cred_warns:
                st.error(f"🚨 {w}")
        else:
            st.success("✅ 認証ファイルはリポジトリルートに存在しません（安全）")

        st.divider()

        # ── Phase 3 Readiness Checklist ───────────────────────────────────────
        st.markdown("**📋 Phase 3 準備状況チェックリスト**")
        st.caption(
            "gspread 統合（Phase 4+）前に必要なセキュリティ確認と依存パッケージ状況。"
            "🔒 マークはセキュリティ必須項目。📦 マークはオプション（Phase 4+ で必要）。"
        )

        try:
            _p3 = _ws_phase3_ready(_ws_settings)
            _p3_checks = _p3.get("checks", [])

            for _chk in _p3_checks:
                _is_opt = _chk.get("optional", False)
                _icon = "✅" if _chk["ok"] else ("📦" if _is_opt else "🔴")
                _prefix = "📦 " if _is_opt else "🔒 "
                _label_text = f"{_prefix}{_chk['label']}"
                if _chk["ok"]:
                    st.success(f"{_icon} **{_label_text}** — {_chk['detail']}")
                elif _is_opt:
                    st.info(f"{_icon} **{_label_text}** — {_chk['detail']}")
                else:
                    st.error(f"{_icon} **{_label_text}** — {_chk['detail']}")

            if _p3["ready"]:
                st.success(
                    "🔒 **セキュリティチェック完了** — "
                    "認証情報の保護が確認されました。"
                )
            else:
                for _blk in _p3["blockers"]:
                    st.warning(f"⚠️ {_blk}")

        except Exception as _p3_exc:
            st.warning(f"Phase 3 チェック実行エラー: {_p3_exc}")

        st.divider()

        # ── Connection Status Banner ──────────────────────────────────────────
        st.markdown("**🔌 接続ステータス**")
        if _ws_conn["status"] == "unconfigured":
            st.warning(
                "⚫ **Workspace Sync 未設定**  \n"
                "`config/workspace_settings.json` の `connector.auth_mode` を設定してください。"
            )
        elif _ws_conn["status"] == "no_credentials":
            st.warning(
                "🔴 **Google認証ファイルなし** — auth_mode が 'disabled' です。  \n"
                "Google Cloud ConsoleからService Account JSONをダウンロードし、"
                "`config/workspace_settings.json` の `connector` セクションを設定してください。"
            )
        else:
            st.info(
                f"{_ws_conn['icon']} **{_ws_conn['label']}** — "
                "Phase 3: gspread 準備完了。Phase 4+ でライブ書き込み実装予定。"
            )

        st.divider()

        # ── Summary metrics ──────────────────────────────────────────────────
        wsm1, wsm2, wsm3, wsm4, wsm5 = st.columns(5)
        wsm1.metric("🔌 接続",       f"{_ws_conn['icon']} {_ws_conn['label']}")
        wsm2.metric("📊 同期総数",   _ws_hist["total_syncs"])
        wsm3.metric("✅ 成功",       _ws_hist["successful"])
        wsm4.metric("⚠️ 競合総数",   _ws_hist["total_conflicts"])
        wsm5.metric("📋 有効ターゲット", _ex_hlth["target_count"])

        st.divider()

        # ── Sheet target list ────────────────────────────────────────────────
        st.markdown("**📋 同期ターゲット一覧**")
        _ws_enabled_targets = _ws_targets(_ws_settings)
        if not _ws_enabled_targets:
            st.caption("有効な同期ターゲットがありません。`config/workspace_settings.json` を確認してください。")
        else:
            for _t in _ws_enabled_targets:
                st.caption(
                    f"• `{_t.get('target_id', '?')}` → シート: **{_t.get('sheet_name', '?')}** "
                    f"| ローカル: `{_t.get('local_file', '?')}`"
                )

        st.divider()

        # ── Diff preview (using sync_executor) ───────────────────────────────
        st.markdown("**🔍 差分プレビュー（コネクター）**")
        st.caption(
            "ローカルJSONとシートデータ（auth_mode=disabled の場合はサンプルデータ）を比較します。"
            "APIへの実際の通信は行いません。"
        )

        if st.button("🔍 差分プレビューを実行", type="secondary", key="ws_diff_preview"):
            with st.spinner("差分を計算中…"):
                try:
                    _prev = _ex_preview(_ws_settings)
                    st.success(
                        f"✅ プレビュー完了  |  "
                        f"ターゲット: {_prev['target_count']}  |  "
                        f"競合: {_prev['total_conflicts']}  |  "
                        f"{_prev['duration_ms']}ms"
                    )
                    for _tp in _prev["targets"]:
                        _diff = _tp.get("diff") or {}
                        _sum  = _diff.get("summary", {})
                        with st.expander(
                            f"{'✅' if _tp['ready'] else '❌'} **{_tp['target_name']}** → "
                            f"シート: `{_tp['sheet_name']}` | {_tp.get('diff_summary', '')}",
                            expanded=False,
                        ):
                            if _tp.get("error"):
                                st.error(f"エラー: {_tp['error']}")
                            else:
                                dpc1, dpc2, dpc3, dpc4, dpc5 = st.columns(5)
                                dpc1.metric("🆕 追加",     _sum.get("added", 0))
                                dpc2.metric("✏️ 更新",     _sum.get("updated", 0))
                                dpc3.metric("🗑️ 削除",     _sum.get("removed", 0))
                                dpc4.metric("⚠️ 競合",     _sum.get("conflicts", 0))
                                dpc5.metric("✅ 変更なし", _sum.get("unchanged", 0))
                except Exception as exc:
                    st.error(f"差分プレビューエラー: {exc}")

        st.divider()

        # ── Validation ───────────────────────────────────────────────────────
        st.markdown("**⚙️ 設定バリデーション**")
        _ws_valid, _ws_errors = _ws_validate(_ws_settings)
        _conn_valid, _conn_errors = _ws_validate_conn(_ws_settings)
        if _ws_valid and _conn_valid:
            st.success("✅ 設定は有効です")
        else:
            for e in _ws_errors + _conn_errors:
                st.warning(f"⚠️ {e}")

        st.divider()

        # ── Phase 4-2: Local Config & Read-Only Connection Test ───────────────
        st.markdown("**🔌 Phase 4-2: ローカル設定 & 読み取り接続テスト**")
        st.caption(
            "gspread サービスアカウント認証で Google Sheets を **読み取り専用** で接続します。  \n"
            "設定は `config/workspace_local.json`（git除外）でローカル上書き可能。書き込みは無効。"
        )

        # ── Local config status ───────────────────────────────────────────────
        _lcol_a, _lcol_b = st.columns([2, 3])
        with _lcol_a:
            _local_icon = "✅" if _ws_local["exists"] else "⬜"
            st.markdown(f"**{_local_icon} `config/workspace_local.json`**")
            if _ws_local["exists"]:
                st.caption(
                    f"auth_mode: `{_ws_local['auth_mode'] or '(未設定)'}` ·  "
                    f"spreadsheet_id: {'✅ 設定済み' if _ws_local['has_spreadsheet_id'] else '⬜ 未設定'} ·  "
                    f"cred file: {'✅ 設定済み' if _ws_local['has_service_account_file'] else '⬜ 未設定'}"
                )
            else:
                st.caption(
                    "`config/workspace_local.json` が見つかりません。  \n"
                    "テンプレートを作成して spreadsheet_id・auth_mode を設定してください。"
                )
                with st.expander("workspace_local.json テンプレートを表示"):
                    st.code(
                        '{\n'
                        '  "auth_mode": "service_account",\n'
                        '  "service_account_file": "credentials/service-account.local.json",\n'
                        '  "spreadsheet_id": "YOUR_SPREADSHEET_ID",\n'
                        '  "worksheet_name": "KPI",\n'
                        '  "range": ""\n'
                        '}',
                        language="json",
                    )

        # ── Dependency + connection status grid ───────────────────────────────
        _deps42   = _ws_dep_status()
        _gs_cfg42 = _ws_merged.get("google_sheets", {})
        _conn_cfg42 = _ws_merged.get("connector", {})
        _cred_cfg42 = _ws_merged.get("credential_paths", {})
        _cred_file_path = (
            _ws_local.get("service_account_file", "")
            or _conn_cfg42.get("service_account_file", "")
            or _cred_cfg42.get("service_account_file", "")
        )

        p42c1, p42c2, p42c3 = st.columns(3)
        p42c1.metric(
            "📦 gspread",
            f"✅ {_deps42['gspread_version']}" if _deps42["gspread_installed"] else "❌ 未インストール",
        )
        p42c2.metric(
            "📦 google-auth",
            f"✅ {_deps42['google_auth_version']}" if _deps42["google_auth_installed"] else "❌ 未インストール",
        )
        p42c3.metric(
            "🔑 auth_mode (実効値)",
            _ws_auth["auth_mode"],
            help="committed=disabled。workspace_local.json で service_account に上書き可能。",
        )

        p42c4, p42c5, p42c6 = st.columns(3)
        _cred_exists42 = bool(_cred_file_path) and (ROOT / _cred_file_path).exists()
        p42c4.metric(
            "📄 認証ファイル",
            "✅ 存在" if _cred_exists42 else ("⬜ パス未設定" if not _cred_file_path else "🔴 ファイルなし"),
        )
        p42c5.metric(
            "🆔 spreadsheet_id",
            "✅ 設定済み" if _gs_cfg42.get("spreadsheet_id", "").strip() else "⬜ 未設定",
        )
        p42c6.metric(
            "📋 worksheet_name",
            _gs_cfg42.get("worksheet_name", "") or "⬜ 未設定",
        )

        # ── Setup hints ───────────────────────────────────────────────────────
        if not _deps42["all_ready"]:
            st.warning(
                f"📦 **依存パッケージ未インストール:** `{_deps42['install_hint']}`  \n"
                "ターミナルで実行後、ページをリロードしてください。"
                "`auth_mode=disabled` のままでもアプリは動作します。"
            )

        if _deps42["all_ready"] and not _cred_exists42:
            st.info(
                "**認証ファイルが見つかりません。** 以下の手順で設定してください:  \n"
                "1. Google Cloud Console → サービスアカウント作成 → JSON キー発行  \n"
                "2. `credentials/service-account.local.json` に配置  \n"
                "3. `config/workspace_local.json` の `auth_mode` を `\"service_account\"` に変更  \n"
                "4. `spreadsheet_id` と `worksheet_name` を設定  \n"
                "詳細: `docs/google_sheets_setup.md`"
            )

        if _deps42["all_ready"] and _cred_exists42 and not _gs_cfg42.get("spreadsheet_id", "").strip():
            st.warning(
                "**spreadsheet_id が未設定です。** `config/workspace_local.json` に設定してください:  \n"
                '`"spreadsheet_id": "YOUR_SPREADSHEET_ID_HERE"`'
            )

        # ── Read Connection Test button ────────────────────────────────────────
        _read_btn_col, _ = st.columns([1, 3])
        with _read_btn_col:
            if st.button(
                "🔌 読み取り接続テスト",
                type="secondary",
                use_container_width=True,
                key="ws_read_test",
            ):
                with st.spinner("接続テスト中…"):
                    try:
                        _rt = _ex_test_read(_ws_merged)  # use merged settings
                        if _rt["ok"]:
                            _src_label = {
                                "live":   "ライブ読み取り",
                                "sample": "サンプルデータ（disabled）",
                                "error":  "エラー",
                            }.get(_rt["source"], _rt["source"])
                            st.success(
                                f"✅ 接続テスト成功  |  "
                                f"ソース: {_src_label}  |  "
                                f"行数: {_rt['row_count']}  |  "
                                f"シート: `{_rt['sheet_tested'] or '(disabled)'}` |  "
                                f"{_rt['duration_ms']}ms"
                            )
                        else:
                            st.error(
                                f"🔴 接続テスト失敗  |  "
                                f"ステータス: `{_rt['client_status']}`  |  "
                                f"エラー: {_rt.get('error', '不明')}"
                            )
                            _cs = _rt["client_status"]
                            if _cs == "deps_missing":
                                st.code("pip install gspread google-auth", language="bash")
                            elif _cs == "no_file_configured":
                                st.info(
                                    "`config/workspace_local.json` に `service_account_file` を設定してください。"
                                )
                            elif _cs == "file_missing":
                                st.info(
                                    f"`{_cred_file_path}` が見つかりません。  \n"
                                    "Google Cloud Console からサービスアカウント JSON をダウンロードし "
                                    "`credentials/service-account.local.json` に配置してください。"
                                )
                            elif _cs == "disabled":
                                st.info(
                                    "`config/workspace_local.json` の `auth_mode` を "
                                    '`"service_account"` に変更してから再テストしてください。'
                                )
                    except Exception as exc:
                        st.error(f"接続テストエラー: {exc}")

        st.caption(
            "Phase 4-3 で読み取り接続確認済み。"
            "Phase 4-4 でテストシート（`test_worksheet_name`）への書き込みが可能になりました。"
            "本番シート（KPI / Revenue / Notes）への書き込みは Phase 4-5 以降で有効化予定。"
        )

        st.divider()

        # ── Manual Dry Run button ─────────────────────────────────────────────
        st.markdown("**手動ドライラン**")
        st.caption("ローカルデータを読み取り、同期プレビューを生成します。外部API通信なし。")
        _dr_btn_col, _ = st.columns([1, 3])
        with _dr_btn_col:
            if st.button("🔍 ドライラン実行", type="primary", use_container_width=True,
                         key="ws_dry_run"):
                with st.spinner("ドライラン実行中…"):
                    try:
                        _dr_result = _ws_dry_run(_ws_settings)
                        st.success(
                            f"✅ ドライラン完了  |  "
                            f"ターゲット: {_dr_result['targets']}  |  "
                            f"総行数: {_dr_result['total_rows']}  |  "
                            f"変更数: {_dr_result['total_changes']}"
                        )
                    except Exception as exc:
                        st.error(f"ドライランエラー: {exc}")

        st.divider()

        # ── Phase 4-4: Test Worksheet Append ─────────────────────────────────
        st.markdown("**✏️ Phase 4-4: テストシート書き込み（孤立ワークシートのみ）**")
        st.caption(
            "本番シート（KPI / Revenue / Notes / SNS / Sales）には書き込みません。  \n"
            "`test_worksheet_name` で指定した孤立テストシートに **1 行だけ** 追記します。"
        )

        _p44_tw = _ws_local.get("test_worksheet_name", "").strip()
        _PROD_WS44 = {"KPI", "Revenue", "Notes", "SNS", "Sales"}

        _p44c1, _p44c2, _p44c3 = st.columns(3)
        _p44c1.metric(
            "📋 test_worksheet_name",
            _p44_tw if _p44_tw else "⬜ 未設定",
        )
        _p44c2.metric(
            "🔒 本番シート保護",
            "✅ 安全" if (_p44_tw and _p44_tw not in _PROD_WS44) else (
                "🔴 本番シート名" if _p44_tw in _PROD_WS44 else "⬜ 未設定"
            ),
        )
        _p44c3.metric(
            "🔑 認証",
            "✅ 接続済み" if _ws_auth["auth_mode"] == "service_account" else f"⬜ {_ws_auth['auth_mode']}",
        )

        if not _p44_tw:
            st.warning(
                "**`test_worksheet_name` が未設定です。**  \n"
                "`config/workspace_local.json` に以下を追加してください:  \n"
                '`"test_worksheet_name": "Phase4-4-Test"`  \n'
                "また Google Sheets でこのシートを事前に作成してください（ヘッダー行不要）。"
            )
        elif _p44_tw in _PROD_WS44:
            st.error(
                f"**`{_p44_tw}` は本番シートです。**  \n"
                "別のシート名（例: `Phase4-4-Test`）を `test_worksheet_name` に設定してください。"
            )
        else:
            if st.button("🔍 ドライランプレビュー（書き込まない）", key="p44_dryrun", type="secondary"):
                with st.spinner("プレビュー中…"):
                    try:
                        _p44_dr = _ex_test_write(_ws_merged, dry_run=True, manual_execute=False)
                        if _p44_dr["ok"]:
                            st.info(
                                f"**プレビュー（書き込みなし）**  \n"
                                f"シート: `{_p44_dr['worksheet']}`  \n"
                                f"追記予定行: `{_p44_dr['row_data']}`"
                            )
                            st.session_state["p44_preview_ok"] = True
                        else:
                            st.error(f"プレビューエラー: {_p44_dr['error']}")
                            st.session_state["p44_preview_ok"] = False
                    except Exception as exc:
                        st.error(f"プレビューエラー: {exc}")
                        st.session_state["p44_preview_ok"] = False

            _p44_confirmed = st.checkbox(
                "プレビューを確認しました。テストシートに 1 行だけ追記します（既存データは変更されません）",
                key="p44_confirm",
            )

            if _p44_confirmed:
                if st.button("⚠️ テスト書き込みを実行", key="p44_write", type="primary"):
                    with st.spinner("書き込み中…"):
                        try:
                            _p44_result = _ex_test_write(
                                _ws_merged,
                                dry_run=False,
                                manual_execute=True,
                            )
                            if _p44_result["ok"] and _p44_result["executed"]:
                                st.success(
                                    f"✅ テスト書き込み成功  \n"
                                    f"シート: `{_p44_result['worksheet']}`  \n"
                                    f"追記行: `{_p44_result['row_data']}`  \n"
                                    f"処理時間: {_p44_result['duration_ms']}ms"
                                )
                                st.warning(
                                    "**ロールバック手順:**  \n"
                                    f"1. Google Sheets で `{_p44_result['worksheet']}` シートを開く  \n"
                                    "2. 追記された最終行を右クリック → 「行を削除」  \n"
                                    "3. または Ctrl+Z（Google Sheets の元に戻す）"
                                )
                            else:
                                st.error(
                                    f"書き込み失敗: "
                                    f"{_p44_result.get('error') or '不明なエラー'}"
                                )
                        except Exception as exc:
                            st.error(f"書き込みエラー: {exc}")

        st.caption(
            "⚠️ **`allow_write=True` は UI ボタン経由でのみ有効。コミット済みコードに含まれません。"
            "本番シートへの書き込みは Phase 4-5 以降。**"
        )

        st.divider()

        # ── Phase 4-5: 本番シート同期（KPI / Revenue / Notes）──────────────
        st.markdown("**📊 Phase 4-5: 本番シート同期（KPI / Revenue / Notes）**")
        st.caption(
            "dry-run プレビュー → 明示確認 → live sync の順に実行します。  \n"
            "行削除は行いません（追加・更新のみ）。KPI / Revenue / Notes 以外には一切アクセスしません。"
        )

        _p45c1, _p45c2, _p45c3 = st.columns(3)
        _p45c1.metric("対象シート", "KPI / Revenue / Notes")
        _p45c2.metric("書き込み戦略", "Upsert（追加+更新）")
        _p45c3.metric("削除", "なし（安全）")

        if st.button("🔍 差分プレビュー（書き込まない）", key="p45_dryrun", type="secondary"):
            with st.spinner("差分計算中..."):
                try:
                    _p45_dr = _ex_prod_sync(
                        _ws_merged,
                        dry_run=True,
                        manual_execute=False,
                        allow_write=False,
                    )
                    if _p45_dr["ok"]:
                        for _p45_tr in _p45_dr["targets"]:
                            if _p45_tr.get("error"):
                                st.error(f"[{_p45_tr['target_id']}] エラー: {_p45_tr['error']}")
                            else:
                                st.success(
                                    f"[{_p45_tr['sheet_name']}] "
                                    f"同期予定: {_p45_tr['flat_rows']}行"
                                )
                                if _p45_tr.get("preview"):
                                    with st.expander(f"{_p45_tr['sheet_name']} プレビュー（先頭3行）"):
                                        st.json(_p45_tr["preview"])
                        st.session_state["p45_preview_ok"] = True
                        st.info(f"プレビュー完了 | {_p45_dr['duration_ms']}ms | 書き込みは行われていません")
                    else:
                        st.error("プレビューに失敗しました")
                        st.session_state["p45_preview_ok"] = False
                except Exception as _p45_exc:
                    st.error(f"プレビューエラー: {_p45_exc}")
                    st.session_state["p45_preview_ok"] = False

        _p45_confirmed = st.checkbox(
            "差分プレビューを確認しました。本番シートに同期します（削除なし / ロールバック: Google Sheets の「元に戻す」で対応）",
            key="p45_confirm",
        )

        if _p45_confirmed:
            if st.button(
                "⚡ 本番同期を実行（KPI / Revenue / Notes）",
                key="p45_write",
                type="primary",
            ):
                with st.spinner("同期中..."):
                    try:
                        _p45_result = _ex_prod_sync(
                            _ws_merged,
                            dry_run=False,
                            manual_execute=True,
                            allow_write=True,
                        )
                        if _p45_result["executed"]:
                            st.success(
                                f"✅ 同期完了  \n"
                                f"追加: {_p45_result['total_appended']}行 / "
                                f"更新: {_p45_result['total_updated']}行 / "
                                f"スキップ: {_p45_result['total_skipped']}行  \n"
                                f"処理時間: {_p45_result['duration_ms']}ms"
                            )
                            for _p45_tr in _p45_result["targets"]:
                                if _p45_tr.get("error"):
                                    st.warning(f"[{_p45_tr['sheet_name']}] {_p45_tr['error']}")
                                else:
                                    st.caption(
                                        f"[{_p45_tr['sheet_name']}] "
                                        f"追加:{_p45_tr['appended']}行 / "
                                        f"更新:{_p45_tr['updated']}行 / "
                                        f"スキップ:{_p45_tr['skipped']}行"
                                    )
                            st.warning(
                                "**ロールバック手順:**  \n"
                                "Google Sheets を開き Ctrl+Z（元に戻す）で変更を取り消せます。  \n"
                                "または「ファイル → バージョン履歴」から特定時点に復元してください。"
                            )
                        else:
                            st.error(
                                f"同期が実行されませんでした: "
                                f"{_p45_result.get('error') or '不明なエラー'}"
                            )
                            for _p45_tr in _p45_result["targets"]:
                                if _p45_tr.get("error"):
                                    st.error(f"[{_p45_tr['sheet_name']}] {_p45_tr['error']}")
                    except Exception as _p45_exc:
                        st.error(f"同期エラー: {_p45_exc}")

        st.caption(
            "**allow_write=True は UI ボタン経由でのみ有効。"
            "コミット済みコードには含まれません。"
            "本番シートへの書き込みは慎重に実行してください。**"
        )

        st.divider()

        # ── Sync History ─────────────────────────────────────────────────────
        st.markdown("**同期履歴 (直近10件)**")
        _ws_recent = _ws_hist_recent(10)
        if not _ws_recent:
            st.caption("同期履歴なし。ドライランを実行すると履歴が記録されます。")
        else:
            for rec in _ws_recent:
                s_icon   = _ws_status_icons.get(rec.get("status", ""), "❓")
                dr_badge = "🔍 Dry" if rec.get("dry_run") else "⚡ Real"
                st.caption(
                    f"{s_icon} `{rec.get('timestamp', '?')}` — "
                    f"{dr_badge} · {rec.get('target_id', '?')} · "
                    f"rows={rec.get('rows_synced', 0)} · "
                    f"conflicts={rec.get('conflicts', 0)}"
                )

    except Exception as exc:
        st.error(f"Workspace Sync の読み込みに失敗しました: {exc}")
