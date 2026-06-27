"""
Mission Control — Creator Factory OS v4.2
Daily command center: KPI, tasks, factory status, finance, AI CEO message.
No external API calls. Rule-based AI message generation.
"""
import json
import sys
from datetime import date
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src.hq.kpi_manager import load_kpi, update_actual, get_kpi_rows
from src.hq.task_manager import (
    load_tasks, update_task_status, get_task_stats,
    PRIORITY_LABEL, STATUS_LABEL,
)
from src.hq.factory_status import (
    load_factory_status, save_factory_status,
    sync_from_tasks, sync_from_sales, sync_from_accounting,
    FACTORIES, FACTORY_ICONS, STATUS_COLORS,
)
from src.hq.daily_report import generate_report, export_report

APP_VERSION = "4.8"
TODAY = date.today()

st.set_page_config(page_title="Mission Control | Creator Factory OS", page_icon="🎯", layout="wide")

# ── Section 1: Header ──────────────────────────────────────────────────────────

st.title("🎯 Creator Factory OS")
h1, h2, h3 = st.columns(3)
h1.caption(f"📅 {TODAY.strftime('%Y年%m月%d日 (%A)')}")
h2.caption(f"🔨 Build: v{APP_VERSION} Automation Factory")
h3.caption(f"✅ Status: v{APP_VERSION} Automation Factory")

st.divider()

# ── Load all data ──────────────────────────────────────────────────────────────

kpi_data = load_kpi()
tasks_data = load_tasks()
factory_data = load_factory_status()
factory_data = sync_from_tasks(factory_data, tasks_data)
factory_data = sync_from_sales(factory_data)
factory_data = sync_from_accounting(factory_data)

finance_path = ROOT / "config" / "revenue_expense.json"
try:
    finance_data = json.loads(finance_path.read_text(encoding="utf-8")) if finance_path.exists() else {}
except Exception:
    finance_data = {}

today_finance = finance_data.get("today", {})
month_finance = finance_data.get("month", {})

# ── Section 2: Today KPI ──────────────────────────────────────────────────────

st.subheader("📊 Today KPI")

kpi_rows = get_kpi_rows(kpi_data)
targets = kpi_data.get("targets", {})
actuals = kpi_data.get("actuals", {})

with st.expander("KPI実績を更新する", expanded=False):
    st.caption("今日の実績値を入力してください。変更は即時保存されます。")
    upd_cols = st.columns(3)
    editable_keys = [r for r in kpi_rows if r["is_actual"]]
    for i, row in enumerate(editable_keys):
        with upd_cols[i % 3]:
            new_val = st.number_input(
                row["label"],
                min_value=0,
                value=row["actual"],
                step=1 if row["unit"] != "円" else 1000,
                key=f"kpi_input_{row['key']}",
            )
            if new_val != row["actual"]:
                kpi_data = update_actual(row["key"], new_val)
                kpi_rows = get_kpi_rows(kpi_data)
                st.rerun()

kpi_cols = st.columns(len(kpi_rows))
for col, row in zip(kpi_cols, kpi_rows):
    if row["is_actual"]:
        delta_str = f"{row['pct']}%" if row["target"] > 0 else None
        col.metric(
            label=row["label"],
            value=f"{row['actual']:,} {row['unit']}",
            delta=delta_str,
            delta_color="normal",
            help=f"目標: {row['target']:,} {row['unit']}",
        )
    else:
        col.metric(
            label=row["label"],
            value=f"{row['target']:,} {row['unit']}",
        )

st.divider()

# ── Section 3: Today Tasks ─────────────────────────────────────────────────────

st.subheader("✅ Today Tasks")

task_stats = get_task_stats(tasks_data)
ts1, ts2, ts3, ts4 = st.columns(4)
ts1.metric("📋 総タスク数", task_stats["total"])
ts2.metric("✅ 完了", task_stats["done"])
ts3.metric("🔄 進行中", task_stats["in_progress"])
ts4.metric("⏸ 未着手", task_stats["pending"])

if task_stats["total"] > 0:
    st.progress(task_stats["pct"] / 100, text=f"今日の完了率: {task_stats['pct']}%")

st.markdown("")

# Page map for navigation
PAGE_MAP: dict[str, str | None] = {
    "AI動画工場":   "pages/1_Script.py",
    "note投稿工場": "pages/18_Note_Factory.py",
    "SNS投稿工場":  "pages/19_SNS_Factory.py",
    "営業工場":     "pages/21_Sales_Factory.py",
    "会計監査工場": "pages/22_Accounting_Factory.py",
    "開発":         "pages/17_Mission_Control.py",
    "経営":         "pages/8_Dashboard.py",
}


def _task_on_change(task_id: str) -> None:
    checked = st.session_state.get(f"chk_{task_id}", False)
    new_status = "done" if checked else "pending"
    update_task_status(task_id, new_status)


# Group tasks by category for display
CATEGORY_ICONS = {
    "AI動画工場":   "🎬",
    "note投稿工場": "📝",
    "SNS投稿工場":  "📱",
    "営業工場":     "💼",
    "会計監査工場": "💰",
    "開発":         "⚙️",
    "経営":         "🏢",
}

all_tasks = tasks_data.get("tasks", [])

# Sort: high priority first, then by status (in_progress > pending > done)
STATUS_ORDER = {"in_progress": 0, "pending": 1, "done": 2}
PRIORITY_ORDER_MAP = {"high": 0, "medium": 1, "low": 2}
sorted_tasks = sorted(
    all_tasks,
    key=lambda t: (STATUS_ORDER.get(t["status"], 9), PRIORITY_ORDER_MAP.get(t["priority"], 9)),
)

for task in sorted_tasks:
    tid = task["id"]
    cat = task.get("category", "開発")
    cat_icon = CATEGORY_ICONS.get(cat, "📌")
    priority_lbl = PRIORITY_LABEL.get(task.get("priority", "medium"), "🟡 中")
    status = task.get("status", "pending")

    col_chk, col_title, col_cat, col_pri, col_action = st.columns([1, 4, 2, 1.5, 2])

    with col_chk:
        st.checkbox(
            "",
            value=(status == "done"),
            key=f"chk_{tid}",
            on_change=_task_on_change,
            args=(tid,),
        )

    with col_title:
        title_text = f"~~{task['title']}~~" if status == "done" else task["title"]
        status_icon = "✅ " if status == "done" else ("🔄 " if status == "in_progress" else "")
        st.markdown(f"{status_icon}{title_text}")

    with col_cat:
        st.caption(f"{cat_icon} {cat}")

    with col_pri:
        st.caption(priority_lbl)

    with col_action:
        if status != "done":
            btn_key = f"start_{tid}"
            if st.button("▶️ 開始", key=btn_key, use_container_width=True):
                update_task_status(tid, "in_progress")
                st.session_state[f"show_link_{tid}"] = True
                st.rerun()

    # Show page link after start
    if st.session_state.get(f"show_link_{tid}") or status == "in_progress":
        task_page = task.get("page_link") or PAGE_MAP.get(cat)
        if task_page and (ROOT / task_page).exists():
            link_col1, link_col2 = st.columns([1, 11])
            with link_col2:
                st.page_link(task_page, label=f"→ {cat}のページを開く", icon="🔗")
        elif task_page is None or not (ROOT / (task_page or "")).exists():
            link_col1, link_col2 = st.columns([1, 11])
            with link_col2:
                guidance = {
                    "note投稿工場":  "noteエディタを開いて記事を作成してください。",
                    "SNS投稿工場":   "Twitter/X・Instagram等のSNSを開いて投稿してください。",
                    "営業工場":      "メールクライアントを開いて営業メールを送信してください。",
                    "会計監査工場":  "スプレッドシートを開いて収支を記録してください。",
                }
                st.caption(f"💡 {guidance.get(cat, 'このタスクは手動で実施してください。')}")

st.divider()

# ── Section 3.5: Projects ─────────────────────────────────────────────────────

st.subheader("🗂️ Projects")
st.caption("Creator Factory OS はプロジェクト中心のOSです。工場はプロジェクトのモジュールです。")

try:
    from src.core.project_manager import get_all_projects
    from src.core.project_registry import ProjectRegistry
    from src.core.factory_interfaces import FACTORY_ICONS as _FICONS

    _sys = ProjectRegistry.get_system_summary()
    _ps1, _ps2, _ps3, _ps4 = st.columns(4)
    _ps1.metric("📁 プロジェクト数", _sys["total_projects"])
    _ps2.metric("🟢 稼働中", _sys["active_projects"])
    _ps3.metric("🏭 工場数", _sys["total_factories"])
    _ps4.metric("✅ 正常工場", f"{_sys['healthy_factories']}/{_sys['total_factories']}")

    _projects = get_all_projects()
    _STATUS_DOT = {"active": "🟢", "paused": "🟡", "completed": "✅", "archived": "⬜"}
    _proj_cols = st.columns(min(len(_projects), 3)) if _projects else []
    for _i, _proj in enumerate(_projects):
        _col = _proj_cols[_i % 3] if _proj_cols else st.container()
        with _col:
            with st.container(border=True):
                _dot = _STATUS_DOT.get(_proj.status, "⚪")
                st.markdown(f"**{_dot} {_proj.name}**")
                st.caption(f"👤 {_proj.owner}  |  優先度: {_proj.priority}  |  進捗: {_proj.progress:.0f}%")
                if _proj.progress > 0:
                    st.progress(_proj.progress / 100)
                _fac_icons = " ".join(_FICONS.get(f, "🏭") for f in _proj.factories)
                st.caption(f"工場: {_fac_icons}")
                if _proj.description:
                    st.caption(_proj.description)
except Exception:
    st.caption("Projects — `src/core/project_manager.py` をインポートできません")

st.divider()

# ── Section 4: Factory Status (Factory Modules) ───────────────────────────────

st.subheader("🏭 Factory Status")

factory_cols = st.columns(3)
for i, factory_name in enumerate(FACTORIES):
    info = factory_data.get(factory_name, {})
    status = info.get("status", "idle")
    icon = FACTORY_ICONS.get(factory_name, "🏭")
    status_dot = STATUS_COLORS.get(status, "⚪")
    warnings = info.get("warning_count", 0)

    with factory_cols[i % 3]:
        with st.container(border=True):
            st.markdown(f"**{icon} {factory_name}**  {status_dot}")
            fc1, fc2 = st.columns(2)
            fc1.metric("稼働中", info.get("active_items", 0))
            fc2.metric("完了(今日)", info.get("completed_today", 0))
            if warnings > 0:
                st.warning(f"⚠️ 警告: {warnings}件")
            st.caption(f"📌 {info.get('next_action', '—')}")

st.divider()

# ── Section 5: Finance Snapshot ───────────────────────────────────────────────

st.subheader("💰 Finance Snapshot")

today_rev = today_finance.get("revenue", 0)
today_exp = today_finance.get("expense", 0)
month_rev = month_finance.get("revenue", 0)
month_exp = month_finance.get("expense", 0)
month_profit = month_rev - month_exp
breakeven = month_finance.get("breakeven", 50000)
breakeven_remaining = max(0, breakeven - month_rev)
roi = (month_profit / month_exp * 100) if month_exp > 0 else 0.0

with st.expander("財務データを更新する", expanded=False):
    fe1, fe2, fe3, fe4 = st.columns(4)
    with fe1:
        new_today_rev = st.number_input("今日の売上 (円)", min_value=0, value=today_rev, step=1000, key="fin_today_rev")
    with fe2:
        new_today_exp = st.number_input("今日の費用 (円)", min_value=0, value=today_exp, step=1000, key="fin_today_exp")
    with fe3:
        new_month_rev = st.number_input("今月売上 (円)", min_value=0, value=month_rev, step=1000, key="fin_month_rev")
    with fe4:
        new_month_exp = st.number_input("今月費用 (円)", min_value=0, value=month_exp, step=1000, key="fin_month_exp")

    if st.button("💾 財務データを保存", key="fin_save"):
        finance_data["today"] = {
            "date": TODAY.isoformat(),
            "revenue": new_today_rev,
            "expense": new_today_exp,
        }
        finance_data["month"] = {
            "year_month": TODAY.strftime("%Y-%m"),
            "revenue": new_month_rev,
            "expense": new_month_exp,
            "breakeven": breakeven,
        }
        finance_path.write_text(json.dumps(finance_data, ensure_ascii=False, indent=2), encoding="utf-8")
        st.success("財務データを保存しました")
        st.rerun()

fn1, fn2, fn3, fn4, fn5, fn6 = st.columns(6)
fn1.metric("今日の売上", f"¥{today_rev:,}")
fn2.metric("今月売上", f"¥{month_rev:,}")
fn3.metric("今月費用", f"¥{month_exp:,}")
fn4.metric("今月利益", f"¥{month_profit:,}", delta_color="normal")
fn5.metric("ROI", f"{roi:.1f}%")
fn6.metric("損益分岐点まで", f"¥{breakeven_remaining:,}")

if month_exp > 0 and month_rev < month_exp:
    st.error("⚠️ 今月の費用が売上を上回っています。無料ツールを優先してコスト削減を検討してください。")
elif month_rev >= breakeven:
    st.success("✅ 今月の損益分岐点を達成しています！")

st.divider()

# ── Section 6: AI CEO Daily Message ──────────────────────────────────────────

st.subheader("🤖 AI CEO Daily Message")

kpi_rows_refresh = get_kpi_rows(kpi_data)
task_stats_refresh = get_task_stats(tasks_data)
tasks_all = tasks_data.get("tasks", [])


def _generate_ceo_message(stats: dict, kpi: list, fin_today_rev: int, fin_month_rev: int, fin_month_exp: int) -> str:
    messages: list[str] = []

    video_row = next((r for r in kpi if r["key"] == "video_count"), None)
    note_row = next((r for r in kpi if r["key"] == "note_posts"), None)
    sns_row = next((r for r in kpi if r["key"] == "sns_posts"), None)
    sales_row = next((r for r in kpi if r["key"] == "sales_calls"), None)
    sales_actual = next((r["actual"] for r in kpi if r["key"] == "sales_actual"), 0)
    sales_target_val = next((r["target"] for r in kpi if r["key"] == "sales_actual"), 1)

    # Finance check
    if fin_month_exp > 0 and fin_month_rev < fin_month_exp:
        messages.append("費用が売上を上回っています。無料運用を優先してください。")

    # All tasks done
    if stats["done"] == stats["total"] and stats["total"] > 0:
        messages.append("本日の主要タスクはすべて完了しています。素晴らしい成果です！")
        return " ".join(messages) if messages else "本日の主要タスクは完了しています。"

    # Video task not done
    video_tasks_pending = [t for t in tasks_all if t.get("category") == "AI動画工場" and t["status"] != "done"]
    if video_tasks_pending:
        messages.append("今日は動画制作を優先してください。")

    # Note not posted
    note_tasks_pending = [t for t in tasks_all if t.get("category") == "note投稿工場" and t["status"] != "done"]
    if note_tasks_pending:
        messages.append("note記事の投稿がまだです。コンテンツ発信を忘れずに。")

    # SNS not done
    sns_tasks_pending = [t for t in tasks_all if t.get("category") == "SNS投稿工場" and t["status"] != "done"]
    if sns_tasks_pending:
        messages.append("SNS投稿でオーディエンスとのエンゲージメントを高めましょう。")

    # Sales
    sales_tasks_pending = [t for t in tasks_all if t.get("category") == "営業工場" and t["status"] != "done"]
    if sales_tasks_pending:
        messages.append("営業活動を積み重ねることで収益につながります。")

    # KPI achievement
    if sales_actual >= sales_target_val and sales_target_val > 0:
        messages.append(f"本日の売上目標 ¥{sales_target_val:,} を達成しました！")

    # Progress based message
    pct = stats["pct"]
    if pct >= 80 and stats["done"] < stats["total"]:
        messages.append(f"今日の進捗は{pct}%です。あと少しで全タスク完了です。")
    elif pct == 0:
        messages.append("今日の作業をまだ開始していません。最優先タスクから着手してください。")
    elif pct < 50:
        messages.append(f"今日の進捗は{pct}%です。集中して作業を進めましょう。")

    if not messages:
        messages.append("今日も着実に前進しています。各工場のタスクを確認してください。")

    return " ".join(messages)


ceo_message = _generate_ceo_message(
    task_stats_refresh, kpi_rows_refresh,
    today_rev, month_rev, month_exp,
)

st.info(f"💬 {ceo_message}")

st.divider()

# ── Section 7: One-click Navigation ──────────────────────────────────────────

st.subheader("🚀 Quick Navigation")

NAV_ITEMS = [
    ("🎬 AI動画工場を開く",      "pages/1_Script.py"),
    ("📝 note投稿工場を開く",    "pages/18_Note_Factory.py"),
    ("📱 SNS投稿工場を開く",     "pages/19_SNS_Factory.py"),
    ("💼 営業工場を開く",        "pages/21_Sales_Factory.py"),
    ("💰 会計監査工場を開く",    "pages/22_Accounting_Factory.py"),
    ("📊 ダッシュボードを開く",  "pages/8_Dashboard.py"),
    ("🔍 承認アシスタント",      "pages/20_Approval_Assistant.py"),
]

nav_cols = st.columns(3)
for i, (label, page_path) in enumerate(NAV_ITEMS):
    with nav_cols[i % 3]:
        if page_path and (ROOT / page_path).exists():
            st.page_link(page_path, label=label, use_container_width=True)
        else:
            st.button(label + " 🚧", disabled=True, use_container_width=True,
                      key=f"nav_coming_{i}", help="Coming Soon — このページはまだ実装されていません")

st.divider()

# ── Section 7.5: Dev Tools ────────────────────────────────────────────────────

st.subheader("🛠️ Dev Tools")

dev_c1, dev_c2 = st.columns([3, 2])

with dev_c1:
    st.markdown("**🔍 Claude承認アシスタント**")
    st.caption("Claude Codeの確認プロンプトを日本語訳してリスク分類します。")
    try:
        from src.devtools.approval_analyzer import get_latest_risk
        _latest = get_latest_risk()
        if _latest:
            _risk_icon = _latest.get("risk_icon", "🟢")
            _risk_label = _latest.get("risk_label", "安全") if "risk_label" in _latest else _latest.get("risk_level", "safe")
            _summary = _latest.get("summary", "")[:60]
            _ts = _latest.get("timestamp", "")[:16].replace("T", " ")
            st.caption(f"最終分析: {_ts} | {_risk_icon} {_risk_label}")
            st.caption(f"内容: {_summary}")
        else:
            st.caption("まだ分析履歴がありません。")
    except Exception:
        st.caption("承認アシスタントのデータを取得できませんでした。")

with dev_c2:
    approval_page = ROOT / "pages" / "20_Approval_Assistant.py"
    if approval_page.exists():
        st.page_link("pages/20_Approval_Assistant.py", label="🔍 承認アシスタントを開く →",
                     use_container_width=True)
    else:
        st.button("🔍 承認アシスタント 🚧", disabled=True, use_container_width=True,
                  key="nav_approval", help="Coming Soon")

st.divider()

# ── Section 7.6: Sales Factory ────────────────────────────────────────────────

st.subheader("💼 営業工場")

sales_c1, sales_c2 = st.columns([3, 2])

with sales_c1:
    st.markdown("**CRM · リード管理 · 商談 · フォロー · 売上予測**")
    try:
        from src.factories.sales.lead_manager import load_leads, get_factory_summary as _lead_sum
        from src.factories.sales.followup_manager import load_followups, get_followup_summary as _fu_sum
        from src.factories.sales.deal_manager import load_deals, get_factory_summary as _deal_sum
        from src.factories.sales.sales_forecast import calculate_forecast as _calc_fc
        _ld = load_leads()
        _fd = load_deals()
        _fud = load_followups()
        _ls = _lead_sum(_ld)
        _ds = _deal_sum(_fd)
        _fus = _fu_sum(_fud)
        _fc = _calc_fc(_ld, _fd)
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("👥 リード", _ls["total"])
        sc2.metric("🤝 商談中", _ds["active"])
        sc3.metric("⚠️ 要フォロー", _fus["needs_followup"])
        sc4.metric("💰 今月予測", f"¥{_fc['expected_monthly']:,}")
        if _fus["overdue"] > 0:
            st.caption(f"🔴 フォロー期限超過 {_fus['overdue']} 件")
        elif _fus["today"] > 0:
            st.caption(f"📅 今日のフォロー {_fus['today']} 件")
        else:
            st.caption(f"✅ フォロー期限内 | 成約: {_ds['contracted']} 件")
    except Exception:
        st.caption("営業データを読み込めませんでした。")

with sales_c2:
    sales_page = ROOT / "pages" / "21_Sales_Factory.py"
    if sales_page.exists():
        st.page_link("pages/21_Sales_Factory.py", label="💼 営業工場を開く →",
                     use_container_width=True)
    else:
        st.button("💼 営業工場 🚧", disabled=True, use_container_width=True,
                  key="nav_sales", help="Coming Soon")

st.divider()

# ── Section 7.7: Accounting Factory ──────────────────────────────────────────

st.subheader("💰 会計監査工場")

acc_c1, acc_c2 = st.columns([3, 2])

with acc_c1:
    st.markdown("**収支管理 · ROI · サブスク · 監査アラート**")
    try:
        from src.factories.accounting.revenue_manager import load_revenue, get_factory_summary as _acc_rev_sum
        from src.factories.accounting.expense_manager import load_expenses
        from src.factories.accounting.subscription_manager import load_subscriptions, get_monthly_subscription_total
        from src.factories.accounting.roi_calculator import calculate_roi as _calc_roi
        from src.factories.accounting.audit_checker import check_audits, get_audit_summary
        import datetime as _dt
        _ym = _dt.date.today().strftime("%Y-%m")
        _rd = load_revenue()
        _ed = load_expenses()
        _sd = load_subscriptions()
        _rs = _acc_rev_sum(_rd)
        _roi = _calc_roi(_rd, _ed, _sd, _ym)
        _warns = check_audits(_rd, _ed, _sd)
        _as = get_audit_summary(_warns)
        ac1, ac2, ac3, ac4 = st.columns(4)
        ac1.metric("💰 今日の売上",   f"¥{_rs['today_revenue']:,}")
        ac2.metric("💹 今月利益",     f"¥{_roi['net_profit']:,}")
        ac3.metric("📉 今月経費",     f"¥{_roi['total_expense']:,}")
        ac4.metric("🔔 監査アラート",  _as["total"])
        if _as["errors"] > 0:
            st.caption(f"🔴 エラー {_as['errors']} 件 | ROI: {_roi['roi']}%")
        elif _as["warning"] > 0:
            st.caption(f"🟠 警告 {_as['warning']} 件 | ROI: {_roi['roi']}%")
        else:
            st.caption(f"✅ 異常なし | ROI: {_roi['roi']}% | 達成率: {_roi['target_attainment']}%")
    except Exception:
        st.caption("会計データを読み込めませんでした。")

with acc_c2:
    acc_page = ROOT / "pages" / "22_Accounting_Factory.py"
    if acc_page.exists():
        st.page_link("pages/22_Accounting_Factory.py", label="💰 会計監査工場を開く →",
                     use_container_width=True)
    else:
        st.button("💰 会計監査工場 🚧", disabled=True, use_container_width=True,
                  key="nav_accounting", help="Coming Soon")

st.divider()

# ── Section 7.8: Core Architecture ───────────────────────────────────────────

st.subheader("🏗️ Core Architecture")

arch_c1, arch_c2 = st.columns([3, 2])

with arch_c1:
    st.markdown("**Project Registry · Factory Registry · Event Bus**")
    try:
        from src.core.project_registry import ProjectRegistry as _PR
        _arch_sys = _PR.get_system_summary()
        _health_icon = {"ok": "✅", "degraded": "🟡", "failed": "🔴"}.get(
            _arch_sys["system_health"], "⚪"
        )
        aa1, aa2, aa3, aa4 = st.columns(4)
        aa1.metric("📁 プロジェクト",  _arch_sys["total_projects"])
        aa2.metric("🏭 工場数",       _arch_sys["total_factories"])
        aa3.metric("✅ 正常工場",      _arch_sys["healthy_factories"])
        aa4.metric("💊 システム健全性", f"{_arch_sys['health_pct']}%")
        st.caption(f"{_health_icon} System Health: {_arch_sys['system_health'].upper()}")
    except Exception:
        st.caption("Core Architecture データを読み込めませんでした。")

with arch_c2:
    st.caption("**Architecture Docs**")
    for _doc_name, _doc_path in [
        ("FACTORY_SPEC.md",            "docs/FACTORY_SPEC.md"),
        ("PROJECT_SPEC.md",            "docs/PROJECT_SPEC.md"),
        ("ARCHITECTURE_DECISIONS.md",  "docs/ARCHITECTURE_DECISIONS.md"),
    ]:
        if (ROOT / _doc_path).exists():
            st.caption(f"✅ {_doc_name}")
        else:
            st.caption(f"❌ {_doc_name}")

st.divider()

# ── Section 7.9: Analytics Factory ───────────────────────────────────────────

st.subheader("📊 アナリティクス工場")

anl_c1, anl_c2 = st.columns([3, 2])

with anl_c1:
    st.markdown("**全工場 · KPI · ROI · プロジェクト · インサイト分析**")
    try:
        from src.factories.analytics.analytics_collector import collect_snapshot as _anl_snap
        from src.factories.analytics.kpi_analyzer       import analyze_kpi as _anl_kpi
        from src.factories.analytics.factory_analyzer   import analyze_factories as _anl_fac
        from src.factories.analytics.roi_analyzer       import analyze_roi as _anl_roi
        from src.factories.analytics.trend_reporter     import synthesize_insights as _anl_syn
        from src.factories.analytics.kpi_analyzer       import get_kpi_insights as _anl_ki
        from src.factories.analytics.factory_analyzer   import get_factory_insights as _anl_fi
        from src.factories.analytics.project_analyzer   import analyze_projects as _anl_proj, get_project_insights as _anl_pi
        from src.factories.analytics.roi_analyzer       import get_roi_insights as _anl_ri
        _s   = _anl_snap()
        _ka  = _anl_kpi(_s.get("kpi", {}))
        _fa  = _anl_fac()
        _pa  = _anl_proj()
        _ra  = _anl_roi(_s.get("accounting_revenue", {}), _s.get("accounting_expenses", {}),
                        _s.get("accounting_subscriptions", {}), _s.get("sales_deals", {}))
        _ins = _anl_syn(_anl_ki(_ka), _anl_fi(_fa), _anl_pi(_pa), _anl_ri(_ra))
        _errs = sum(1 for i in _ins if i.startswith("🔴"))
        _warn = sum(1 for i in _ins if i.startswith("⚠️"))
        ac1, ac2, ac3, ac4 = st.columns(4)
        ac1.metric("🏭 工場健全性",   f"{_fa['health_pct']}%")
        ac2.metric("📊 KPI達成率",    f"{_ka['avg_pct']}%")
        ac3.metric("📁 稼働PJ数",     _pa["active"])
        ac4.metric("💡 インサイト数",  len(_ins))
        if _errs > 0:
            st.caption(f"🔴 エラー {_errs} 件 | ⚠️ 警告 {_warn} 件")
        elif _warn > 0:
            st.caption(f"⚠️ 警告 {_warn} 件 | 工場健全性 {_fa['health_pct']}%")
        else:
            st.caption(f"✅ 異常なし | ROI: {_ra['roi']}% | 今月利益: ¥{_ra['net_profit']:,}")
    except Exception:
        st.caption("アナリティクスデータを読み込めませんでした。")

with anl_c2:
    anl_page = ROOT / "pages" / "23_Analytics_Factory.py"
    if anl_page.exists():
        st.page_link("pages/23_Analytics_Factory.py", label="📊 アナリティクス工場を開く →",
                     use_container_width=True)
    else:
        st.button("📊 アナリティクス工場 🚧", disabled=True, use_container_width=True,
                  key="nav_analytics", help="Coming Soon")

st.divider()

# ── Section 7.10: Automation Factory ─────────────────────────────────────────

st.subheader("⚙️ 自動化工場")

auto_c1, auto_c2 = st.columns([3, 2])

with auto_c1:
    st.markdown("**ルールベース工場間ワークフロー自動化 — 安全優先・ドライランデフォルト**")
    try:
        from src.factories.automation.workflow_manager   import get_workflow_summary as _auto_wfs
        from src.factories.automation.automation_reporter import get_run_summary as _auto_rs
        _awsum = _auto_wfs()
        _arsum = _auto_rs()
        auc1, auc2, auc3, auc4 = st.columns(4)
        auc1.metric("🔧 ワークフロー数",  _awsum["total"])
        auc2.metric("🟢 有効",            _awsum["enabled"])
        auc3.metric("▶️ 総実行回数",      _arsum["total_runs"])
        auc4.metric("✅ 成功アクション",  _arsum["successful"])
        st.caption(f"ドライラン実行: {_arsum['dry_run_count']} 件 | 最終実行: {_arsum['last_run']}")
    except Exception:
        st.caption("自動化データを読み込めませんでした。")

with auto_c2:
    auto_page = ROOT / "pages" / "24_Automation_Factory.py"
    if auto_page.exists():
        st.page_link("pages/24_Automation_Factory.py", label="⚙️ 自動化工場を開く →",
                     use_container_width=True)
    else:
        st.button("⚙️ 自動化工場 🚧", disabled=True, use_container_width=True,
                  key="nav_automation", help="Coming Soon")

st.divider()

# ── Section 8: Daily Report ───────────────────────────────────────────────────

st.subheader("📝 Daily Report")

report_content = generate_report(kpi_data, tasks_data, finance_data, ceo_message)

with st.expander("レポートプレビュー", expanded=False):
    st.markdown(report_content)

rc1, rc2 = st.columns(2)

with rc1:
    if st.button("📄 レポートをエクスポート", type="primary", use_container_width=True, key="export_report"):
        try:
            out_path = export_report(report_content)
            rel = out_path.relative_to(ROOT)
            st.success(f"✅ エクスポート完了: `{rel}`")
            st.session_state["last_report_path"] = str(out_path)
        except Exception as exc:
            st.error(f"エクスポートエラー: {exc}")

with rc2:
    st.download_button(
        label="⬇️ Markdownをダウンロード",
        data=report_content.encode("utf-8"),
        file_name=f"{TODAY.isoformat()}_daily_report.md",
        mime="text/markdown",
        use_container_width=True,
        key="dl_report",
    )

if st.session_state.get("last_report_path"):
    st.caption(f"最後のエクスポート先: `{st.session_state['last_report_path']}`")
