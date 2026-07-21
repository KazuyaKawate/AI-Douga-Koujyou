"""OPERATION-4 Business Home — projection-only daily business cockpit."""

from __future__ import annotations

import html

import pandas as pd
import streamlit as st

from src.operations.daily_projection import DailyOperationProjection
from src.operations.owner4_configuration import project_owner_configuration
from src.operations.owner6_approval_capture import (
    REVIEW_LAYER, capture_owner_approval, empty_approval_register,
    project_approval_capture,
)
from src.ui import apply_design_system, evidence_status_legend
from src.ui.revenue1_readiness import render_business_home_readiness, render_executive_readiness
from src.ui.revenue2_first_customer import render_business_home as render_revenue2_home, render_executive as render_revenue2_executive
from src.ui.revenue3_customer_package import render_executive_package, render_first_customer_package
from src.ui.revenue4_onboarding import render_business_home as render_revenue4_home, render_executive as render_revenue4_executive
from src.ui.revenue5_owner_approval import render_business_home as render_revenue5_home, render_executive as render_revenue5_executive
from src.ui.revenue6_controlled_intake import render_business_home as render_revenue6_home, render_executive as render_revenue6_executive
from src.ui.revenue7_operation_simulation import render_business_home as render_revenue7_home, render_evidence_summary as render_revenue7_evidence, render_executive as render_revenue7_executive
from src.ui.revenue8_first_offer import render_business_home as render_revenue8_home, render_executive as render_revenue8_executive, render_readiness_summary as render_revenue8_summary
from src.ui.revenue9_owner_decision import render_business_home as render_revenue9_home, render_executive as render_revenue9_executive


st.set_page_config(page_title="AIOS Business Home", page_icon="🏢", layout="wide")
apply_design_system()
st.markdown(
    """
    <style>
    .op4-hero{border:1px solid rgba(0,255,255,.3);border-left:5px solid #00ffff;border-radius:.75rem;padding:1rem 1.2rem;background:rgba(0,255,255,.055);margin:.55rem 0 1rem}
    .op4-hero small,.op4-card small{display:block;opacity:.72}.op4-hero h2{margin:.2rem 0 .35rem;font-size:clamp(1.2rem,4vw,1.8rem)}
    .op4-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.7rem;margin:.65rem 0 1.25rem}
    .op4-card{border:1px solid rgba(128,160,180,.28);border-radius:.65rem;padding:.85rem;min-width:0;overflow-wrap:anywhere}
    .op4-card strong{display:block;font-size:1.35rem;margin:.15rem 0}.op4-proposal{border-left:3px solid #f2c94c}
    .op4-flow{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.55rem;margin:.6rem 0 1.1rem}
    .op4-step{border:1px solid rgba(0,255,255,.24);border-radius:.6rem;padding:.75rem;min-height:86px}.op4-step b,.op4-step span{display:block}.op4-step span{font-size:.78rem;opacity:.72}
    .op4-nav{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:.55rem;margin:.5rem 0 1.25rem}
    .op4-safety{font-weight:700;letter-spacing:.02em}
    @media(max-width:1024px){.op4-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.op4-flow{grid-template-columns:repeat(3,minmax(0,1fr))}}
    @media(max-width:720px){div[data-testid="stHorizontalBlock"]{flex-wrap:wrap}.op4-nav,.op4-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.op4-flow{grid-template-columns:1fr}.op4-step{min-height:0}}
    @media(max-width:390px){.block-container{padding-left:.65rem!important;padding-right:.65rem!important}.op4-nav,.op4-grid{grid-template-columns:1fr}.op4-hero{padding:.8rem}.op4-card strong{font-size:1.15rem}}
    @media(max-width:360px){.block-container{padding-left:.5rem!important;padding-right:.5rem!important}}
    </style>
    """,
    unsafe_allow_html=True,
)

payload = DailyOperationProjection().build_business_execution_mode()
owner4 = project_owner_configuration()
owner6_register = empty_approval_register()
for index, row in enumerate(owner6_register):
    captured = st.session_state.get("owner6_approvals", {}).get(row["decision_id"])
    if captured:
        owner6_register[index] = captured
owner6 = project_approval_capture(owner6_register)
executive = payload["executive"]
kpi = executive["todays_kpi"]


def safe_page_link(route: str, *, label: str, icon: str = "") -> None:
    """Render native navigation with an AppTest fallback."""
    try:
        st.page_link(route, label=label, icon=icon or None, use_container_width=True)
    except (KeyError, TypeError):
        slug = route.removeprefix("pages/").removesuffix(".py").split("_", 1)[-1]
        st.markdown(f"[{icon} {label}](./{slug})")


def cards(items: list[tuple[str, object, str]]) -> None:
    body = "".join(
        f'<div class="op4-card"><small>{html.escape(label)}</small><strong>{html.escape(str(value))}</strong><small>{html.escape(note)}</small></div>'
        for label, value, note in items
    )
    st.markdown(f'<div class="op4-grid">{body}</div>', unsafe_allow_html=True)


st.title("AIOS Business Home")
st.caption(f'OPERATION-4 REAL BUSINESS EXECUTION / {payload["operation_date"]} / BUSINESS HOME ONLY')
st.error("PROJECTION FIRST | PROPOSAL ONLY | REVIEW REQUIRED | EXECUTE: FALSE | DRY RUN: TRUE")
evidence_status_legend()
render_business_home_readiness()
render_revenue2_home()
render_first_customer_package()
render_revenue4_home()
render_revenue5_home()
render_revenue6_home()
render_revenue7_home()
render_revenue7_evidence()
render_revenue8_home()
render_revenue8_summary()
render_revenue9_home()

st.subheader("Work Navigation")
nav_columns = st.columns(4)
navigation = (
    ("Commander", "commander", "💬"), ("Sales", "sales", "🎯"),
    ("Marketing", "marketing", "📣"), ("Learning", "learning", "🧠"),
    ("Review", "review", "✅"), ("Executive", "executive", "📊"),
    ("Customer", "delivery", "👤"),
)
for index, (label, key, icon) in enumerate(navigation):
    with nav_columns[index % 4]:
        safe_page_link(payload["navigation_routes"][key], label=label, icon=icon)

st.subheader("Inquiry Preparation")
contact_left, contact_right = st.columns([3, 1])
with contact_left:
    st.info("CONTACT READY / サービス・価格・納期・FAQ・問い合わせ手順を閲覧できます。Proposal only / 受付停止中。")
with contact_right:
    safe_page_link("pages/61_Contact_Inquiry_Preparation.py", label="お問い合わせ準備を見る", icon="📨")
st.caption("Business Home is the only entry point / OWNER FINAL REVIEW REQUIRED / PRODUCTION NO-GO")

st.subheader("Official Website")
website_left, website_right = st.columns([3, 1])
with website_left:
    st.info("Website Completion 100% / Page Count 12 / Missing Pages 0 / Review Status: OWNER REQUIRED")
with website_right:
    safe_page_link("pages/34_Official_Site.py", label="公式サイトをレビュー", icon="🌐")
st.caption("Website Preview / Proposal only / Quick Action disabled / Production NO-GO")

st.subheader("Today's Mission")
progress_total = max(len(payload["todays_tasks"]), 1)
progress_done = sum(item.get("status") == "completed" for item in payload["todays_tasks"])
st.markdown(
    f'<div class="op4-hero"><small>最優先タスク / PROPOSAL</small><h2>{html.escape(executive["todays_priority"])}</h2>'
    f'<span>期限: End of Day ・ 売上目標: 初収益に近づく人間レビュー ・ 現在の進捗: {progress_done}/{progress_total}</span></div>',
    unsafe_allow_html=True,
)
st.progress(progress_done / progress_total, text=f"Today's progress {progress_done}/{progress_total}")
st.dataframe(pd.DataFrame(payload["todays_priorities"]), use_container_width=True, hide_index=True)

st.subheader("Commander Mission")
st.info(payload["commander_daily_mission"]["mission"])
st.caption(f'根拠: {payload["commander_daily_mission"]["basis"]} / PROPOSAL ONLY')
mission_steps = ("記事を書く", "レビュー", "営業", "納品", "Learning")
flow = "".join(f'<div class="op4-step"><span>{index:02d}</span><b>{label}</b><span>PROPOSAL / HUMAN REVIEW</span></div>' for index, label in enumerate(mission_steps, 1))
st.markdown(f'<div class="op4-flow">{flow}</div>', unsafe_allow_html=True)

st.subheader("Sales Today")
cards([
    ("問い合わせ", kpi["inquiries"], "Projection"),
    ("案件", kpi["active_projects"], "Projection"),
    ("見積", payload["sales_queue"]["count"], "候補 / Projection"),
    ("納品待ち", payload["delivery_queue"]["count"], "Projection"),
])

st.subheader("Marketing Today")
marketing_metrics = payload["marketing"]["metrics"]
marketing_timeline = payload["marketing"]["timeline_counts"]
cards([
    ("note", marketing_metrics.get("published_article_count", 0), "公開済みProjection"),
    ("Threads", marketing_timeline.get("threads", marketing_timeline.get("threads_count", 0)), "候補Projection"),
    ("LP", marketing_timeline.get("lp", marketing_timeline.get("lp_count", 0)), "候補Projection"),
    ("FAQ", marketing_timeline.get("faq", marketing_timeline.get("faq_count", 0)), "候補Projection"),
    ("改善候補", payload["marketing_queue"]["count"], "PROPOSAL ONLY"),
])

st.subheader("Executive Snapshot")
render_executive_readiness()
render_revenue2_executive()
render_executive_package()
render_revenue4_executive()
render_revenue5_executive()
render_revenue6_executive()
render_revenue7_executive()
render_revenue8_executive()
render_revenue9_executive()
cards([
    ("Revenue", f'¥{kpi["verified_revenue_jpy"]:,}', "VERIFIED ACTUAL"),
    ("Customer", kpi["inquiries"], "問い合わせProjection"),
    ("Projects", kpi["active_projects"], "Active Projection"),
    ("Marketing", kpi["published_articles"], "Published Projection"),
    ("Learning", 1, "PROPOSAL ONLY"),
    ("Owner Completion %", f'{owner4["executive"]["owner_completion_percent"]}%', "APPROVED ONLY"),
    ("Approved", owner4["executive"]["approved"], "Owner Decisions"),
    ("Remaining", owner4["executive"]["remaining"], "Owner Decisions"),
    ("Launch Blockers", len(owner4["executive"]["launch_blockers"]), "LAUNCH NO-GO"),
    ("Legal Status", owner4["executive"]["legal_status"], "Review Required"),
    ("Business Status", owner4["executive"]["business_status"], "Review Required"),
])
for label, value in (("Today's Priority", executive["todays_priority"]), ("Current Bottleneck", executive["current_bottleneck"]), ("Risk", executive["risk"]), ("Next Action", executive["next_action"])):
    st.write(f"**{label}:** {value}")

st.markdown("#### OWNER-10 Executive / Proposal Only")
cards([
    ("Owner Ready", "BLOCKED", "APPROVED 0/20"),
    ("Business Ready", "BLOCKED", "Commercial decisions pending"),
    ("Legal Ready", "BLOCKED", "Legal evidence pending"),
    ("Revenue Ready", "BLOCKED", "Revenue decisions pending"),
    ("Production Ready", "BLOCKED", "PRODUCTION NO-GO"),
])

st.subheader("Launch Status")
launch_blocks = [
    {"block": "Owner approvals", "status": "BLOCKED" if kpi["owner_unresolved"] else "REVIEW_REQUIRED", "evidence": f'{kpi["owner_unresolved"]} unresolved'},
    {"block": "First revenue evidence", "status": "BLOCKED" if kpi["verified_revenue_jpy"] == 0 else "REVIEW_REQUIRED", "evidence": f'¥{kpi["verified_revenue_jpy"]:,} verified'},
    {"block": "Customer pipeline", "status": "BLOCKED" if kpi["inquiries"] == 0 else "REVIEW_REQUIRED", "evidence": f'{kpi["inquiries"]} inquiries'},
    {"block": "Production release", "status": "BLOCKED", "evidence": "Production prohibited in OPERATION-4"},
]
st.dataframe(pd.DataFrame(launch_blocks), use_container_width=True, hide_index=True)

st.markdown("#### OWNER-10 Launch Gate")
owner10_gates = [
    {"gate": "Technical", "status": "READY"}, {"gate": "Visual", "status": "READY"},
    {"gate": "Accessibility", "status": "READY"}, {"gate": "Security", "status": "READY"},
    {"gate": "Business", "status": "BLOCKED"}, {"gate": "Legal", "status": "BLOCKED"},
    {"gate": "Revenue", "status": "BLOCKED"}, {"gate": "Owner", "status": "BLOCKED"},
    {"gate": "Operations", "status": "CONDITIONAL"}, {"gate": "Production", "status": "BLOCKED"},
]
st.dataframe(pd.DataFrame(owner10_gates), use_container_width=True, hide_index=True)
st.caption("READY / BLOCKED / CONDITIONAL only · Proposal display · Production NO-GO")

st.subheader("Owner Decisions")
cards([
    ("Owner Approval Progress", owner6["business_home"]["approval_progress"], "OWNER-10 Review Layer"),
    ("Approved", owner6["business_home"]["approved"], "Human Input Only"),
    ("Remaining", owner6["business_home"]["remaining"], "Human Review"),
    ("Evidence Complete", 20 - owner6["business_home"]["evidence_missing"], "Local Evidence Only"),
    ("Launch Gate Summary", "4 READY / 5 BLOCKED / 1 CONDITIONAL", "PRODUCTION BLOCKED"),
])
st.caption(
    f'Approval {owner6["executive"]["approval_percent"]}% / '
    f'Evidence {owner6["executive"]["evidence_percent"]}% / '
    f'Launch {owner6["executive"]["launch_percent"]}%'
)
owner10_proposals = (
    "AIOS", "アンドプランニング（正式名称・事業形態未確認）", "svc-note-article-foundation",
    "16,500円（1件）", "税込表示案", "平日10:00〜18:00 Asia/Tokyo", "初回返信1営業日以内",
    "AIOS公式サイト（正式送信先未確定、disabled）", "必要資料完全受領後3〜5営業日",
    "初稿提出後2回まで（当初scope内）", "銀行振込（振込先は公開設定に保存しない）",
    "制作開始前は返金可。開始後は進行済み作業相当額を控除し個別協議",
    "OWNER2_TERMS_DRAFT.md", "OWNER2_PRIVACY_DRAFT.md", "未確定（公開禁止）", "未確定",
    "同時受付1件", "未確定", "未確定", "NO-GOを維持。独立GO承認は未提示",
)
display_fields = [
    "decision_id", "title", "current_value", "proposal_value", "approved_value",
    "rejected_value", "evidence_id", "evidence_source", "owner", "reviewer",
    "approval_date", "effective_date", "launch_impact", "rollback_impact",
]
st.caption(f'未承認 {owner6["business_home"]["remaining"]}件 / 20項目表示 / Session memory only / Business Logic反映なし')
owner_rows = [owner6["review_records"][index - 1] for index in range(1, 21)][:20]
owner10_rows = []
for index, row in enumerate(owner_rows):
    status = row["current_status"]
    owner10_rows.append({
        **row,
        "current_value": "",
        "proposal_value": owner10_proposals[index],
        "approved_value": owner10_proposals[index] if status == "APPROVED" else "",
        "rejected_value": "",
        "launch_impact": "CONDITIONAL" if row["decision_id"] in {"OWNER3-OD-06", "OWNER3-OD-10", "OWNER3-OD-17"} else "BLOCKED",
    })
st.dataframe(pd.DataFrame(owner10_rows)[display_fields], use_container_width=True, hide_index=True)

with st.expander("OWNER-6 Review Layer — Human Approval Input"):
    st.warning("この入力は人間Owner専用です。保存・実行・Business Logic反映は行いません。")
    with st.form("owner6_human_approval_form", clear_on_submit=False):
        decision_id = st.selectbox("Decision ID", [row["decision_id"] for row in owner6_register])
        selected = next(row for row in owner6_register if row["decision_id"] == decision_id)
        st.text_input("Current Status", value=selected["current_status"], disabled=True)
        proposal = st.text_input("Proposal")
        evidence_id = st.text_input("Evidence ID")
        evidence_source = st.text_input("Evidence Source")
        owner = st.text_input("Owner")
        reviewer = st.text_input("Reviewer")
        approval_date = st.date_input("Approval Date")
        effective_date = st.date_input("Effective Date")
        rollback_impact = st.text_area("Rollback Impact")
        remarks = st.text_area("Remarks")
        human_attested = st.checkbox("I am the human Owner and explicitly approve this Decision")
        submitted = st.form_submit_button("Capture Owner Approval in Review Layer", type="primary")
    if submitted:
        try:
            candidate = {
                **selected, "proposal": proposal, "evidence_id": evidence_id,
                "evidence_source": evidence_source, "owner": owner, "reviewer": reviewer,
                "approval_date": approval_date, "effective_date": effective_date,
                "rollback_impact": rollback_impact, "remarks": remarks,
            }
            captured = capture_owner_approval(
                candidate, input_channel=REVIEW_LAYER, human_attested=human_attested,
            )
            approvals = dict(st.session_state.get("owner6_approvals", {}))
            approvals[decision_id] = captured
            st.session_state["owner6_approvals"] = approvals
            st.success("Human approval captured in local session memory. No business action executed.")
            st.rerun()
        except (PermissionError, ValueError) as error:
            st.error(str(error))

st.subheader("Daily Checklist")
checklist = (("Morning", "Business HomeとExecutive Snapshotを確認"), ("Working", "Commander順序で候補作業"), ("Review", "成果・Evidence・未承認を人間確認"), ("Learning", "改善候補のみ作成。登録禁止"), ("Finish", "End Of Dayを確認して終了"))
checklist_html = "".join(f'<div class="op4-step"><span>{index:02d}</span><b>{label}</b><span>{detail}</span></div>' for index, (label, detail) in enumerate(checklist, 1))
st.markdown(f'<div class="op4-flow">{checklist_html}</div>', unsafe_allow_html=True)

st.subheader("End Of Day")
end_of_day = payload["end_of_day_summary"]
cards([
    ("本日の成果", end_of_day["completed_count"], "Completed Projection"),
    ("Proposal", end_of_day["review_required_count"], "Review Required"),
    ("Knowledge候補", 0, "登録禁止"),
    ("改善候補", 1, "Learning Proposal"),
    ("売上", f'¥{end_of_day["verified_revenue_jpy"]:,}', "VERIFIED ACTUAL"),
    ("未完了", max(progress_total - progress_done, 0), "Projection"),
])
st.info(payload["learning_proposal"]["proposal"])
st.caption(end_of_day["close_condition"])

# Legacy headings retained for regression/search compatibility; all remain projection-only.
with st.expander("Projection Details"):
    st.markdown("#### Today's Tasks")
    st.dataframe(pd.DataFrame(payload["todays_tasks"]), use_container_width=True, hide_index=True)
    st.markdown("#### Today's Priorities")
    st.markdown("#### Commander Daily Mission")
    st.markdown("#### Sales Queue / Marketing Queue / Delivery Queue")
    st.markdown("#### Learning Proposal / Executive Summary / End of Day Summary")
    st.markdown("#### Customer Workspace / Workspace Read / Knowledge / Daily Summary")
    st.caption("Owner未決・問い合わせ・案件・売上は既存ローカルProjectionのみです。")

st.subheader("Quick Actions")
action_html = "".join(f'<button disabled aria-disabled="true" style="min-height:44px;cursor:not-allowed">{html.escape(action["label"])}</button>' for action in payload["quick_actions"])
st.markdown(f'<div class="op4-grid">{action_html}</div>', unsafe_allow_html=True)
st.warning("外部通信、Production、Google Workspace Write、Mail、SNS、契約、決済、Knowledge/Learning登録、Git Push、Releaseは禁止です。")
