"""
Approval Center — Creator Factory OS v5.1
Human-approval gateway for all OS actions.
Never executes commands. Human approval required for every action.
"""
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.approval.approval_queue import (
    get_pending, get_history, add_item, approve_item,
    reject_item, delete_pending, get_summary,
)
from src.approval.approval_models import STATUS_ICONS, RISK_ICONS, SOURCE_LABELS, RISK_LEVELS
from src.approval.risk_analyzer import analyze_risk, get_risk_color
from src.approval.command_preview import preview_action, get_short_summary

st.set_page_config(page_title="Approval Center | Creator Factory OS", page_icon="✅", layout="wide")
st.title("✅ Approval Center")
st.caption("人間承認ゲートウェイ — すべてのアクションに人間の承認が必要です。自動実行なし。v5.1")

# ── Live Inbox aggregation ─────────────────────────────────────────────────────

def _aggregate_live_inbox() -> list[dict]:
    """Collect pending-review items from AI CEO, Automation, DevStudio. Read-only."""
    items: list[dict] = []

    try:
        from src.aiceo.executive_engine import collect_snapshot as _snap
        from src.aiceo.recommendation_engine import generate_recommendations as _recs
        from src.aiceo.risk_engine import identify_risks as _risks
        from src.aiceo.opportunity_engine import identify_opportunities as _opps
        from src.aiceo.priority_engine import score_priorities as _pris
        _s = _snap()
        _ri = _risks(_s)
        _op = _opps(_s)
        _pr = _pris(_s)
        for rec in _recs(_s, _ri, _op, _pr)[:5]:
            risk = "medium" if rec.get("confidence", 50) >= 60 else "low"
            items.append({
                "_inbox": True,
                "title":           rec.get("title", "(AI CEO推奨)"),
                "source":          "aiceo",
                "command_summary": rec.get("action", "詳細はAI CEOページを確認"),
                "expected_impact": rec.get("expected_impact", ""),
                "estimated_risk":  risk,
                "affected_files":  [],
                "related_id":      rec.get("title", ""),
                "notes":           f"Confidence: {rec.get('confidence', 0)}%",
            })
    except Exception:
        pass

    try:
        from src.factories.automation.workflow_manager import get_all_workflows as _wfs
        for wf in _wfs():
            if not wf.get("enabled", True):
                items.append({
                    "_inbox": True,
                    "title":           f"ワークフロー有効化リクエスト: {wf.get('name', '')}",
                    "source":          "automation",
                    "command_summary": f"ワークフロー '{wf.get('name', '')}' を有効化する",
                    "expected_impact": wf.get("description", ""),
                    "estimated_risk":  "low",
                    "affected_files":  [],
                    "related_id":      wf.get("workflow_id", ""),
                    "notes":           f"トリガー: {wf.get('trigger', '')}",
                })
    except Exception:
        pass

    try:
        from src.devstudio.decision_log_manager import get_all_decisions as _decs
        for dec in _decs():
            if dec.get("status") == "open":
                items.append({
                    "_inbox": True,
                    "title":           f"決定リクエスト: {dec.get('theme', '')}",
                    "source":          "devstudio",
                    "command_summary": dec.get("decision", ""),
                    "expected_impact": dec.get("expected_effect", ""),
                    "estimated_risk":  "low" if dec.get("impact") == "low" else "medium",
                    "affected_files":  [],
                    "related_id":      dec.get("decision_id", ""),
                    "notes":           f"理由: {dec.get('reason', '')}",
                })
    except Exception:
        pass

    return items


summary = get_summary()

# ── Header metrics ─────────────────────────────────────────────────────────────
hm1, hm2, hm3, hm4 = st.columns(4)
hm1.metric("⏳ 承認待ち",     summary["pending_count"])
hm2.metric("🔴 高リスク",     summary["high_risk_count"])
hm3.metric("✅ 承認済み",     summary["approved_count"])
hm4.metric("❌ 却下済み",     summary["rejected_count"])

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_pending, tab_approved, tab_rejected, tab_submit, tab_summary = st.tabs([
    "📋 Pending",
    "✅ Approved",
    "❌ Rejected",
    "➕ New Request",
    "📊 Summary",
])

# ── Tab 1: Pending ─────────────────────────────────────────────────────────────
with tab_pending:
    pending_items = get_pending()

    # Stored pending items
    if pending_items:
        st.markdown(f"#### キュー内 承認待ちアクション ({len(pending_items)} 件)")
        for item in pending_items:
            risk_analysis = analyze_risk(item)
            risk_lv = risk_analysis["risk_level"]
            risk_icon = RISK_ICONS.get(risk_lv, "⚪")
            source_label = SOURCE_LABELS.get(item.get("source", ""), item.get("source", ""))
            created = item.get("created_at", "")[:10]

            with st.expander(
                f"{risk_icon} {item.get('title', '(タイトルなし)')} — {source_label} ({created})",
                expanded=False,
            ):
                preview_col, action_col = st.columns([3, 1])
                with preview_col:
                    st.markdown(preview_action(item))
                    if risk_analysis.get("factors"):
                        st.caption("リスク要因: " + " / ".join(risk_analysis["factors"]))

                with action_col:
                    st.markdown(f"**リスク**: {risk_icon} {risk_lv.upper()}")
                    st.markdown(f"**ソース**: {source_label}")
                    st.markdown(f"**作成日**: {created}")

                    notes_key = f"notes_{item['approval_id']}"
                    notes_val = st.text_input("承認メモ (任意)", key=notes_key)

                    col_a, col_r = st.columns(2)
                    with col_a:
                        if st.button("✅ 承認", key=f"approve_{item['approval_id']}",
                                     type="primary", use_container_width=True):
                            approve_item(item["approval_id"], notes_val)
                            st.success("承認しました。")
                            st.rerun()
                    with col_r:
                        if st.button("❌ 却下", key=f"reject_{item['approval_id']}",
                                     use_container_width=True):
                            reject_item(item["approval_id"], notes_val)
                            st.warning("却下しました。")
                            st.rerun()

                    if st.button("🗑️ 削除", key=f"delete_{item['approval_id']}",
                                 use_container_width=True):
                        delete_pending(item["approval_id"])
                        st.rerun()
        st.divider()
    else:
        st.info("承認待ちのアイテムはありません。")

    # Live Inbox
    st.markdown("#### 📥 Live Inbox — 各モジュールからの提案")
    st.caption("以下は AI CEO / 自動化工場 / Development Studio からのリアルタイム提案です。"
               "「キューに追加」ボタンで承認待ちリストに登録できます。")

    live_items = _aggregate_live_inbox()
    if live_items:
        for idx, item in enumerate(live_items):
            risk_icon = RISK_ICONS.get(item.get("estimated_risk", "low"), "🟡")
            source_label = SOURCE_LABELS.get(item.get("source", ""), item.get("source", ""))
            with st.expander(
                f"{risk_icon} [{source_label}] {item.get('title', '')}",
                expanded=False,
            ):
                st.markdown(f"**内容**: {item.get('command_summary', '')}")
                st.markdown(f"**期待効果**: {item.get('expected_impact', '')}")
                if item.get("notes"):
                    st.caption(item["notes"])
                if st.button("📥 キューに追加", key=f"inbox_{idx}_{item.get('source', '')}",
                             use_container_width=False):
                    add_item(
                        title=item["title"],
                        source=item["source"],
                        command_summary=item["command_summary"],
                        expected_impact=item["expected_impact"],
                        estimated_risk=item["estimated_risk"],
                        affected_files=item.get("affected_files", []),
                        related_id=item.get("related_id", ""),
                        notes=item.get("notes", ""),
                    )
                    st.success("キューに追加しました。")
                    st.rerun()
    else:
        st.caption("現在、ライブインボックスにアイテムはありません。")

# ── Tab 2: Approved History ────────────────────────────────────────────────────
with tab_approved:
    history = get_history(limit=50)
    approved = [i for i in history if i.get("status") == "approved"]
    st.markdown(f"#### 承認済みアクション ({len(approved)} 件)")
    if approved:
        for item in approved:
            source_label = SOURCE_LABELS.get(item.get("source", ""), item.get("source", ""))
            reviewed = item.get("reviewed_at", "")[:10]
            with st.expander(
                f"✅ {item.get('title', '')} — {source_label} (承認: {reviewed})",
                expanded=False,
            ):
                st.markdown(f"**内容**: {item.get('command_summary', '')}")
                st.markdown(f"**期待効果**: {item.get('expected_impact', '')}")
                if item.get("notes"):
                    st.caption(f"メモ: {item['notes']}")
    else:
        st.info("承認済みのアイテムはありません。")

# ── Tab 3: Rejected History ────────────────────────────────────────────────────
with tab_rejected:
    history = get_history(limit=50)
    rejected = [i for i in history if i.get("status") == "rejected"]
    st.markdown(f"#### 却下済みアクション ({len(rejected)} 件)")
    if rejected:
        for item in rejected:
            source_label = SOURCE_LABELS.get(item.get("source", ""), item.get("source", ""))
            reviewed = item.get("reviewed_at", "")[:10]
            with st.expander(
                f"❌ {item.get('title', '')} — {source_label} (却下: {reviewed})",
                expanded=False,
            ):
                st.markdown(f"**内容**: {item.get('command_summary', '')}")
                if item.get("notes"):
                    st.caption(f"却下理由: {item['notes']}")
    else:
        st.info("却下済みのアイテムはありません。")

# ── Tab 4: New Request ─────────────────────────────────────────────────────────
with tab_submit:
    st.markdown("#### ➕ 新規承認リクエストを登録")
    st.caption("手動で承認リクエストをキューに追加します。実行はされません。")

    with st.form("new_approval_request"):
        nr_title = st.text_input("タイトル *", placeholder="例: SNS工場の自動投稿を有効化")
        nr_summary = st.text_area("実行内容の説明 *", placeholder="何をするのか、具体的に記述")
        nr_impact = st.text_area("期待される効果 *", placeholder="承認後にどんな変化が起きるか")
        nr_risk = st.selectbox("リスクレベル", RISK_LEVELS, index=1)
        nr_files = st.text_input("影響ファイル (カンマ区切り、任意)", placeholder="config/sns_posts.json, pages/19_SNS_Factory.py")
        nr_notes = st.text_area("備考 (任意)")

        submitted = st.form_submit_button("📥 キューに追加", type="primary", use_container_width=True)
        if submitted:
            if not nr_title.strip() or not nr_summary.strip() or not nr_impact.strip():
                st.error("タイトル・実行内容・期待効果は必須です。")
            else:
                affected = [f.strip() for f in nr_files.split(",") if f.strip()] if nr_files else []
                add_item(
                    title=nr_title.strip(),
                    source="manual",
                    command_summary=nr_summary.strip(),
                    expected_impact=nr_impact.strip(),
                    estimated_risk=nr_risk,
                    affected_files=affected,
                    notes=nr_notes.strip(),
                )
                st.success("✅ 承認リクエストをキューに追加しました。")
                st.rerun()

# ── Tab 5: Summary ─────────────────────────────────────────────────────────────
with tab_summary:
    st.markdown("#### 📊 Approval Center サマリー")

    all_history = get_history(limit=100)
    all_pending = get_pending()
    live_inbox = _aggregate_live_inbox()

    sm1, sm2, sm3, sm4, sm5 = st.columns(5)
    sm1.metric("⏳ 承認待ち",     len(all_pending))
    sm2.metric("📥 Live Inbox",   len(live_inbox))
    sm3.metric("✅ 承認済み",     sum(1 for i in all_history if i.get("status") == "approved"))
    sm4.metric("❌ 却下済み",     sum(1 for i in all_history if i.get("status") == "rejected"))
    sm5.metric("📋 総レビュー数", len(all_history))

    st.divider()

    # Source breakdown
    st.markdown("**ソース別 内訳**")
    source_counts: dict[str, int] = {}
    for item in all_pending + all_history:
        src = SOURCE_LABELS.get(item.get("source", ""), item.get("source", ""))
        source_counts[src] = source_counts.get(src, 0) + 1
    for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
        st.markdown(f"- **{src}**: {cnt} 件")

    # Risk breakdown
    if all_pending:
        st.divider()
        st.markdown("**保留中アイテムのリスク分布**")
        risk_counts: dict[str, int] = {}
        for item in all_pending:
            r = item.get("estimated_risk", "low")
            risk_counts[r] = risk_counts.get(r, 0) + 1
        for level in ["high", "medium", "low", "none"]:
            cnt = risk_counts.get(level, 0)
            if cnt:
                icon = RISK_ICONS.get(level, "⚪")
                st.markdown(f"- {icon} **{level.upper()}**: {cnt} 件")

    st.divider()
    st.caption(
        "⚠️ Approval Center は表示専用です。「承認」ボタンはキューの状態を更新するのみで、"
        "いかなるコマンドも自動実行しません。"
    )
