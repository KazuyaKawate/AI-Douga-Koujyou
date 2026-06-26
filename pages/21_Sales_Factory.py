"""
Sales Factory — Creator Factory OS v4.5
CRM: leads, deals, follow-ups, proposals, revenue forecast.
No external API calls. Rule-based only.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.factories.sales.lead_manager import (
    load_leads, create_lead, update_lead, delete_lead,
    LEAD_STATUSES, STATUS_LABELS as LEAD_STATUS_LABELS,
    STATUS_ICONS as LEAD_STATUS_ICONS,
    LEAD_RANKS, RANK_ICONS,
    LEAD_SOURCES, SOURCE_LABELS,
    get_factory_summary as lead_summary,
)
from src.factories.sales.deal_manager import (
    load_deals, create_deal, update_deal, transition_stage, delete_deal,
    STAGES, STAGE_LABELS, STAGE_ICONS, STAGE_PROBABILITY,
    get_factory_summary as deal_summary,
)
from src.factories.sales.followup_manager import (
    load_followups, create_followup, mark_done_followup, skip_followup,
    get_overdue_followups, get_today_followups, get_week_followups,
    get_followup_summary, FOLLOWUP_TYPES, TYPE_LABELS, STATUS_LABELS as FU_STATUS_LABELS,
)
from src.factories.sales.proposal_tracker import (
    load_proposals, create_proposal, update_proposal_status, delete_proposal,
    RESPONSE_STATUSES, RESPONSE_LABELS, RESPONSE_ICONS, get_proposal_summary,
)
from src.factories.sales.sales_forecast import (
    calculate_forecast, get_pipeline_by_stage, get_monthly_projection,
)

st.set_page_config(page_title="営業工場 | Creator Factory OS", page_icon="💼", layout="wide")

TODAY = date.today()
TODAY_STR = TODAY.isoformat()

# ── Load data ──────────────────────────────────────────────────────────────────
leads_data = load_leads()
deals_data = load_deals()
followups_data = load_followups()
proposals_data = load_proposals()

l_sum = lead_summary(leads_data)
d_sum = deal_summary(deals_data)
fu_sum = get_followup_summary(followups_data)
forecast = calculate_forecast(leads_data, deals_data)

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("💼 営業工場")
st.caption(f"CRM・リード管理・商談・フォロー・提案・売上予測 | v4.5 | {TODAY.strftime('%Y年%m月%d日')}")

if fu_sum["overdue"] > 0:
    st.warning(f"⚠️ 期限超過のフォローアップが **{fu_sum['overdue']} 件** あります。すぐに対応してください。")

st.divider()

# ── Summary cards ──────────────────────────────────────────────────────────────
s1, s2, s3, s4, s5, s6 = st.columns(6)
s1.metric("👥 見込み客数",     l_sum["total"],
          help="登録済み見込み客の総数")
s2.metric("🤝 商談数",         d_sum["active"],
          help="進行中の商談")
s3.metric("🏆 成約数",         d_sum["contracted"],
          help="成約した商談の累計")
s4.metric("❌ 失注数",         d_sum["lost"],
          help="失注した商談の累計")
s5.metric("💰 今月売上予測",   f"¥{forecast['expected_monthly']:,}",
          help=f"目標: ¥{forecast['monthly_target']:,} / 達成率 {forecast['target_attainment']}%")
s6.metric("⚠️ 要フォロー",     fu_sum["needs_followup"],
          delta=f"-{fu_sum['overdue']} 期限超過" if fu_sum["overdue"] > 0 else None,
          delta_color="inverse" if fu_sum["overdue"] > 0 else "off",
          help="今日 + 期限超過のフォローアップ")

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_names = ["🏠 ダッシュボード", "👥 見込み客", "🤝 商談", "📅 フォロー", "📋 提案", "📈 売上予測"]
tabs = st.tabs(tab_names)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 1: Dashboard
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tabs[0]:
    st.subheader("今日の営業アクション")

    today_fus = get_today_followups(followups_data)
    overdue_fus = get_overdue_followups(followups_data)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**📅 今日のフォローアップ**")
        if today_fus:
            for fu in today_fus:
                lead = next((l for l in leads_data["leads"] if l["lead_id"] == fu["lead_id"]), {})
                lead_name = lead.get("name", fu["lead_id"])
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"**{TYPE_LABELS.get(fu['type'], fu['type'])}** — {lead_name}")
                    c1.caption(fu.get("description", ""))
                    if c2.button("✅ 完了", key=f"dash_done_{fu['followup_id']}"):
                        ok, msg = mark_done_followup(fu["followup_id"])
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
        else:
            st.info("今日のフォローアップはありません。")

    with col_b:
        st.markdown("**⚠️ 期限超過フォローアップ**")
        if overdue_fus:
            for fu in overdue_fus[:5]:
                lead = next((l for l in leads_data["leads"] if l["lead_id"] == fu["lead_id"]), {})
                lead_name = lead.get("name", fu["lead_id"])
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(f"🔴 **{lead_name}** — {fu.get('due_date', '')} 期限")
                    c1.caption(fu.get("description", ""))
                    if c2.button("✅ 完了", key=f"dash_ov_{fu['followup_id']}"):
                        ok, msg = mark_done_followup(fu["followup_id"])
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            if len(overdue_fus) > 5:
                st.caption(f"他 {len(overdue_fus) - 5} 件の期限超過があります。")
        else:
            st.success("期限超過のフォローアップはありません。")

    st.divider()
    st.subheader("パイプライン概要")
    pipeline = get_pipeline_by_stage(deals_data)
    pcols = st.columns(len(STAGES))
    for col, stage in zip(pcols, STAGES):
        info = pipeline.get(stage, {})
        col.metric(
            f"{STAGE_ICONS.get(stage,'')} {STAGE_LABELS.get(stage, stage)}",
            f"{info.get('count', 0)} 件",
            f"¥{info.get('amount', 0):,}" if info.get("amount") else None,
        )

    st.divider()
    st.subheader("最近の商談")
    all_deals = sorted(deals_data.get("deals", []), key=lambda d: d.get("updated_at", ""), reverse=True)
    for deal in all_deals[:6]:
        with st.container(border=True):
            d1, d2, d3 = st.columns([3, 2, 1])
            icon = STAGE_ICONS.get(deal.get("stage", ""), "")
            d1.markdown(f"{icon} **{deal.get('title', '')}**")
            d1.caption(f"期待額: ¥{deal.get('amount', 0):,} | 確度: {deal.get('probability', 0)}%")
            d2.caption(f"ステージ: {STAGE_LABELS.get(deal.get('stage', ''), deal.get('stage',''))}")
            d2.caption(f"更新: {deal.get('updated_at', '')[:10]}")
            d3.caption(deal.get("status", ""))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 2: Leads
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tabs[1]:
    st.subheader("見込み客管理")

    # Create new lead
    with st.expander("➕ 新規リード登録", expanded=False):
        with st.form("new_lead_form"):
            lf1, lf2 = st.columns(2)
            l_name = lf1.text_input("氏名 *", placeholder="田中太郎")
            l_company = lf2.text_input("会社名", placeholder="株式会社サンプル")
            lf3, lf4, lf5 = st.columns(3)
            l_source = lf3.selectbox("流入元", LEAD_SOURCES, format_func=lambda x: SOURCE_LABELS.get(x, x))
            l_rank = lf4.selectbox("ランク", LEAD_RANKS, index=2,
                                   format_func=lambda x: f"{RANK_ICONS.get(x,'')} {x}")
            l_contact = lf5.text_input("連絡方法", placeholder="DM, メール, 電話...")
            l_interest = st.text_input("興味・関心", placeholder="AI動画制作支援, etc.")
            lf6, lf7 = st.columns(2)
            l_next_action = lf6.text_input("次のアクション", placeholder="資料送付")
            l_next_date = lf7.date_input("アクション期限", value=None)
            l_memo = st.text_area("メモ", height=80)
            if st.form_submit_button("🆕 リードを登録", type="primary"):
                if l_name.strip():
                    create_lead(
                        name=l_name.strip(),
                        company=l_company.strip(),
                        source=l_source,
                        contact_method=l_contact.strip() or "DM",
                        rank=l_rank,
                        interest=l_interest.strip(),
                        next_action=l_next_action.strip(),
                        next_action_date=l_next_date.isoformat() if l_next_date else "",
                        memo=l_memo.strip(),
                    )
                    st.success("リードを登録しました")
                    st.rerun()
                else:
                    st.error("氏名は必須です")

    # Filters
    flt1, flt2, flt3 = st.columns(3)
    flt_status = flt1.multiselect("ステータスフィルター", LEAD_STATUSES,
                                   format_func=lambda x: f"{LEAD_STATUS_ICONS.get(x,'')} {LEAD_STATUS_LABELS.get(x,x)}")
    flt_rank = flt2.multiselect("ランクフィルター", LEAD_RANKS,
                                 format_func=lambda x: f"{RANK_ICONS.get(x,'')} {x}")
    flt_source = flt3.multiselect("流入元フィルター", LEAD_SOURCES,
                                   format_func=lambda x: SOURCE_LABELS.get(x, x))

    leads = leads_data.get("leads", [])
    if flt_status:
        leads = [l for l in leads if l.get("status") in flt_status]
    if flt_rank:
        leads = [l for l in leads if l.get("rank") in flt_rank]
    if flt_source:
        leads = [l for l in leads if l.get("source") in flt_source]
    leads = sorted(leads, key=lambda l: (l.get("rank", "Z"), l.get("updated_at", "")), reverse=True)

    st.caption(f"{len(leads)} 件のリード")

    if not leads:
        st.info("リードが登録されていません。「新規リード登録」から追加してください。")
    else:
        for lead in leads:
            status_icon = LEAD_STATUS_ICONS.get(lead.get("status", "new"), "")
            rank_icon = RANK_ICONS.get(lead.get("rank", "C"), "")
            overdue = (lead.get("next_action_date", "9999") < TODAY_STR
                       and lead.get("status") not in ("contracted", "lost", "archived"))
            with st.container(border=True):
                hdr, act = st.columns([5, 2])
                with hdr:
                    st.markdown(
                        f"{rank_icon} **{lead.get('name', '')}** "
                        f"{('— ' + lead.get('company','')) if lead.get('company') else ''} "
                        f"&nbsp;&nbsp;{status_icon} {LEAD_STATUS_LABELS.get(lead.get('status',''), lead.get('status',''))}"
                    )
                    src = SOURCE_LABELS.get(lead.get("source", ""), lead.get("source", ""))
                    nxt = lead.get("next_action", "")
                    nxt_date = lead.get("next_action_date", "")
                    overdue_badge = " 🔴 期限超過" if overdue else ""
                    st.caption(f"📍 {src} | 連絡: {lead.get('contact_method','')} | 次: {nxt} {nxt_date}{overdue_badge}")
                    if lead.get("interest"):
                        st.caption(f"💡 {lead['interest']}")

                with act:
                    status_options = LEAD_STATUSES
                    current_idx = status_options.index(lead.get("status", "new")) if lead.get("status") in status_options else 0
                    new_status = st.selectbox(
                        "ステータス",
                        status_options,
                        index=current_idx,
                        format_func=lambda x: f"{LEAD_STATUS_ICONS.get(x,'')} {LEAD_STATUS_LABELS.get(x,x)}",
                        key=f"lead_status_{lead['lead_id']}",
                        label_visibility="collapsed",
                    )
                    if new_status != lead.get("status"):
                        update_lead(lead["lead_id"], status=new_status)
                        st.rerun()

                with st.expander("詳細・編集", expanded=False):
                    ef1, ef2, ef3 = st.columns(3)
                    e_rank = ef1.selectbox("ランク", LEAD_RANKS,
                                           index=LEAD_RANKS.index(lead.get("rank", "C")),
                                           format_func=lambda x: f"{RANK_ICONS.get(x,'')} {x}",
                                           key=f"e_rank_{lead['lead_id']}")
                    e_next = ef2.text_input("次のアクション", value=lead.get("next_action", ""),
                                            key=f"e_next_{lead['lead_id']}")
                    e_date_val = None
                    if lead.get("next_action_date"):
                        try:
                            from datetime import date as _date
                            e_date_val = _date.fromisoformat(lead["next_action_date"])
                        except Exception:
                            pass
                    e_date = ef3.date_input("期限", value=e_date_val, key=f"e_date_{lead['lead_id']}")
                    e_memo = st.text_area("メモ", value=lead.get("memo", ""), height=60,
                                          key=f"e_memo_{lead['lead_id']}")
                    ec1, ec2 = st.columns(2)
                    if ec1.button("💾 保存", key=f"save_lead_{lead['lead_id']}"):
                        update_lead(
                            lead["lead_id"],
                            rank=e_rank,
                            next_action=e_next,
                            next_action_date=e_date.isoformat() if e_date else "",
                            memo=e_memo,
                        )
                        st.success("保存しました")
                        st.rerun()
                    if ec2.button("🗑️ 削除", key=f"del_lead_{lead['lead_id']}",
                                  help="このリードを完全に削除します"):
                        delete_lead(lead["lead_id"])
                        st.rerun()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 3: Deals
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tabs[2]:
    st.subheader("商談管理")

    with st.expander("➕ 新規商談登録", expanded=False):
        with st.form("new_deal_form"):
            lead_options = {l["lead_id"]: f"{l.get('name','')} ({l.get('company','')})"
                           for l in leads_data.get("leads", [])}
            df1, df2 = st.columns(2)
            d_title = df1.text_input("商談タイトル *", placeholder="AI動画制作サポートプラン")
            d_lead = df2.selectbox("関連リード", [""] + list(lead_options.keys()),
                                   format_func=lambda x: lead_options.get(x, "— なし —"))
            df3, df4, df5 = st.columns(3)
            d_stage = df3.selectbox("ステージ", STAGES,
                                    format_func=lambda x: f"{STAGE_ICONS.get(x,'')} {STAGE_LABELS.get(x,x)}")
            d_amount = df4.number_input("金額 (円)", min_value=0, step=1000, value=0)
            d_prob = df5.number_input("確度 (%)", min_value=0, max_value=100,
                                       value=STAGE_PROBABILITY.get(d_stage, 20))
            d_close = st.date_input("期待クローズ日", value=None)
            d_memo = st.text_area("メモ", height=60)
            if st.form_submit_button("🆕 商談を登録", type="primary"):
                if d_title.strip():
                    create_deal(
                        title=d_title.strip(),
                        lead_id=d_lead,
                        stage=d_stage,
                        amount=int(d_amount),
                        probability=int(d_prob),
                        expected_close_date=d_close.isoformat() if d_close else "",
                        memo=d_memo.strip(),
                    )
                    st.success("商談を登録しました")
                    st.rerun()
                else:
                    st.error("商談タイトルは必須です")

    # Filter
    dc1, dc2 = st.columns(2)
    flt_deal_stage = dc1.multiselect("ステージフィルター", STAGES,
                                      format_func=lambda x: f"{STAGE_ICONS.get(x,'')} {STAGE_LABELS.get(x,x)}")
    flt_deal_status = dc2.multiselect("ステータス", ["active", "won", "lost"],
                                       format_func=lambda x: {"active": "🔵 進行中", "won": "✅ 成約", "lost": "❌ 失注"}.get(x, x))

    all_deals_list = deals_data.get("deals", [])
    if flt_deal_stage:
        all_deals_list = [d for d in all_deals_list if d.get("stage") in flt_deal_stage]
    if flt_deal_status:
        all_deals_list = [d for d in all_deals_list if d.get("status") in flt_deal_status]
    all_deals_list = sorted(all_deals_list, key=lambda d: d.get("updated_at", ""), reverse=True)

    st.caption(f"{len(all_deals_list)} 件の商談")

    if not all_deals_list:
        st.info("商談が登録されていません。「新規商談登録」から追加してください。")
    else:
        for deal in all_deals_list:
            stage_icon = STAGE_ICONS.get(deal.get("stage", ""), "")
            status_color = {"active": "🔵", "won": "✅", "lost": "❌"}.get(deal.get("status", "active"), "🔵")
            with st.container(border=True):
                dh1, dh2 = st.columns([4, 2])
                with dh1:
                    st.markdown(f"{stage_icon} **{deal.get('title', '')}** &nbsp; {status_color}")
                    lead = next((l for l in leads_data["leads"] if l["lead_id"] == deal.get("lead_id")), {})
                    lead_info = f"👤 {lead.get('name','')} {('/ ' + lead.get('company','')) if lead.get('company') else ''}" if lead else ""
                    st.caption(f"¥{deal.get('amount',0):,} | 確度{deal.get('probability',0)}% | 期待WF: ¥{int(deal.get('amount',0)*deal.get('probability',0)/100):,}")
                    if lead_info:
                        st.caption(lead_info)
                    close_date = deal.get("expected_close_date", "")
                    if close_date:
                        late = close_date < TODAY_STR and deal.get("status") == "active"
                        st.caption(f"クローズ予定: {close_date}" + (" 🔴 超過" if late else ""))

                with dh2:
                    cur_stage = deal.get("stage", "new")
                    cur_idx = STAGES.index(cur_stage) if cur_stage in STAGES else 0
                    new_stage = st.selectbox(
                        "ステージ変更",
                        STAGES,
                        index=cur_idx,
                        format_func=lambda x: f"{STAGE_ICONS.get(x,'')} {STAGE_LABELS.get(x,x)}",
                        key=f"deal_stage_{deal['deal_id']}",
                        label_visibility="collapsed",
                    )
                    if new_stage != cur_stage:
                        ok, msg, _ = transition_stage(deal["deal_id"], new_stage)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)
                        st.rerun()

                with st.expander("詳細・編集", expanded=False):
                    ea1, ea2 = st.columns(2)
                    e_amount = ea1.number_input("金額 (円)", value=int(deal.get("amount", 0)),
                                                 step=1000, key=f"e_amount_{deal['deal_id']}")
                    e_prob = ea2.number_input("確度 (%)", value=int(deal.get("probability", 20)),
                                               min_value=0, max_value=100,
                                               key=f"e_prob_{deal['deal_id']}")
                    e_close_val = None
                    if deal.get("expected_close_date"):
                        try:
                            e_close_val = date.fromisoformat(deal["expected_close_date"])
                        except Exception:
                            pass
                    e_close = st.date_input("クローズ予定日", value=e_close_val,
                                            key=f"e_close_{deal['deal_id']}")
                    e_dmemo = st.text_area("メモ", value=deal.get("memo", ""), height=60,
                                           key=f"e_dmemo_{deal['deal_id']}")
                    dc_s1, dc_s2 = st.columns(2)
                    if dc_s1.button("💾 保存", key=f"save_deal_{deal['deal_id']}"):
                        update_deal(
                            deal["deal_id"],
                            amount=int(e_amount),
                            probability=int(e_prob),
                            expected_close_date=e_close.isoformat() if e_close else "",
                            memo=e_dmemo,
                        )
                        st.success("保存しました")
                        st.rerun()
                    if dc_s2.button("🗑️ 削除", key=f"del_deal_{deal['deal_id']}"):
                        delete_deal(deal["deal_id"])
                        st.rerun()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 4: Follow-ups
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tabs[3]:
    st.subheader("フォロー管理")

    with st.expander("➕ フォローアップ登録", expanded=False):
        with st.form("new_fu_form"):
            fu_leads = {l["lead_id"]: f"{l.get('name','')} ({l.get('company','')})"
                        for l in leads_data.get("leads", [])}
            fl1, fl2, fl3 = st.columns(3)
            fu_lead = fl1.selectbox("リード *", list(fu_leads.keys()),
                                    format_func=lambda x: fu_leads.get(x, x))
            fu_type = fl2.selectbox("種別", FOLLOWUP_TYPES,
                                    format_func=lambda x: TYPE_LABELS.get(x, x))
            fu_due = fl3.date_input("期限日", value=date.today() + timedelta(days=1))
            fu_desc = st.text_input("内容 *", placeholder="初回資料を送付する")
            fu_deal_opts = {d["deal_id"]: d.get("title", d["deal_id"])
                           for d in deals_data.get("deals", []) if d.get("status") == "active"}
            fu_deal = st.selectbox("関連商談（任意）", [""] + list(fu_deal_opts.keys()),
                                   format_func=lambda x: fu_deal_opts.get(x, "— なし —"))
            if st.form_submit_button("📅 フォローアップを登録", type="primary"):
                if fu_lead and fu_desc.strip():
                    create_followup(
                        lead_id=fu_lead,
                        description=fu_desc.strip(),
                        due_date=fu_due.isoformat(),
                        followup_type=fu_type,
                        deal_id=fu_deal,
                    )
                    st.success("フォローアップを登録しました")
                    st.rerun()
                else:
                    st.error("リードと内容は必須です")

    fu_view = st.radio("表示", ["今日", "7日以内", "期限超過", "すべて"], horizontal=True,
                        key="fu_view_radio")

    if fu_view == "今日":
        display_fus = get_today_followups(followups_data)
        st.caption(f"今日のフォローアップ: {len(display_fus)} 件")
    elif fu_view == "7日以内":
        display_fus = get_week_followups(followups_data)
        st.caption(f"7日以内のフォローアップ: {len(display_fus)} 件")
    elif fu_view == "期限超過":
        display_fus = get_overdue_followups(followups_data)
        st.caption(f"期限超過: {len(display_fus)} 件")
    else:
        display_fus = sorted(
            followups_data.get("followups", []),
            key=lambda f: f.get("due_date", ""),
        )
        st.caption(f"すべてのフォローアップ: {len(display_fus)} 件")

    if not display_fus:
        st.info("該当するフォローアップはありません。")
    else:
        for fu in display_fus:
            lead = next((l for l in leads_data["leads"] if l["lead_id"] == fu.get("lead_id", "")), {})
            lead_name = lead.get("name", fu.get("lead_id", ""))
            overdue_flag = fu.get("due_date", "9999") < TODAY_STR and fu.get("status") == "pending"
            with st.container(border=True):
                fc1, fc2, fc3 = st.columns([4, 2, 2])
                fc1.markdown(
                    f"{'🔴 ' if overdue_flag else ''}"
                    f"{TYPE_LABELS.get(fu.get('type',''), fu.get('type',''))} — "
                    f"**{lead_name}**"
                )
                fc1.caption(f"{fu.get('description', '')} | 期限: {fu.get('due_date', '')}")
                fc2.caption(FU_STATUS_LABELS.get(fu.get("status", "pending"), ""))
                if fu.get("status") == "pending":
                    if fc3.button("✅ 完了", key=f"fu_done_{fu['followup_id']}"):
                        ok, msg = mark_done_followup(fu["followup_id"])
                        if ok:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    if fc3.button("⏭️ スキップ", key=f"fu_skip_{fu['followup_id']}"):
                        skip_followup(fu["followup_id"])
                        st.rerun()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 5: Proposals
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tabs[4]:
    st.subheader("提案管理")

    p_sum = get_proposal_summary(proposals_data)
    ps1, ps2, ps3, ps4, ps5 = st.columns(5)
    ps1.metric("📋 提案総数",   p_sum["total"])
    ps2.metric("📝 下書き",     p_sum["draft"])
    ps3.metric("📨 送付済",     p_sum["sent"])
    ps4.metric("✅ 承諾",       p_sum["accepted"])
    ps5.metric("💰 承諾額合計", f"¥{p_sum['accepted_amount']:,}")

    with st.expander("➕ 新規提案登録", expanded=False):
        with st.form("new_prop_form"):
            prop_leads = {l["lead_id"]: f"{l.get('name','')} ({l.get('company','')})"
                          for l in leads_data.get("leads", [])}
            pf1, pf2 = st.columns(2)
            prop_title = pf1.text_input("提案タイトル *", placeholder="AI動画制作サポートプラン 月額プロポーザル")
            prop_lead = pf2.selectbox("リード", [""] + list(prop_leads.keys()),
                                       format_func=lambda x: prop_leads.get(x, "— なし —"))
            pf3, pf4 = st.columns(2)
            prop_amount = pf3.number_input("提案金額 (円)", min_value=0, step=1000, value=0)
            prop_sent = pf4.date_input("送付日", value=None)
            prop_deal_opts = {d["deal_id"]: d.get("title", d["deal_id"])
                              for d in deals_data.get("deals", []) if d.get("status") == "active"}
            prop_deal = st.selectbox("関連商談（任意）", [""] + list(prop_deal_opts.keys()),
                                      format_func=lambda x: prop_deal_opts.get(x, "— なし —"))
            prop_memo = st.text_area("メモ", height=60)
            if st.form_submit_button("📋 提案を登録", type="primary"):
                if prop_title.strip():
                    create_proposal(
                        title=prop_title.strip(),
                        amount=int(prop_amount),
                        lead_id=prop_lead,
                        deal_id=prop_deal,
                        sent_date=prop_sent.isoformat() if prop_sent else "",
                        memo=prop_memo.strip(),
                    )
                    st.success("提案を登録しました")
                    st.rerun()
                else:
                    st.error("提案タイトルは必須です")

    proposals = sorted(proposals_data.get("proposals", []),
                        key=lambda p: p.get("updated_at", ""), reverse=True)
    st.caption(f"{len(proposals)} 件の提案")

    if not proposals:
        st.info("提案が登録されていません。")
    else:
        for prop in proposals:
            lead = next((l for l in leads_data["leads"] if l["lead_id"] == prop.get("lead_id", "")), {})
            lead_name = lead.get("name", "")
            r_icon = RESPONSE_ICONS.get(prop.get("response_status", "draft"), "📝")
            with st.container(border=True):
                pr1, pr2 = st.columns([4, 2])
                with pr1:
                    st.markdown(f"{r_icon} **{prop.get('title', '')}**")
                    st.caption(f"¥{prop.get('amount', 0):,} | {lead_name} | 送付: {prop.get('sent_date', '—')}")
                with pr2:
                    cur_rs = prop.get("response_status", "draft")
                    cur_rs_idx = RESPONSE_STATUSES.index(cur_rs) if cur_rs in RESPONSE_STATUSES else 0
                    new_rs = st.selectbox(
                        "ステータス",
                        RESPONSE_STATUSES,
                        index=cur_rs_idx,
                        format_func=lambda x: f"{RESPONSE_ICONS.get(x,'')} {RESPONSE_LABELS.get(x,x)}",
                        key=f"prop_rs_{prop['proposal_id']}",
                        label_visibility="collapsed",
                    )
                    if new_rs != cur_rs:
                        ok, msg, _ = update_proposal_status(prop["proposal_id"], new_rs)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)
                        st.rerun()
                if prop.get("memo"):
                    st.caption(f"📝 {prop['memo']}")
                if st.button("🗑️ 削除", key=f"del_prop_{prop['proposal_id']}"):
                    delete_proposal(prop["proposal_id"])
                    st.rerun()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 6: Forecast
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tabs[5]:
    st.subheader("売上予測")

    monthly = get_monthly_projection(deals_data)
    settings_data = {}
    try:
        import json as _json
        _sp = ROOT / "config" / "sales_settings.json"
        settings_data = _json.loads(_sp.read_text(encoding="utf-8")) if _sp.exists() else {}
    except Exception:
        pass

    fc1, fc2, fc3, fc4 = st.columns(4)
    fc1.metric("💰 パイプライン総額",  f"¥{forecast['pipeline_total']:,}",
               help="進行中の全商談の合計金額")
    fc2.metric("📊 加重予測",          f"¥{forecast['weighted_forecast']:,}",
               help="金額 × 確度の加重合計")
    fc3.metric("🏆 成約済み総額",      f"¥{forecast['contracted_total']:,}")
    fc4.metric("🎯 今月売上予測",      f"¥{forecast['expected_monthly']:,}",
               help=f"目標: ¥{forecast['monthly_target']:,}")

    target = forecast["monthly_target"]
    attain = forecast["target_attainment"]
    progress_val = min(attain / 100, 1.0)
    st.markdown(f"**月次目標達成率: {attain}%** (¥{forecast['expected_monthly']:,} / ¥{target:,})")
    st.progress(progress_val)

    st.divider()

    fg1, fg2 = st.columns(2)
    with fg1:
        st.markdown("**📈 今月クローズ予定**")
        st.metric("件数",     monthly["closing_this_month"])
        st.metric("予測額",   f"¥{monthly['projected_revenue']:,}")
        st.metric("成約済み", f"¥{monthly['contracted_revenue']:,}")
        st.metric("今月合計", f"¥{monthly['total_forecast']:,}")

    with fg2:
        st.markdown("**📊 コンバージョン率**")
        st.metric("商談成約率",   f"{forecast['conversion_rate']}%",
                  help="(成約件数) / (成約+失注件数) × 100")
        st.metric("リード成約率", f"{forecast['lead_conversion_rate']}%",
                  help="(成約リード) / (全リード) × 100")
        st.metric("アクティブ商談数", forecast["active_deal_count"])
        st.metric("成約商談数",       forecast["contracted_count"])

    st.divider()
    st.subheader("ステージ別パイプライン")
    pipeline = get_pipeline_by_stage(deals_data)
    for stage in STAGES:
        info = pipeline.get(stage, {})
        if info.get("count", 0) > 0:
            icon = STAGE_ICONS.get(stage, "")
            label = STAGE_LABELS.get(stage, stage)
            st.markdown(f"{icon} **{label}** — {info['count']} 件 | ¥{info['amount']:,}")
            weighted = sum(
                d.get("amount", 0) * d.get("probability", 0) / 100
                for d in info.get("deals", [])
            )
            st.caption(f"加重: ¥{int(weighted):,}")

    st.divider()
    st.subheader("⚙️ 月次目標設定")
    new_target = st.number_input(
        "月次売上目標 (円)",
        value=int(settings_data.get("monthly_target", 100000)),
        step=10000,
        min_value=0,
        key="monthly_target_input",
    )
    if st.button("💾 目標を保存", key="save_monthly_target"):
        try:
            import json as _json
            _sp = ROOT / "config" / "sales_settings.json"
            sd = _json.loads(_sp.read_text(encoding="utf-8")) if _sp.exists() else {}
            sd["monthly_target"] = int(new_target)
            _sp.write_text(_json.dumps(sd, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success(f"月次目標を ¥{new_target:,} に設定しました")
            st.rerun()
        except Exception as exc:
            st.error(f"保存エラー: {exc}")
