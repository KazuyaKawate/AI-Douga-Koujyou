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
    sync_from_tasks, FACTORIES, FACTORY_ICONS, STATUS_COLORS,
)
from src.hq.daily_report import generate_report, export_report

APP_VERSION = "4.4.1"
TODAY = date.today()

st.set_page_config(page_title="Mission Control | Creator Factory OS", page_icon="🎯", layout="wide")

# ── Section 1: Header ──────────────────────────────────────────────────────────

st.title("🎯 Creator Factory OS")
h1, h2, h3 = st.columns(3)
h1.caption(f"📅 {TODAY.strftime('%Y年%m月%d日 (%A)')}")
h2.caption(f"🔨 Build: v{APP_VERSION} Approval Assistant")
h3.caption(f"✅ Status: v{APP_VERSION} Approval Assistant")

st.divider()

# ── Load all data ──────────────────────────────────────────────────────────────

kpi_data = load_kpi()
tasks_data = load_tasks()
factory_data = load_factory_status()
factory_data = sync_from_tasks(factory_data, tasks_data)

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
    "営業工場":     None,
    "会計監査工場": None,
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

# ── Section 4: Factory Status ─────────────────────────────────────────────────

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
    ("💼 営業工場を開く",        None),
    ("💰 会計監査工場を開く",    None),
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
