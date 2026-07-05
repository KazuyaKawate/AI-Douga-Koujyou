"""Review & Approval — Patch レビュー・承認・Merge・履歴ページ。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

st.set_page_config(page_title="Review | AIOS", page_icon="🔍", layout="wide")

@st.cache_resource(ttl=0)
def _load():
    from src.ai_agents.registry import get_agent_registry
    get_agent_registry().auto_load()
    from src.core.kernel import get_kernel
    from src.autonomous.queue_manager import get_autonomous_queue, TaskStatus
    from src.autonomous.safe_mode import SafeMode
    k = get_kernel()
    return k, get_autonomous_queue(), SafeMode(), TaskStatus

k, queue, safe_mode, TS = _load()

st.title("🔍 Patch Review & Approval")
st.caption("生成された Patch を AI レビュー → 承認 → Merge する")

tab_review, tab_approval, tab_history = st.tabs(["🔍 Patch レビュー", "✅ 承認管理", "📜 適用履歴"])

# ═══════════════════════════════════════════════════════════════════
with tab_review:
    st.subheader("Patch 生成 & AI レビュー")

    # Patch 待ちタスク
    patch_tasks = queue.list_all(TS.PATCH_READY)
    running_tasks= queue.list_all(TS.PENDING)

    # Pending タスクから Patch 生成
    if running_tasks:
        st.markdown("**待機中タスク (Patch 生成可能)**")
        for t in running_tasks:
            with st.expander(f"⏳ {t.title} — `{t.workflow_to_run}`"):
                st.markdown(f"**対象:** {t.target}  \n**説明:** {t.description}")

                col1, col2 = st.columns(2)
                if col1.button("▶ Patch 生成", key=f"gen_{t.task_id}", type="primary"):
                    with st.spinner(f"Patch 生成中: {t.workflow_to_run}..."):
                        patch = safe_mode.generate_patch(t)
                    if patch.success:
                        st.success(f"Patch 生成完了: {patch.patch_path}")
                        if patch.diff_stats:
                            st.json(patch.diff_stats)
                    else:
                        st.error(f"生成失敗: {patch.error}")
                    st.rerun()

                if col2.button("▶ Patch + AI レビュー", key=f"genrev_{t.task_id}"):
                    with st.spinner("Patch 生成中..."):
                        patch = safe_mode.generate_patch(t)
                    if patch.success:
                        with st.spinner("AI レビュー中..."):
                            review = safe_mode.review_patch(t)
                        score_icon = "🟢" if review.score >= 8.5 else "🟡" if review.score >= 6 else "🔴"
                        st.markdown(f"### {score_icon} レビュースコア: {review.score:.1f}/10")
                        st.markdown(review.summary)
                        if review.risks:
                            st.markdown("**リスク:**")
                            for r in review.risks:
                                st.markdown(f"- ⚠️ {r}")
                        if review.suggestions:
                            st.markdown("**改善提案:**")
                            for s in review.suggestions:
                                st.markdown(f"- 💡 {s}")
                        if review.auto_approve:
                            st.success("スコア ≥ 8.5 → 自動承認対象です")
                    else:
                        st.error(f"生成失敗: {patch.error}")
                    st.rerun()

    st.divider()

    # Patch 表示
    if patch_tasks:
        st.markdown("**Patch 確認 (レビュー済み)**")
        for t in patch_tasks:
            score = t.review_score or 0
            score_icon = "🟢" if score >= 8.5 else "🟡" if score >= 6 else "🔴"
            with st.expander(f"{score_icon} [{score:.1f}/10] {t.title}"):
                st.markdown(f"**レビュー:** {t.review_summary}")
                patch_text = safe_mode.get_patch_text(t.task_id)
                st.code(patch_text[:3000], language="diff")
                if len(patch_text) > 3000:
                    st.caption(f"... (表示は先頭 3000 文字。全体 {len(patch_text)} 文字)")

                col1, col2 = st.columns(2)
                if col1.button("✅ 承認", key=f"appr_{t.task_id}", type="primary"):
                    safe_mode.approve(t.task_id, "human")
                    st.rerun()
                if col2.button("❌ 却下", key=f"rej_{t.task_id}"):
                    queue.reject(t.task_id, "手動却下")
                    st.rerun()
    else:
        st.info("Patch 待ちのタスクがありません。待機中タスクから「Patch 生成」を実行してください。")

# ═══════════════════════════════════════════════════════════════════
with tab_approval:
    st.subheader("承認管理")

    approved_tasks = queue.list_all(TS.APPROVED)
    if not approved_tasks:
        st.info("承認済みタスクがありません。")
    else:
        for t in approved_tasks:
            with st.expander(f"✅ {t.title} (承認者: {t.approved_by})"):
                st.markdown(f"**対象:** {t.target}")
                st.markdown(f"**レビュースコア:** {t.review_score:.1f}/10")
                st.markdown(f"**レビューサマリー:** {t.review_summary}")
                if t.patch_path:
                    st.markdown(f"**Patch ファイル:** `{t.patch_path}`")
                    patch_text = safe_mode.get_patch_text(t.task_id)
                    with st.expander("Patch を表示"):
                        st.code(patch_text[:2000], language="diff")

                col1, col2 = st.columns(2)
                if col1.button("🎉 Merge", key=f"merge_{t.task_id}", type="primary"):
                    with st.spinner("Merge 処理中..."):
                        merge_result = safe_mode.merge(t.task_id)
                    if merge_result.success:
                        st.success(f"Merge 完了 → {merge_result.approved_dir}")
                        st.caption("実際のファイルへの適用は git apply などで手動実行してください。")
                    else:
                        st.error(f"Merge 失敗: {merge_result.error}")
                    st.rerun()
                if col2.button("取消", key=f"unapp_{t.task_id}"):
                    queue.reject(t.task_id, "承認後取消")
                    st.rerun()

# ═══════════════════════════════════════════════════════════════════
with tab_history:
    st.subheader("適用履歴 (Merged)")

    # Merged タスク
    merged_tasks = queue.list_all(TS.MERGED)
    history      = safe_mode.load_history(50)

    col1, col2 = st.columns(2)
    col1.metric("Merge 済みタスク", len(merged_tasks))
    col2.metric("履歴レコード", len(history))

    st.divider()

    if history:
        st.markdown("### 適用履歴ログ")
        import pandas as pd
        df = pd.DataFrame(history)
        st.dataframe(df[["applied_at","title","approved_by","review_score","patch_path"]], use_container_width=True)
    else:
        st.info("適用履歴がありません。")

    st.divider()

    if merged_tasks:
        st.markdown("### Merge 済みタスク")
        for t in merged_tasks:
            with st.expander(f"🎉 {t.title} — {t.completed_at}"):
                st.markdown(f"**対象:** {t.target}")
                st.markdown(f"**スコア:** {t.review_score:.1f}/10 | **承認者:** {t.approved_by}")
                if t.patch_path:
                    approved_patch = Path("data/autonomous/approved") / t.task_id / Path(t.patch_path).name
                    if approved_patch.exists():
                        st.download_button(
                            "Patch をダウンロード",
                            approved_patch.read_text(encoding="utf-8"),
                            file_name=approved_patch.name,
                            key=f"dl_{t.task_id}",
                        )
