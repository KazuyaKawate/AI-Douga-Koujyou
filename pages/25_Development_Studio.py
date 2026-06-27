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
        "v5.2 · ローカルJSON → Google Sheets マッピング。"
        "**手動同期のみ。自動実行なし。ドライラン デフォルト。外部API不使用（Phase 1）。**"
    )

    try:
        from src.workspace.sync_validator import load_settings as _ws_load_settings, \
            validate_settings as _ws_validate, get_connection_status as _ws_conn_status, \
            get_enabled_targets as _ws_targets
        from src.workspace.sync_engine import generate_preview as _ws_preview, \
            run_dry_run as _ws_dry_run, get_sync_health as _ws_health
        from src.workspace.sync_history import get_summary as _ws_hist_sum, \
            get_recent as _ws_hist_recent
        from src.workspace.sync_models import STATUS_ICONS as _ws_status_icons

        _ws_settings = _ws_load_settings()
        _ws_conn     = _ws_conn_status(_ws_settings)
        _ws_hist     = _ws_hist_sum()
        _ws_health   = _ws_health(_ws_settings)

        # Connection Status Banner
        if _ws_conn["status"] == "unconfigured":
            st.warning(
                "⚫ **Workspace Sync 未設定**  \n"
                "`config/workspace_settings.json` に `spreadsheet_id` と "
                "`google_credentials_path` を設定してください。"
            )
        elif _ws_conn["status"] == "no_credentials":
            st.error(
                "🔴 **Google認証ファイルなし**  \n"
                "Google Cloud ConsoleからService Account JSONをダウンロードし、"
                "`config/google_credentials.json` に配置してください。"
            )
        elif _ws_conn["status"] in ("no_spreadsheet", "disabled"):
            st.warning(f"{_ws_conn['icon']} **{_ws_conn['label']}** — 設定を確認してください。")
        else:
            st.info(
                f"{_ws_conn['icon']} **{_ws_conn['label']}**  \n"
                "Phase 1: ローカルデータの読み取り・プレビュー生成のみ。"
                "実際のSheets書き込みはPhase 2で実装予定。"
            )

        st.divider()

        # Summary metrics
        wsm1, wsm2, wsm3, wsm4, wsm5 = st.columns(5)
        wsm1.metric("🔌 接続",       f"{_ws_conn['icon']} {_ws_conn['label']}")
        wsm2.metric("🔍 ドライラン", "✅ ON" if _ws_conn["dry_run_default"] else "⚠️ OFF")
        wsm3.metric("📊 同期総数",   _ws_hist["total_syncs"])
        wsm4.metric("✅ 成功",       _ws_hist["successful"])
        wsm5.metric("⚠️ 競合総数",   _ws_hist["total_conflicts"])

        st.divider()

        # Validation
        _ws_valid, _ws_errors = _ws_validate(_ws_settings)
        st.markdown("**設定バリデーション**")
        if _ws_valid:
            st.success("✅ 設定は有効です（Phase 2で接続可能）")
        else:
            for e in _ws_errors:
                st.warning(f"⚠️ {e}")

        st.divider()

        # Sync Preview
        st.markdown("**同期プレビュー（ドライラン）**")
        st.caption("以下はローカルJSONから読み取ったデータ行数です。実際のAPI通信は行いません。")

        _ws_enabled_targets = _ws_targets(_ws_settings)
        if not _ws_enabled_targets:
            st.caption("有効な同期ターゲットがありません。`config/workspace_settings.json` を確認してください。")
        else:
            _ws_previews = _ws_preview(_ws_settings)
            for pv in _ws_previews:
                with st.expander(
                    f"{'✅' if pv['ready'] else '❌'} **{pv['target_name']}** → "
                    f"シート: `{pv['sheet_name']}`  |  "
                    f"ローカルファイル: `{pv['local_file']}`  |  "
                    f"行数: {pv['rows_total']}",
                    expanded=False
                ):
                    if pv.get("error"):
                        st.error(f"エラー: {pv['error']}")
                    else:
                        pvc1, pvc2, pvc3 = st.columns(3)
                        pvc1.metric("📊 総行数",   pv["rows_total"])
                        pvc2.metric("🆕 新規行",   pv["rows_new"])
                        pvc3.metric("⚠️ 競合",     pv["conflict_count"])

        st.divider()

        # Manual Dry Run button
        st.markdown("**手動ドライラン**")
        st.caption("ローカルデータを読み取り、プレビューを生成します。外部API通信なし。")
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

        # Sync History
        st.markdown("**同期履歴 (直近10件)**")
        _ws_recent = _ws_hist_recent(10)
        if not _ws_recent:
            st.caption("同期履歴なし。ドライランを実行すると履歴が記録されます。")
        else:
            for rec in _ws_recent:
                s_icon = _ws_status_icons.get(rec.get("status", ""), "❓")
                dr_badge = "🔍 Dry" if rec.get("dry_run") else "⚡ Real"
                st.caption(
                    f"{s_icon} `{rec.get('timestamp', '?')}` — "
                    f"{dr_badge} · {rec.get('target_id', '?')} · "
                    f"rows={rec.get('rows_synced', 0)} · "
                    f"conflicts={rec.get('conflicts', 0)}"
                )

    except Exception as exc:
        st.error(f"Workspace Sync の読み込みに失敗しました: {exc}")
