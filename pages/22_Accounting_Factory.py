"""
Accounting Audit Factory — Creator Factory OS v4.6
Revenue, expense, subscription, ROI, audit, and monthly report.
No external API calls. Rule-based only.
"""
import sys
from datetime import date
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.factories.accounting.revenue_manager import (
    load_revenue, create_revenue, update_revenue, delete_revenue,
    REVENUE_SOURCES, SOURCE_LABELS, REVENUE_STATUSES, STATUS_LABELS as REV_STATUS_LABELS,
    get_today_revenue, get_monthly_revenue, get_revenue_by_source,
    get_factory_summary as rev_summary,
)
from src.factories.accounting.expense_manager import (
    load_expenses, create_expense, update_expense, delete_expense,
    EXPENSE_CATEGORIES, CATEGORY_LABELS, BILLING_CYCLES, BILLING_LABELS,
    EXPENSE_STATUSES, STATUS_LABELS as EXP_STATUS_LABELS,
    get_monthly_expenses, get_expenses_by_category,
    get_factory_summary as exp_summary,
)
from src.factories.accounting.subscription_manager import (
    load_subscriptions, create_subscription, update_subscription,
    toggle_active, delete_subscription, PRESET_SERVICES,
    get_monthly_subscription_total, get_upcoming_renewals,
    get_factory_summary as sub_summary,
)
from src.factories.accounting.roi_calculator import calculate_roi, load_settings
from src.factories.accounting.audit_checker import check_audits, get_audit_summary, AUDIT_LEVELS
from src.factories.accounting.monthly_report import generate_monthly_report, export_monthly_report

st.set_page_config(page_title="会計監査工場 | Creator Factory OS", page_icon="💰", layout="wide")

TODAY = date.today()
TODAY_STR = TODAY.isoformat()
YEAR_MONTH = TODAY.strftime("%Y-%m")

# ── Load data ──────────────────────────────────────────────────────────────────
revenue_data = load_revenue()
expense_data = load_expenses()
subscription_data = load_subscriptions()
settings = load_settings()

roi = calculate_roi(revenue_data, expense_data, subscription_data, YEAR_MONTH)
warnings = check_audits(revenue_data, expense_data, subscription_data, settings)
audit_sum = get_audit_summary(warnings)
r_sum = rev_summary(revenue_data)
e_sum = exp_summary(expense_data)
s_sum = sub_summary(subscription_data)

break_even = settings.get("break_even_monthly", 50000)
break_even_remaining = roi["break_even_remaining"]

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("💰 会計監査工場")
st.caption(f"収支管理・ROI・サブスク・監査・月次レポート | v4.6 | {TODAY.strftime('%Y年%m月%d日')}")

if audit_sum["errors"] > 0:
    st.error(f"🔴 監査エラーが {audit_sum['errors']} 件あります。確認してください。")
elif audit_sum["warning"] > 0:
    st.warning(f"🟠 監査警告が {audit_sum['warning']} 件あります。")

st.divider()

# ── Summary cards ──────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("💰 今日の売上",     f"¥{r_sum['today_revenue']:,}")
c2.metric("📈 今月売上",       f"¥{roi['total_revenue']:,}")
c3.metric("📉 今月経費",       f"¥{roi['total_expense']:,}")
c4.metric("💹 今月利益",
          f"¥{roi['net_profit']:,}",
          delta="黒字" if roi["net_profit"] >= 0 else "赤字",
          delta_color="normal" if roi["net_profit"] >= 0 else "inverse")

c5, c6, c7, c8 = st.columns(4)
c5.metric("📊 ROI",            f"{roi['roi']}%",
          help="純利益 / 経費合計 × 100")
c6.metric("🎯 損益分岐点まで", f"¥{break_even_remaining:,}",
          help=f"目標: ¥{break_even:,} / 達成率: {roi['target_attainment']}%")
c7.metric("🔄 サブスク合計",   f"¥{s_sum['monthly_total']:,}/月",
          help=f"{s_sum['active_subscriptions']} 件稼働中")
c8.metric("🔔 監査アラート",    audit_sum["total"],
          delta=f"{audit_sum['errors']} エラー" if audit_sum["errors"] else None,
          delta_color="inverse" if audit_sum["errors"] else "off")

st.divider()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tabs = st.tabs(["🏠 ダッシュボード", "📈 収入管理", "📉 経費管理",
                "🔄 サブスク管理", "📊 ROI分析", "📋 月次レポート"])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 1: Dashboard
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tabs[0]:
    st.subheader("今月の財務サマリー")

    # Break-even progress
    attain = roi["target_attainment"]
    prog_val = min(attain / 100, 1.0)
    st.markdown(f"**損益分岐点達成率: {attain}%** (¥{roi['total_revenue']:,} / ¥{break_even:,})")
    st.progress(prog_val)

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**🔔 監査アラート**")
        if not warnings:
            st.success("✅ 今月の監査アラートはありません。")
        else:
            for w in warnings:
                level_info = AUDIT_LEVELS.get(w["level"], {"icon": "🔹"})
                icon = level_info["icon"]
                msg = w.get("message", "")
                details = w.get("details", "")
                if w["level"] == "error":
                    st.error(f"{icon} {msg}\n\n_{details}_")
                elif w["level"] == "warning":
                    st.warning(f"{icon} {msg}\n\n_{details}_")
                else:
                    st.info(f"{icon} {msg}\n\n_{details}_")

    with col_b:
        st.markdown("**📊 今月の収支内訳**")
        by_source = get_revenue_by_source(revenue_data, YEAR_MONTH)
        if by_source:
            for src, amt in sorted(by_source.items(), key=lambda x: -x[1]):
                label = SOURCE_LABELS.get(src, src)
                st.metric(f"{label}", f"¥{amt:,}")
        else:
            st.caption("今月の収入がまだありません。")

        st.markdown("**📉 経費カテゴリ**")
        by_cat = get_expenses_by_category(expense_data, YEAR_MONTH)
        if by_cat:
            for cat, amt in sorted(by_cat.items(), key=lambda x: -x[1]):
                label = CATEGORY_LABELS.get(cat, cat)
                st.metric(f"{label}", f"¥{amt:,}")
        else:
            st.caption("今月の経費がまだありません。")

    st.divider()
    st.subheader("⚡ クイック入力")
    with st.form("quick_rev_form"):
        qr1, qr2, qr3 = st.columns(3)
        q_source = qr1.selectbox("売上元", REVENUE_SOURCES,
                                  format_func=lambda x: SOURCE_LABELS.get(x, x))
        q_amount = qr2.number_input("金額 (円)", min_value=0, step=100, value=0)
        q_memo = qr3.text_input("メモ", placeholder="note記事売上など")
        if st.form_submit_button("💰 売上を記録", type="primary"):
            if q_amount > 0:
                create_revenue(source=q_source, amount=int(q_amount), memo=q_memo.strip())
                st.success(f"売上 ¥{q_amount:,} を記録しました")
                st.rerun()
            else:
                st.error("金額を入力してください")

    # Recent revenue entries
    st.markdown("**📅 最近の売上**")
    recent_rev = sorted(revenue_data.get("revenue", []),
                        key=lambda r: r.get("date", ""), reverse=True)[:5]
    if recent_rev:
        for rev in recent_rev:
            src_label = SOURCE_LABELS.get(rev.get("source", ""), rev.get("source", ""))
            status_label = REV_STATUS_LABELS.get(rev.get("status", ""), "")
            st.caption(f"{rev.get('date','')} | {src_label} | ¥{rev.get('amount',0):,} | {status_label} | {rev.get('memo','')}")
    else:
        st.caption("まだ売上が記録されていません。")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 2: Revenue
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tabs[1]:
    st.subheader("収入管理")

    # Sales Factory import
    sales_deals_path = ROOT / "config" / "sales_deals.json"
    if sales_deals_path.exists():
        with st.expander("💼 営業工場から収入をインポート", expanded=False):
            try:
                import json as _json
                _deals_data = _json.loads(sales_deals_path.read_text(encoding="utf-8"))
                _contracted = [
                    d for d in _deals_data.get("deals", [])
                    if d.get("status") == "won" and d.get("amount", 0) > 0
                ]
                if _contracted:
                    st.caption(f"成約済み商談: {len(_contracted)} 件")
                    for deal in _contracted:
                        ic1, ic2 = st.columns([4, 1])
                        ic1.caption(f"🏆 {deal.get('title','')} — ¥{deal.get('amount',0):,} | {deal.get('contracted_at','')[:10]}")
                        if ic2.button("📥 取込", key=f"import_deal_{deal['deal_id']}"):
                            create_revenue(
                                source="sales",
                                amount=int(deal.get("amount", 0)),
                                entry_date=deal.get("contracted_at", TODAY_STR)[:10],
                                source_factory="営業工場",
                                memo=f"営業工場: {deal.get('title','')}",
                            )
                            st.success(f"¥{deal.get('amount',0):,} を収入に記録しました")
                            st.rerun()
                else:
                    st.caption("インポート対象の成約商談がありません。")
            except Exception as exc:
                st.caption(f"営業データ読み込みエラー: {exc}")

    with st.expander("➕ 新規収入を記録", expanded=False):
        with st.form("new_rev_form"):
            rf1, rf2, rf3 = st.columns(3)
            r_source = rf1.selectbox("売上元", REVENUE_SOURCES,
                                     format_func=lambda x: SOURCE_LABELS.get(x, x))
            r_amount = rf2.number_input("金額 (円)", min_value=0, step=100, value=0)
            r_date = rf3.date_input("日付", value=TODAY)
            r_status = st.selectbox("ステータス", REVENUE_STATUSES,
                                    format_func=lambda x: REV_STATUS_LABELS.get(x, x))
            r_memo = st.text_input("メモ", placeholder="note月額サポート収入など")
            if st.form_submit_button("💰 収入を記録", type="primary"):
                if r_amount > 0:
                    create_revenue(
                        source=r_source,
                        amount=int(r_amount),
                        entry_date=r_date.isoformat(),
                        status=r_status,
                        memo=r_memo.strip(),
                    )
                    st.success("収入を記録しました")
                    st.rerun()
                else:
                    st.error("金額を入力してください")

    # Filter
    rv1, rv2 = st.columns(2)
    flt_source = rv1.multiselect("売上元フィルター", REVENUE_SOURCES,
                                  format_func=lambda x: SOURCE_LABELS.get(x, x))
    flt_rev_month = rv2.text_input("月フィルター (YYYY-MM)", value=YEAR_MONTH)

    rev_list = revenue_data.get("revenue", [])
    if flt_source:
        rev_list = [r for r in rev_list if r.get("source") in flt_source]
    if flt_rev_month:
        rev_list = [r for r in rev_list if r.get("date", "")[:7] == flt_rev_month]
    rev_list = sorted(rev_list, key=lambda r: r.get("date", ""), reverse=True)

    month_total = sum(r.get("amount", 0) for r in rev_list if r.get("status") == "confirmed")
    st.caption(f"{len(rev_list)} 件 | 合計: ¥{month_total:,}")

    if not rev_list:
        st.info("表示する収入データがありません。")
    else:
        for rev in rev_list:
            src_label = SOURCE_LABELS.get(rev.get("source", ""), rev.get("source", ""))
            status_label = REV_STATUS_LABELS.get(rev.get("status", "confirmed"), "")
            with st.container(border=True):
                rc1, rc2 = st.columns([4, 1])
                with rc1:
                    st.markdown(f"**{src_label}** &nbsp; ¥{rev.get('amount',0):,} &nbsp; {status_label}")
                    st.caption(f"📅 {rev.get('date','')} | {rev.get('source_factory','')} | {rev.get('memo','')}")
                with rc2:
                    cur_status = rev.get("status", "confirmed")
                    cur_idx = REVENUE_STATUSES.index(cur_status) if cur_status in REVENUE_STATUSES else 0
                    new_rs = st.selectbox(
                        "ステータス", REVENUE_STATUSES, index=cur_idx,
                        format_func=lambda x: REV_STATUS_LABELS.get(x, x),
                        key=f"rev_st_{rev['revenue_id']}",
                        label_visibility="collapsed",
                    )
                    if new_rs != cur_status:
                        update_revenue(rev["revenue_id"], status=new_rs)
                        st.rerun()
                    if st.button("🗑️", key=f"del_rev_{rev['revenue_id']}"):
                        delete_revenue(rev["revenue_id"])
                        st.rerun()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 3: Expenses
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tabs[2]:
    st.subheader("経費管理")

    with st.expander("➕ 新規経費を記録", expanded=False):
        with st.form("new_exp_form"):
            ef1, ef2, ef3 = st.columns(3)
            e_cat = ef1.selectbox("カテゴリ", EXPENSE_CATEGORIES,
                                   format_func=lambda x: CATEGORY_LABELS.get(x, x))
            e_service = ef2.text_input("サービス名", placeholder="Claude Pro, Runway Gen-3...")
            e_amount = ef3.number_input("金額 (円)", min_value=0, step=100, value=0)
            ef4, ef5, ef6 = st.columns(3)
            e_cycle = ef4.selectbox("請求サイクル", BILLING_CYCLES,
                                    format_func=lambda x: BILLING_LABELS.get(x, x))
            e_date = ef5.date_input("支払日", value=TODAY)
            e_status = ef6.selectbox("ステータス", EXPENSE_STATUSES,
                                     format_func=lambda x: EXP_STATUS_LABELS.get(x, x))
            e_memo = st.text_input("メモ", placeholder="月額プランなど")
            if st.form_submit_button("📉 経費を記録", type="primary"):
                if e_amount > 0 and e_service.strip():
                    create_expense(
                        category=e_cat,
                        service_name=e_service.strip(),
                        amount=int(e_amount),
                        billing_cycle=e_cycle,
                        entry_date=e_date.isoformat(),
                        status=e_status,
                        memo=e_memo.strip(),
                    )
                    st.success("経費を記録しました")
                    st.rerun()
                else:
                    st.error("金額とサービス名は必須です")

    # Filter
    ec1, ec2 = st.columns(2)
    flt_cat = ec1.multiselect("カテゴリフィルター", EXPENSE_CATEGORIES,
                               format_func=lambda x: CATEGORY_LABELS.get(x, x))
    flt_exp_month = ec2.text_input("月フィルター (YYYY-MM)", value=YEAR_MONTH, key="exp_month_filter")

    exp_list = expense_data.get("expenses", [])
    if flt_cat:
        exp_list = [e for e in exp_list if e.get("category") in flt_cat]
    if flt_exp_month:
        exp_list = [e for e in exp_list if e.get("date", "")[:7] == flt_exp_month]
    exp_list = sorted(exp_list, key=lambda e: e.get("date", ""), reverse=True)

    exp_total = sum(e.get("amount", 0) for e in exp_list if e.get("status") == "paid")
    st.caption(f"{len(exp_list)} 件 | 合計: ¥{exp_total:,}")

    if not exp_list:
        st.info("表示する経費データがありません。")
    else:
        for exp in exp_list:
            cat_label = CATEGORY_LABELS.get(exp.get("category", ""), exp.get("category", ""))
            cycle_label = BILLING_LABELS.get(exp.get("billing_cycle", "monthly"), "")
            status_label = EXP_STATUS_LABELS.get(exp.get("status", "paid"), "")
            large = exp.get("amount", 0) >= settings.get("large_expense_threshold", 10000)
            with st.container(border=True):
                ex1, ex2 = st.columns([4, 1])
                with ex1:
                    prefix = "⚠️ " if large and not exp.get("memo", "").strip() else ""
                    st.markdown(f"{prefix}**{exp.get('service_name','')}** &nbsp; ¥{exp.get('amount',0):,} &nbsp; {status_label}")
                    st.caption(f"{cat_label} | {cycle_label} | 📅 {exp.get('date','')} | {exp.get('memo','')}")
                with ex2:
                    cur_es = exp.get("status", "paid")
                    cur_eidx = EXPENSE_STATUSES.index(cur_es) if cur_es in EXPENSE_STATUSES else 0
                    new_es = st.selectbox(
                        "ステータス", EXPENSE_STATUSES, index=cur_eidx,
                        format_func=lambda x: EXP_STATUS_LABELS.get(x, x),
                        key=f"exp_st_{exp['expense_id']}",
                        label_visibility="collapsed",
                    )
                    if new_es != cur_es:
                        update_expense(exp["expense_id"], status=new_es)
                        st.rerun()
                    if st.button("🗑️", key=f"del_exp_{exp['expense_id']}"):
                        delete_expense(exp["expense_id"])
                        st.rerun()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 4: Subscriptions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tabs[3]:
    st.subheader("サブスクリプション管理")

    sub_total = get_monthly_subscription_total(subscription_data)
    upcoming = get_upcoming_renewals(subscription_data, 7)
    su1, su2, su3 = st.columns(3)
    su1.metric("🔄 月額合計",     f"¥{sub_total:,}/月")
    su2.metric("✅ 稼働中",       s_sum["active_subscriptions"])
    su3.metric("📅 7日以内の更新", len(upcoming))

    if upcoming:
        st.warning(f"⚠️ {len(upcoming)} 件のサブスクが7日以内に更新されます")
        for sub in upcoming:
            days = sub.get("_days_until_renewal", 0)
            st.caption(f"  • {sub['name']} — {sub.get('renewal_date','')} ({days}日後) ¥{sub.get('monthly_cost',0):,}/月")

    # Quick add preset
    with st.expander("⚡ プリセットから追加", expanded=False):
        preset_cols = st.columns(4)
        for i, preset in enumerate(PRESET_SERVICES):
            col = preset_cols[i % 4]
            if col.button(
                f"{preset['name']}\n¥{preset['monthly_cost']:,}/月",
                key=f"preset_{i}",
                use_container_width=True,
            ):
                create_subscription(
                    name=preset["name"],
                    monthly_cost=preset["monthly_cost"],
                )
                st.success(f"{preset['name']} を追加しました")
                st.rerun()

    # Create custom subscription
    with st.expander("➕ カスタム登録", expanded=False):
        with st.form("new_sub_form"):
            sf1, sf2, sf3 = st.columns(3)
            s_name = sf1.text_input("サービス名 *", placeholder="Notion, Figma...")
            s_cost = sf2.number_input("月額費用 (円)", min_value=0, step=100, value=0)
            s_day = sf3.number_input("請求日", min_value=1, max_value=31, value=1)
            s_renewal = st.date_input("次回更新日", value=None)
            s_memo = st.text_input("メモ")
            if st.form_submit_button("🔄 サブスクを登録", type="primary"):
                if s_name.strip() and s_cost > 0:
                    create_subscription(
                        name=s_name.strip(),
                        monthly_cost=int(s_cost),
                        billing_day=int(s_day),
                        renewal_date=s_renewal.isoformat() if s_renewal else "",
                        memo=s_memo.strip(),
                    )
                    st.success("サブスクを登録しました")
                    st.rerun()
                else:
                    st.error("サービス名と月額費用は必須です")

    # Subscription list
    subs = subscription_data.get("subscriptions", [])
    active_subs = [s for s in subs if s.get("active", True)]
    inactive_subs = [s for s in subs if not s.get("active", True)]
    active_total = sum(s.get("monthly_cost", 0) for s in active_subs)

    st.caption(f"稼働中: {len(active_subs)} 件 (¥{active_total:,}/月) | 停止中: {len(inactive_subs)} 件")

    for sub in sorted(subs, key=lambda s: (-s.get("active", True), s.get("name", ""))):
        is_active = sub.get("active", True)
        with st.container(border=True):
            sb1, sb2, sb3 = st.columns([4, 1, 1])
            with sb1:
                icon = "🟢" if is_active else "⚫"
                st.markdown(f"{icon} **{sub.get('name','')}** — ¥{sub.get('monthly_cost',0):,}/月")
                renewal = sub.get("renewal_date", "")
                billing = sub.get("billing_day", "")
                st.caption(f"請求日: {billing}日 | 更新: {renewal} | {sub.get('memo','')}")
            with sb2:
                toggle_label = "⏸️ 停止" if is_active else "▶️ 再開"
                if st.button(toggle_label, key=f"toggle_{sub['subscription_id']}"):
                    toggle_active(sub["subscription_id"])
                    st.rerun()
            with sb3:
                if st.button("🗑️ 削除", key=f"del_sub_{sub['subscription_id']}"):
                    delete_subscription(sub["subscription_id"])
                    st.rerun()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 5: ROI Analysis
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tabs[4]:
    st.subheader("ROI分析")

    ra1, ra2, ra3, ra4 = st.columns(4)
    ra1.metric("📈 売上",       f"¥{roi['total_revenue']:,}")
    ra2.metric("📉 経費",       f"¥{roi['total_expense']:,}")
    ra3.metric("💹 純利益",     f"¥{roi['net_profit']:,}")
    ra4.metric("📊 ROI",        f"{roi['roi']}%")

    st.divider()
    st.markdown(f"**🎯 損益分岐点達成率: {roi['target_attainment']}%**")
    st.progress(min(roi["target_attainment"] / 100, 1.0))
    st.caption(f"目標: ¥{roi['break_even_target']:,} | 現在: ¥{roi['total_revenue']:,} | 残: ¥{roi['break_even_remaining']:,}")

    st.divider()

    rg1, rg2 = st.columns(2)
    with rg1:
        st.markdown("**📈 工場別売上**")
        rev_by_fac = roi.get("revenue_by_factory", {})
        if rev_by_fac:
            for fac, amt in sorted(rev_by_fac.items(), key=lambda x: -x[1]):
                pct = (amt / roi["total_revenue"] * 100) if roi["total_revenue"] > 0 else 0
                st.metric(fac, f"¥{amt:,}", f"{pct:.0f}%")
        else:
            st.caption("売上データがありません。")

    with rg2:
        st.markdown("**📉 カテゴリ別経費**")
        exp_by_cat = roi.get("expense_by_category", {})
        if exp_by_cat:
            for cat, amt in sorted(exp_by_cat.items(), key=lambda x: -x[1]):
                label = CATEGORY_LABELS.get(cat, cat)
                pct = (amt / roi["total_expense"] * 100) if roi["total_expense"] > 0 else 0
                st.metric(label, f"¥{amt:,}", f"{pct:.0f}%")
        else:
            st.caption("経費データがありません。")

    st.divider()
    st.subheader("⚙️ 損益分岐点の設定")
    new_be = st.number_input(
        "月次損益分岐点 (円)",
        value=int(settings.get("break_even_monthly", 50000)),
        step=5000, min_value=0,
        key="be_input",
    )
    new_thresh = st.number_input(
        "大きな経費の閾値 (円) — この金額以上の経費にはメモを推奨",
        value=int(settings.get("large_expense_threshold", 10000)),
        step=1000, min_value=0,
        key="thresh_input",
    )
    if st.button("💾 設定を保存", key="save_roi_settings"):
        try:
            import json as _json
            _sp = ROOT / "config" / "accounting_settings.json"
            sd = _json.loads(_sp.read_text(encoding="utf-8")) if _sp.exists() else {}
            sd["break_even_monthly"] = int(new_be)
            sd["large_expense_threshold"] = int(new_thresh)
            _sp.write_text(_json.dumps(sd, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success("設定を保存しました")
            st.rerun()
        except Exception as exc:
            st.error(f"保存エラー: {exc}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tab 6: Monthly Report
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tabs[5]:
    st.subheader("月次レポート")

    report_year = st.number_input("年", min_value=2024, max_value=2030, value=TODAY.year, key="report_yr")
    report_month = st.number_input("月", min_value=1, max_value=12, value=TODAY.month, key="report_mo")
    selected_ym = f"{int(report_year)}-{int(report_month):02d}"

    if st.button("📋 レポートを生成", type="primary", key="gen_report"):
        roi_sel = calculate_roi(revenue_data, expense_data, subscription_data, selected_ym)
        warns_sel = check_audits(revenue_data, expense_data, subscription_data, settings)
        content = generate_monthly_report(
            year_month=selected_ym,
            revenue_data=revenue_data,
            expense_data=expense_data,
            subscription_data=subscription_data,
            roi=roi_sel,
            warnings=warns_sel,
        )
        st.session_state["acc_report_content"] = content
        st.session_state["acc_report_ym"] = selected_ym

    if "acc_report_content" in st.session_state:
        content = st.session_state["acc_report_content"]
        ym = st.session_state.get("acc_report_ym", selected_ym)
        st.divider()
        with st.expander("📄 レポートプレビュー", expanded=True):
            st.markdown(content)

        if st.button("📥 エクスポート (Markdown)", key="export_report_btn"):
            try:
                out_path = export_monthly_report(content, ym)
                rel = out_path.relative_to(ROOT)
                st.success(f"✅ エクスポート完了: `{rel}`")
            except Exception as exc:
                st.error(f"エクスポートエラー: {exc}")

    # List existing reports
    reports_dir = ROOT / "reports" / "monthly"
    if reports_dir.exists():
        existing = sorted(reports_dir.glob("*_accounting_report.md"), reverse=True)
        if existing:
            st.divider()
            st.markdown("**📂 既存のレポート**")
            for rpt in existing[:10]:
                rel = rpt.relative_to(ROOT)
                size = rpt.stat().st_size / 1024
                st.caption(f"📄 `{rel}` ({size:.1f} KB)")
