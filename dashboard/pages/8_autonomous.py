"""Autonomous — AIOS 自律改善コントロールパネル。

Goal 管理 / Queue 管理 / サイクル実行 をこの1ページで行う。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

st.set_page_config(page_title="Autonomous | AIOS", page_icon="🤖", layout="wide")

@st.cache_resource(ttl=0)
def _load():
    from src.core.kernel import get_kernel
    from src.ai_agents.registry import get_agent_registry
    get_agent_registry().auto_load()
    k = get_kernel()
    from src.autonomous.goal_manager import get_goal_manager
    from src.autonomous.queue_manager import get_autonomous_queue, TaskStatus
    return k, get_goal_manager(), get_autonomous_queue(), TaskStatus

k, gm, queue, TS = _load()

st.title("🤖 Autonomous Improvement")
st.caption("AIOS が自分で改善サイクルを回す — Goal 管理 / Queue 管理 / サイクル実行")

# ── タブ ──────────────────────────────────────────────────────────
tab_cycle, tab_goal, tab_queue = st.tabs(["▶ 改善サイクル", "🎯 Goal", "📋 Queue"])

# ═══════════════════════════════════════════════════════════════════
# TAB 1: 改善サイクル
# ═══════════════════════════════════════════════════════════════════
with tab_cycle:
    st.subheader("改善サイクル実行")

    col_a, col_b, col_c = st.columns(3)
    period_days  = col_a.number_input("分析対象 (日)", value=30, min_value=1, max_value=365)
    max_actions  = col_b.number_input("最大アクション数", value=5, min_value=1, max_value=20)
    dry_run      = col_c.checkbox("Dry Run (キュー登録のみ)", value=True)
    auto_approve = st.checkbox("AI スコア ≥ 8.5 で自動承認 (Dry Run=false 時のみ)", value=False)

    st.info(
        "**Dry Run ON (推奨):** 分析・計画・キュー登録のみ。Patch は生成しません。\n"
        "**Dry Run OFF:** 最優先タスクの Patch まで自動生成します。"
    )

    if st.button("▶ 改善サイクル実行", type="primary"):
        with st.spinner("自律改善サイクルを実行中..."):
            from src.autonomous import run_improvement_cycle
            result = run_improvement_cycle(
                period_days  = int(period_days),
                max_actions  = int(max_actions),
                auto_approve = auto_approve,
                dry_run      = dry_run,
            )
        st.success(
            f"完了: 候補 {result['candidates']} 件 / "
            f"アクション {result['planned_actions']} 件 / "
            f"登録 {len(result.get('enqueued_tasks', []))} タスク"
        )
        st.json(result)

    st.divider()

    # Workflow 経由のサイクル実行
    st.subheader("autonomous.run_cycle Workflow 実行")
    col1, col2 = st.columns(2)
    p2 = col1.number_input("分析日数", value=30, min_value=1)
    m2 = col2.number_input("最大アクション", value=5, min_value=1)
    if st.button("Workflow で実行"):
        with st.spinner("autonomous.run_cycle 実行中..."):
            status = k.run_workflow("autonomous.run_cycle", {
                "period_days": str(p2),
                "max_actions": str(m2),
            })
        ctx = getattr(status, "context", {})
        report = ctx.get("cycle_report", "")
        if report:
            st.markdown("### サイクルレポート")
            st.markdown(report)
        out_files = list(Path("output/autonomous").glob("cycle_report_*.md")) if Path("output/autonomous").exists() else []
        if out_files:
            latest = max(out_files, key=lambda f: f.stat().st_mtime)
            with st.expander("保存されたレポート"):
                st.download_button("ダウンロード", latest.read_text(encoding="utf-8"), file_name=latest.name)

# ═══════════════════════════════════════════════════════════════════
# TAB 2: Goal 管理
# ═══════════════════════════════════════════════════════════════════
with tab_goal:
    from src.autonomous.goal_manager import GoalLevel, GoalStatus

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("現在の目標")
        for level, label, icon in [
            (GoalLevel.LONG,  "長期目標", "🌟"),
            (GoalLevel.MID,   "中期目標", "📌"),
            (GoalLevel.SHORT, "短期タスク", "✅"),
        ]:
            goals = gm.get_active(level)
            st.markdown(f"#### {icon} {label}")
            if not goals:
                st.caption("(目標なし)")
            for g in goals:
                with st.expander(f"[{g.completion_pct:.0f}%] {g.title} (P{g.priority})", expanded=False):
                    st.write(g.description or "(説明なし)")
                    if g.success_criteria:
                        st.markdown("**成功条件:**")
                        for sc in g.success_criteria:
                            st.markdown(f"- {sc}")
                    new_pct = st.slider(
                        "進捗", 0, 100, int(g.completion_pct), key=f"pct_{g.goal_id}"
                    )
                    col_s1, col_s2, col_s3 = st.columns(3)
                    if col_s1.button("更新", key=f"upd_{g.goal_id}"):
                        gm.update_progress(g.goal_id, float(new_pct))
                        st.rerun()
                    if col_s2.button("完了", key=f"done_{g.goal_id}"):
                        gm.complete(g.goal_id)
                        st.rerun()
                    if col_s3.button("削除", key=f"del_{g.goal_id}"):
                        gm.delete(g.goal_id)
                        st.rerun()

    with col_right:
        st.subheader("目標を追加")
        with st.form("add_goal"):
            g_title  = st.text_input("タイトル *")
            g_level  = st.selectbox("レベル", [GoalLevel.SHORT, GoalLevel.MID, GoalLevel.LONG],
                                    format_func=lambda l: {"long":"長期","mid":"中期","short":"短期"}[l])
            g_desc   = st.text_area("説明", height=80)
            g_prio   = st.slider("優先度", 1, 10, 5)
            g_date   = st.text_input("目標日 (YYYY-MM-DD)", "")
            g_crit   = st.text_area("成功条件 (1行1件)", height=60)
            if st.form_submit_button("追加"):
                if g_title:
                    criteria = [c.strip() for c in g_crit.splitlines() if c.strip()]
                    gm.add(
                        title            = g_title,
                        level            = g_level,
                        description      = g_desc,
                        priority         = g_prio,
                        target_date      = g_date or None,
                        success_criteria = criteria,
                    )
                    st.success("追加しました")
                    st.rerun()
                else:
                    st.error("タイトルを入力してください")

        st.divider()
        with st.expander("完了・キャンセル済み"):
            all_goals = gm.list_all()
            done = [g for g in all_goals if g.status in (GoalStatus.COMPLETED, GoalStatus.CANCELLED)]
            for g in done[-10:]:
                icon = "✅" if g.status == GoalStatus.COMPLETED else "❌"
                st.markdown(f"{icon} ~~{g.title}~~")

# ═══════════════════════════════════════════════════════════════════
# TAB 3: Queue 管理
# ═══════════════════════════════════════════════════════════════════
with tab_queue:
    stats = queue.stats()
    cols  = st.columns(5)
    for i, (label, key) in enumerate([
        ("待機中", TS.PENDING), ("実行中", TS.RUNNING),
        ("Patch待ち", TS.PATCH_READY), ("承認済み", TS.APPROVED),
        ("完了", TS.MERGED),
    ]):
        cols[i].metric(label, stats.get(key, 0))

    st.divider()

    # フィルター
    status_filter = st.selectbox(
        "ステータスフィルター", ["全て", TS.PENDING, TS.PATCH_READY, TS.APPROVED, TS.MERGED, TS.REJECTED],
    )
    tasks = queue.list_all(None if status_filter == "全て" else status_filter)

    if not tasks:
        st.info("タスクがありません。「改善サイクル」タブから実行してください。")
    else:
        for t in tasks:
            status_icon = {
                TS.PENDING:"⏳", TS.RUNNING:"🔄", TS.PATCH_READY:"📄",
                TS.APPROVED:"✅", TS.MERGED:"🎉", TS.REJECTED:"❌",
                TS.FAILED:"🔴", TS.CANCELLED:"⚫",
            }.get(t.status, "❓")
            with st.expander(f"{status_icon} [{t.status}] {t.title} (P{t.priority})", expanded=False):
                st.markdown(f"**対象:** `{t.target}` | **Workflow:** `{t.workflow_to_run}`")
                st.markdown(f"**説明:** {t.description}")
                st.markdown(f"**作成:** {t.created_at} | **ソース:** {t.source}")

                if t.review_summary:
                    score_icon = "🟢" if (t.review_score or 0) >= 8.5 else "🟡" if (t.review_score or 0) >= 6 else "🔴"
                    st.markdown(f"{score_icon} **レビュースコア:** {t.review_score:.1f}/10 — {t.review_summary}")

                if t.patch_path:
                    st.markdown(f"**Patch:** `{t.patch_path}`")

                # ボタン
                bcols = st.columns(4)
                if t.status == TS.PENDING:
                    if bcols[0].button("キャンセル", key=f"cancel_{t.task_id}"):
                        queue.cancel(t.task_id)
                        st.rerun()
                if t.status == TS.PATCH_READY:
                    if bcols[0].button("✅ 承認", key=f"approve_{t.task_id}", type="primary"):
                        from src.autonomous.safe_mode import SafeMode
                        SafeMode().approve(t.task_id, "human")
                        st.rerun()
                    if bcols[1].button("❌ 却下", key=f"reject_{t.task_id}"):
                        queue.reject(t.task_id, "手動却下")
                        st.rerun()
                if t.status == TS.APPROVED:
                    if bcols[0].button("🎉 Merge", key=f"merge_{t.task_id}", type="primary"):
                        from src.autonomous.safe_mode import SafeMode
                        result = SafeMode().merge(t.task_id)
                        st.success(f"Merge 完了: {result.approved_dir}")
                        st.rerun()

    st.divider()

    # 手動タスク追加
    with st.expander("手動でタスクを追加"):
        with st.form("add_task"):
            t_title = st.text_input("タイトル *")
            t_wf    = st.text_input("実行 Workflow", "dev.code_review")
            t_target= st.text_input("対象 (workflow_name/agent_id/etc.)")
            t_desc  = st.text_area("説明", height=60)
            t_prio  = st.slider("優先度", 1, 10, 5)
            t_ctx   = st.text_area("context JSON", "{}", height=60)
            if st.form_submit_button("追加"):
                import json
                try:
                    ctx = json.loads(t_ctx)
                    queue.enqueue(
                        title=t_title, task_type="custom",
                        workflow_to_run=t_wf, target=t_target,
                        description=t_desc, priority=t_prio,
                        context=ctx, source="manual",
                    )
                    st.success("タスクを追加しました")
                    st.rerun()
                except Exception as e:
                    st.error(f"エラー: {e}")
