"""Scheduler ページ。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="Scheduler", page_icon="⏰", layout="wide")
st.title("⏰ Job Scheduler")
st.caption("Workflow の時間・イベント起動スケジューリング")

from src.job_scheduler.engine import get_job_engine, JobEngine
from src.job_scheduler.job    import TriggerType, JobStatus
from dashboard.utils          import init_kernel, STATUS_COLORS

@st.cache_resource(ttl=300)
def _kernel():
    return init_kernel()

kernel = _kernel()
engine = get_job_engine()

# エンジンが未起動なら起動
if not engine.is_running():
    engine.start()
    st.toast("Job Engine を起動しました", icon="⏰")

tab1, tab2 = st.tabs(["📋 ジョブ一覧", "➕ 新規スケジュール"])

# ── Tab1: ジョブ一覧 ─────────────────────────────────────────────
with tab1:
    jobs = engine.list_jobs()

    col1, col2, col3 = st.columns(3)
    col1.metric("登録ジョブ", engine.count())
    col2.metric("稼働中", sum(1 for j in jobs if j.status == JobStatus.ACTIVE))
    col3.metric("停止中", sum(1 for j in jobs if j.status == JobStatus.PAUSED))

    if not jobs:
        st.info("スケジュール済みジョブがありません。「新規スケジュール」タブから追加してください。")
    else:
        for job in jobs:
            status_color = STATUS_COLORS.get(job.status.value, "#888")
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 3])
                with col1:
                    st.markdown(f"**{job.name}**")
                    st.caption(f"`{job.workflow_name}`")
                with col2:
                    trigger = job.trigger
                    if trigger.type == TriggerType.DAILY:
                        st.write(f"🔁 毎日 {trigger.run_at}")
                    elif trigger.type == TriggerType.WEEKLY:
                        days = ["月","火","水","木","金","土","日"]
                        day  = days[trigger.weekday] if trigger.weekday is not None else "?"
                        st.write(f"🔁 毎週{day} {trigger.run_at}")
                    elif trigger.type == TriggerType.INTERVAL:
                        st.write(f"⏱ {trigger.interval_min}分ごと")
                    elif trigger.type == TriggerType.ONCE:
                        st.write(f"1️⃣ {trigger.run_once_at}")
                    else:
                        st.write("👆 手動のみ")
                with col3:
                    st.markdown(
                        f"<span style='color:{status_color};font-weight:600;'>"
                        f"● {job.status.value}</span>",
                        unsafe_allow_html=True,
                    )
                    if job.next_run_at:
                        st.caption(f"次回: {job.next_run_at[:16]}")
                    st.caption(f"実行: {job.run_count}回")
                with col4:
                    btn_col1, btn_col2, btn_col3 = st.columns(3)
                    with btn_col1:
                        if st.button("▶ 今すぐ", key=f"run_{job.job_id}"):
                            with st.spinner("実行中..."):
                                rec = engine.run_now(job.job_id)
                            if rec.success:
                                st.success(f"完了 ({rec.duration_ms}ms)")
                            else:
                                st.error(f"失敗: {rec.error}")
                    with btn_col2:
                        if job.status == JobStatus.ACTIVE:
                            if st.button("⏸", key=f"pause_{job.job_id}"):
                                engine.pause(job.job_id)
                                st.rerun()
                        else:
                            if st.button("▶", key=f"resume_{job.job_id}"):
                                engine.resume(job.job_id)
                                st.rerun()
                    with btn_col3:
                        if st.button("🗑", key=f"del_{job.job_id}", type="secondary"):
                            engine.remove_job(job.job_id)
                            st.rerun()

    if st.button("🔄 更新"):
        st.rerun()

# ── Tab2: 新規スケジュール ───────────────────────────────────────
with tab2:
    st.subheader("新しいスケジュールジョブを作成")

    all_wf = sorted(kernel.registry.list_workflows())

    with st.form("new_job_form"):
        col1, col2 = st.columns(2)
        with col1:
            job_name    = st.text_input("ジョブ名 *", placeholder="毎日SNS投稿")
            workflow    = st.selectbox("Workflow *", all_wf)
            trigger_opt = st.selectbox(
                "トリガー",
                ["manual", "daily", "weekly", "interval", "once"],
                format_func=lambda x: {
                    "manual":   "👆 手動のみ",
                    "daily":    "🔁 毎日",
                    "weekly":   "📅 毎週",
                    "interval": "⏱ 定期実行",
                    "once":     "1️⃣ 1回だけ",
                }[x],
            )
        with col2:
            run_at      = st.text_input("実行時刻 (HH:MM)", value="09:00",
                                         help="daily/weekly の場合に使用")
            weekday_opt = st.selectbox("曜日", ["月(0)","火(1)","水(2)","木(3)","金(4)","土(5)","日(6)"],
                                        help="weekly の場合に使用")
            interval_min= st.number_input("実行間隔 (分)", value=60, min_value=1, max_value=1440,
                                           help="interval の場合に使用")
            run_once_at = st.text_input("実行日時 (ISO8601)", value="",
                                         placeholder="2026-07-01T09:00:00",
                                         help="once の場合に使用")

        context_json = st.text_area(
            "コンテキスト (JSON)",
            value="{}",
            height=80,
            help='例: {"topic": "AI動画", "tone": "プロフェッショナル"}',
        )

        submit = st.form_submit_button("📅 スケジュール登録", type="primary")

    if submit:
        import json
        if not job_name or not workflow:
            st.error("ジョブ名と Workflow は必須です。")
        else:
            try:
                context = json.loads(context_json)
            except Exception:
                context = {}

            weekday = int(weekday_opt.split("(")[1].rstrip(")"))
            trigger_map = {
                "manual":   TriggerType.MANUAL,
                "daily":    TriggerType.DAILY,
                "weekly":   TriggerType.WEEKLY,
                "interval": TriggerType.INTERVAL,
                "once":     TriggerType.ONCE,
            }
            job = JobEngine.create_job(
                name         = job_name,
                workflow_name= workflow,
                trigger_type = trigger_map[trigger_opt],
                context      = context,
                run_at       = run_at if trigger_opt in ("daily","weekly") else None,
                weekday      = weekday if trigger_opt == "weekly" else None,
                interval_min = int(interval_min) if trigger_opt == "interval" else None,
                run_once_at  = run_once_at or None,
            )
            engine.add_job(job)
            st.success(f"✓ ジョブ '{job_name}' を登録しました！次回実行: {job.next_run_at or 'なし（手動のみ）'}")
            st.rerun()
