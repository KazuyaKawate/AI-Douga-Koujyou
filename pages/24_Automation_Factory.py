"""
Automation Factory — Creator Factory OS v4.8
Rule-based workflow automation connecting all factories.
Safe-first: dry-run mode is default. No external API calls. No auto-publishing.
"""
import streamlit as st
import json
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="自動化工場", page_icon="⚙️", layout="wide")

ROOT = Path(__file__).parent.parent


def _load_settings() -> dict:
    p = ROOT / "config" / "automation_settings.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"dry_run_default": True, "max_runs": 200}


def _save_settings(s: dict) -> None:
    p = ROOT / "config" / "automation_settings.json"
    p.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Header ─────────────────────────────────────────────────────────────────────

st.title("⚙️ 自動化工場")
st.caption("Automation Factory  •  Creator Factory OS v4.8")

settings = _load_settings()
dry_run_default: bool = settings.get("dry_run_default", True)

# Global dry-run badge
if dry_run_default:
    st.info("🛡️ **ドライランモード ON** — アクションはシミュレートのみ。実際のデータは変更されません。", icon=None)
else:
    st.warning("⚡ **ドライランモード OFF** — アクションが実際のデータに書き込みます。", icon=None)

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 ダッシュボード",
    "🔧 ワークフロー",
    "📋 テンプレート",
    "📜 実行ログ",
    "📝 レポート",
    "⚙️ 設定",
])

# ══════════════════════════════════════════════════════════════════════════════
# Tab 1 — Dashboard
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    try:
        from src.factories.automation.workflow_manager import get_workflow_summary, get_enabled_workflows
        from src.factories.automation.automation_reporter import get_run_summary

        wf_summary  = get_workflow_summary()
        run_summary = get_run_summary()
        enabled_wfs = get_enabled_workflows()
    except Exception as e:
        st.error(f"データ読み込みエラー: {e}")
        wf_summary  = {"total": 0, "enabled": 0, "disabled": 0, "total_runs": 0}
        run_summary = {"total_runs": 0, "triggered": 0, "successful": 0,
                       "dry_run_count": 0, "real_count": 0, "last_run": "—"}
        enabled_wfs = []

    # Metrics row
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("ワークフロー数",   wf_summary["total"])
    c2.metric("有効",             wf_summary["enabled"])
    c3.metric("無効",             wf_summary["disabled"])
    c4.metric("総実行回数",       run_summary["total_runs"])
    c5.metric("成功アクション",   run_summary["successful"])
    c6.metric("ドライラン実行",   run_summary["dry_run_count"])

    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("有効なワークフロー")
        if enabled_wfs:
            from src.factories.automation.automation_rules import (
                TRIGGER_LABELS, TRIGGER_ICONS, ACTION_LABELS, ACTION_ICONS
            )
            for wf in enabled_wfs:
                t_type = wf.get("trigger_type", "")
                a_type = wf.get("action_type", "")
                t_icon = TRIGGER_ICONS.get(t_type, "🔄")
                a_icon = ACTION_ICONS.get(a_type, "✅")
                with st.container(border=True):
                    st.markdown(
                        f"**{wf['name']}**  \n"
                        f"{t_icon} {TRIGGER_LABELS.get(t_type, t_type)} → "
                        f"{a_icon} {ACTION_LABELS.get(a_type, a_type)}  \n"
                        f"実行: {wf.get('run_count', 0)} 回  |  最終: {wf.get('last_run', '未実行') or '未実行'}"
                    )
        else:
            st.info("有効なワークフローがありません。「ワークフロー」タブで有効化してください。")

    with col_right:
        st.subheader("クイック実行")
        st.caption("ドライランモードで全ワークフローをテスト実行します。")
        if st.button("▶️ 全ワークフロー実行（ドライラン）", use_container_width=True):
            try:
                from src.factories.automation.automation_runner import run_all_enabled
                results = run_all_enabled(dry_run=True)
                fired = sum(1 for r in results if r.get("trigger_fired"))
                st.success(f"完了: {len(results)} 件実行 / {fired} 件トリガー発火")
                for r in results:
                    icon = "✅" if r.get("trigger_fired") else "⏭️"
                    st.write(f"{icon} {r['workflow_name']}: {r['trigger_reason']}")
            except Exception as e:
                st.error(f"実行エラー: {e}")

        st.divider()

        # Recent runs
        st.subheader("直近の実行")
        try:
            from src.factories.automation.automation_reporter import get_run_history
            recent = get_run_history(limit=5)
            if recent:
                for r in recent:
                    fired_icon = "🔥" if r.get("trigger_fired") else "💤"
                    dry_badge  = "DRY" if r.get("dry_run") else "REAL"
                    ts         = r.get("timestamp", "")[:16].replace("T", " ")
                    st.write(f"{fired_icon} `{dry_badge}` {ts}  \n{r.get('workflow_name', '')} — {r.get('trigger_reason', '')}")
            else:
                st.caption("実行履歴なし")
        except Exception:
            st.caption("実行履歴を読み込めませんでした")

# ══════════════════════════════════════════════════════════════════════════════
# Tab 2 — Workflow Management
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    try:
        from src.factories.automation.workflow_manager import (
            get_all_workflows, toggle_enabled, delete_workflow, create_workflow
        )
        from src.factories.automation.automation_rules import (
            ALL_TRIGGER_TYPES, TRIGGER_LABELS, TRIGGER_ICONS,
            ALL_ACTION_TYPES,  ACTION_LABELS,  ACTION_ICONS,
        )
        workflows = get_all_workflows()
    except Exception as e:
        st.error(f"読み込みエラー: {e}")
        workflows = []

    st.subheader(f"ワークフロー一覧 ({len(workflows)} 件)")

    if workflows:
        for wf in workflows:
            t_type = wf.get("trigger_type", "")
            a_type = wf.get("action_type", "")
            enabled = wf.get("enabled", False)
            with st.container(border=True):
                c_name, c_trigger, c_action, c_toggle, c_delete = st.columns([3, 2, 2, 1, 1])
                with c_name:
                    badge = "🟢" if enabled else "⭕"
                    st.markdown(f"{badge} **{wf['name']}**  \n{wf.get('description', '')[:60]}")
                with c_trigger:
                    t_icon = TRIGGER_ICONS.get(t_type, "🔄")
                    st.write(f"{t_icon} {TRIGGER_LABELS.get(t_type, t_type)}")
                with c_action:
                    a_icon = ACTION_ICONS.get(a_type, "✅")
                    st.write(f"{a_icon} {ACTION_LABELS.get(a_type, a_type)}")
                with c_toggle:
                    label = "無効化" if enabled else "有効化"
                    if st.button(label, key=f"toggle_{wf['workflow_id']}"):
                        ok, msg, _ = toggle_enabled(wf["workflow_id"])
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                with c_delete:
                    if st.button("削除", key=f"del_{wf['workflow_id']}"):
                        ok, msg = delete_workflow(wf["workflow_id"])
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
    else:
        st.info("ワークフローがありません。下のフォームから作成するか、テンプレートをインストールしてください。")

    st.divider()
    st.subheader("新規ワークフロー作成")
    with st.form("create_workflow_form"):
        wf_name = st.text_input("ワークフロー名", placeholder="例: 記事公開 → SNS下書き")
        wf_desc = st.text_input("説明", placeholder="（任意）このワークフローの目的")
        col_t, col_a = st.columns(2)
        with col_t:
            t_sel = st.selectbox("トリガー",
                options=list(ALL_TRIGGER_TYPES),
                format_func=lambda x: f"{TRIGGER_ICONS.get(x, '')} {TRIGGER_LABELS.get(x, x)}")
        with col_a:
            a_sel = st.selectbox("アクション",
                options=list(ALL_ACTION_TYPES),
                format_func=lambda x: f"{ACTION_ICONS.get(x, '')} {ACTION_LABELS.get(x, x)}")
        wf_enabled = st.checkbox("すぐに有効化する", value=False)
        if st.form_submit_button("作成", type="primary"):
            if wf_name.strip():
                try:
                    new_wf = create_workflow(
                        name=wf_name.strip(),
                        description=wf_desc.strip(),
                        trigger_type=t_sel,
                        trigger_config={},
                        action_type=a_sel,
                        action_config={},
                        enabled=wf_enabled,
                    )
                    st.success(f"作成しました: {new_wf['name']}")
                    st.rerun()
                except Exception as e:
                    st.error(f"作成エラー: {e}")
            else:
                st.warning("ワークフロー名を入力してください")

# ══════════════════════════════════════════════════════════════════════════════
# Tab 3 — Templates
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("組み込みワークフローテンプレート")
    st.caption("テンプレートをインストールすると、設定済みのワークフローが追加されます。デフォルトでは有効化されていません。")

    try:
        from src.factories.automation.automation_rules import (
            WORKFLOW_TEMPLATES, TRIGGER_LABELS, TRIGGER_ICONS, ACTION_LABELS, ACTION_ICONS
        )
        from src.factories.automation.workflow_manager import create_workflow, get_all_workflows
        existing_ids = {w["workflow_id"] for w in get_all_workflows()}
    except Exception as e:
        st.error(f"読み込みエラー: {e}")
        WORKFLOW_TEMPLATES = []
        existing_ids = set()

    for tpl in WORKFLOW_TEMPLATES:
        t_type = tpl.get("trigger_type", "")
        a_type = tpl.get("action_type", "")
        with st.container(border=True):
            col_info, col_btn = st.columns([4, 1])
            with col_info:
                st.markdown(
                    f"**{tpl['name']}**  \n"
                    f"{tpl.get('description', '')}  \n"
                    f"{TRIGGER_ICONS.get(t_type, '')} {TRIGGER_LABELS.get(t_type, t_type)} → "
                    f"{ACTION_ICONS.get(a_type, '')} {ACTION_LABELS.get(a_type, a_type)}"
                )
            with col_btn:
                already = tpl["workflow_id"] in existing_ids
                if already:
                    st.success("インストール済み", icon="✅")
                else:
                    if st.button("インストール", key=f"install_{tpl['workflow_id']}"):
                        try:
                            create_workflow(
                                name=tpl["name"],
                                description=tpl.get("description", ""),
                                trigger_type=tpl["trigger_type"],
                                trigger_config=tpl.get("trigger_config", {}),
                                action_type=tpl["action_type"],
                                action_config=tpl.get("action_config", {}),
                                enabled=False,
                            )
                            st.success("インストールしました！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"インストールエラー: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# Tab 4 — Run Log
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("実行ログ")

    try:
        from src.factories.automation.automation_reporter import get_run_history
        from src.factories.automation.automation_runner import run_workflow, run_all_enabled

        # Filter controls
        col_filter, col_wf, col_run = st.columns([2, 2, 1])
        with col_filter:
            show_dry  = st.checkbox("ドライラン実行を表示", value=True)
            show_real = st.checkbox("実際の実行を表示",     value=True)
        with col_wf:
            run_all_dry = st.button("▶️ 全実行（ドライラン）", use_container_width=True)
        with col_run:
            limit_n = st.number_input("表示件数", min_value=5, max_value=200, value=30, step=5)

        if run_all_dry:
            results = run_all_enabled(dry_run=True)
            st.success(f"{len(results)} 件実行完了")
            st.rerun()

        runs = get_run_history(limit=int(limit_n))
        if not show_dry:
            runs = [r for r in runs if not r.get("dry_run")]
        if not show_real:
            runs = [r for r in runs if r.get("dry_run")]

        if runs:
            for r in runs:
                fired_icon  = "🔥" if r.get("trigger_fired") else "💤"
                success_ico = "✅" if r.get("success") else "❌"
                dry_badge   = "🛡️ DRY" if r.get("dry_run") else "⚡ REAL"
                ts          = r.get("timestamp", "")[:16].replace("T", " ")
                action_desc = ""
                if r.get("action_result"):
                    action_desc = r["action_result"].get("description", "")[:60]
                with st.expander(
                    f"{fired_icon} {success_ico} `{dry_badge}` {ts} — {r.get('workflow_name', '')}",
                    expanded=False,
                ):
                    st.write(f"**トリガー:** {r.get('trigger_reason', '—')}")
                    st.write(f"**アクション:** {action_desc or '（未実行）'}")
                    st.write(f"**Run ID:** `{r.get('run_id', '—')}`")
        else:
            st.info("実行ログがありません。ダッシュボードからワークフローを実行してください。")

    except Exception as e:
        st.error(f"実行ログ読み込みエラー: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# Tab 5 — Report
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.subheader("自動化レポート")

    try:
        from src.factories.automation.workflow_manager   import get_workflow_summary
        from src.factories.automation.automation_reporter import (
            generate_automation_report, export_automation_report,
            get_run_history, get_run_summary, list_reports
        )

        wf_sum  = get_workflow_summary()
        run_sum = get_run_summary()
        runs    = get_run_history(limit=20)

        col_gen, col_export = st.columns([2, 1])
        with col_gen:
            if st.button("📝 レポートを生成", type="primary", use_container_width=True):
                content = generate_automation_report(runs, wf_sum, run_sum)
                st.session_state["auto_report_content"] = content
                st.success("レポートを生成しました")

        with col_export:
            if st.button("💾 エクスポート (Markdown)", use_container_width=True):
                content = st.session_state.get(
                    "auto_report_content",
                    generate_automation_report(runs, wf_sum, run_sum)
                )
                path = export_automation_report(content)
                st.success(f"保存しました: {path.name}")

        if "auto_report_content" in st.session_state:
            st.divider()
            st.markdown(st.session_state["auto_report_content"])

        # Past reports
        past = list_reports()
        if past:
            st.divider()
            st.subheader("過去のレポート")
            for p in past[:10]:
                st.write(f"📄 {p.name}")

    except Exception as e:
        st.error(f"レポートエラー: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# Tab 6 — Settings
# ══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.subheader("自動化設定")
    st.caption("⚠️ ドライランモードをOFFにすると、ワークフローのアクションが実際のデータに書き込まれます。")

    settings = _load_settings()
    with st.form("settings_form"):
        new_dry = st.toggle(
            "ドライランモード（デフォルト）",
            value=settings.get("dry_run_default", True),
            help="ONにするとアクションはシミュレートのみ。OFFにすると実際にデータが作成されます。",
        )
        new_max_runs = st.number_input(
            "最大実行ログ保存数",
            min_value=50, max_value=500, value=settings.get("max_runs", 200), step=50,
        )
        new_log_days = st.number_input(
            "ログ保持日数",
            min_value=7, max_value=365, value=settings.get("log_retention_days", 30), step=1,
        )
        new_auto_start = st.toggle(
            "起動時に自動実行",
            value=settings.get("auto_run_on_startup", False),
            help="アプリ起動時に有効なワークフローを自動実行します。",
        )
        if st.form_submit_button("設定を保存", type="primary"):
            settings["dry_run_default"]      = new_dry
            settings["max_runs"]             = int(new_max_runs)
            settings["log_retention_days"]   = int(new_log_days)
            settings["auto_run_on_startup"]  = new_auto_start
            settings["meta"]["updated_at"]   = datetime.now().strftime("%Y-%m-%d")
            _save_settings(settings)
            st.success("設定を保存しました")
            st.rerun()

    st.divider()
    st.subheader("安全性ガイドライン")
    with st.container(border=True):
        st.markdown("""
**自動化工場の安全原則:**

- 🛡️ 全アクションはドラフト/ペンディング状態で作成 — 自動公開なし
- 🔒 外部APIへのアクセスなし — 完全ローカル動作
- 📋 既存データの上書きなし — 常に新規追加のみ
- ✍️ `_automation_source: true` フラグで自動生成アイテムを識別可能
- 🔄 全実行は automation_runs.json に記録 — 監査証跡あり
- ❌ 削除・上書きアクションなし
        """)
