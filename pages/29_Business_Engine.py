from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from src.business_engine.manager import BusinessEngineStore, GEMINI_RUNTIME_JOB_TYPES, JOB_TYPES, REVENUE_STAGES
from src.business_engine.automation import RevenueAutomation
from src.business_engine.scheduler_daemon import SchedulerDaemon
from src.business_engine.worker import BusinessWorker
from src.core.version import get_version_label
from src.providers.gemini_cli_provider import GeminiCLIProvider

st.set_page_config(page_title="Business Engine", page_icon="📈", layout="wide")

store = BusinessEngineStore()
automation = RevenueAutomation(store)
scheduler = SchedulerDaemon(store)
data = store.load()
summary = store.pipeline_summary()
forecast = store.earnings_forecast()
monitor = store.execution_monitor()
revenue_summary = automation.dashboard_summary()
beta_metrics = store.beta_metrics()
adapter_registry = store.adapter_registry()
ai_runtime = store.ai_runtime_summary()
gemini_cli = GeminiCLIProvider(timeout_seconds=10, retries=1)
gemini_health = gemini_cli.health()

st.title("📈 Business Engine")
st.caption(f"Revenue, scheduling, KPI, forecast, and retry control | {get_version_label()} | Local-first")
st.info("Local-first mode: external generation APIs are disabled by default. This page records plans and local execution state only.")

tabs = st.tabs([
    "📊 Dashboard",
    "💰 Revenue Pipeline",
    "🗓️ Scheduler",
    "🎯 Daily KPI",
    "📈 Forecast",
    "🧾 History",
    "🔁 Retry Queue",
    "🤖 Automation",
    "🧠 AI Runtime",
    "🔌 Adapters",
])

with tabs[0]:
    worker = monitor.get("worker", {})
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Today's Revenue", f"¥{revenue_summary['today_revenue']:,}")
    c2.metric("Projected Monthly", f"¥{revenue_summary['projected_monthly_revenue']:,}")
    c3.metric("Article Queue", revenue_summary["article_queue"])
    c4.metric("Post Queue", revenue_summary["post_queue"])
    c5.metric("Affiliate Queue", revenue_summary["affiliate_queue"])
    c6.metric("SEO Queue", revenue_summary["seo_queue"])

    s1, s2, s3, s4, s5, s6 = st.columns(6)
    s1.metric("Worker Status", worker.get("status", "idle"))
    s2.metric("Queue Length", monitor["queue_length"])
    s3.metric("Completed Today", monitor["completed_today"])
    s4.metric("Failed Today", monitor["failed_today"])
    s5.metric("Completed Jobs", revenue_summary["completed_jobs"])
    s6.metric("Failed Jobs", revenue_summary["failed_jobs"])

    st.divider()
    b1, b2, b3, b4, b5, b6 = st.columns(6)
    b1.metric("Scheduler Status", beta_metrics["scheduler_status"])
    b2.metric("Active Adapter", beta_metrics["active_adapter"])
    b3.metric("API Status", beta_metrics["api_status"])
    b4.metric("Total Articles", beta_metrics["total_articles"])
    b5.metric("Total SNS Posts", beta_metrics["total_sns_posts"])
    b6.metric("Total Affiliate Links", beta_metrics["total_affiliate_links"])

    p1, p2, p3, p4, p5, p6, p7 = st.columns(7)
    p1.metric("Current Provider", beta_metrics["current_provider"])
    p2.metric("Provider Health", beta_metrics["provider_health"])
    p3.metric("Available Providers", beta_metrics["available_providers"])
    p4.metric("Last Provider Call", beta_metrics["last_provider_call"])
    p5.metric("Generation Time", f"{beta_metrics['generation_time_ms']} ms")
    p6.metric("Token Usage", beta_metrics["estimated_token_usage"])
    p7.metric("Provider Errors", beta_metrics["provider_errors"])

    r1, r2, r3, r4, r5, r6 = st.columns(6)
    r1.metric("AI Runtime", ai_runtime["provider"])
    r2.metric("Gemini CLI Status", gemini_health["status"])
    r3.metric("Gemini Version", gemini_health["version"] or "Unknown")
    r4.metric("Prompt Queue", ai_runtime["prompt_queue"])
    r5.metric("Average Tokens", ai_runtime["average_tokens"])
    r6.metric("Average Cost", f"¥{ai_runtime['average_cost_yen']}")

    q1, q2, q3, q4, q5, q6 = st.columns(6)
    q1.metric("Pending Reviews", beta_metrics["pending_reviews"])
    q2.metric("Approved Today", beta_metrics["approved_today"])
    q3.metric("Rejected Today", beta_metrics["rejected_today"])
    q4.metric("Revision Requested", beta_metrics["revision_requested"])
    q5.metric("Publish Ready", beta_metrics["publish_ready"])
    q6.metric("Risk Warnings", beta_metrics["risk_warnings"])

    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Pending Exports", beta_metrics["pending_exports"])
    e2.metric("Completed Exports", beta_metrics["completed_exports"])
    e3.metric("Failed Exports", beta_metrics["failed_exports"])
    e4.metric("Total Local Packages", beta_metrics["total_local_packages"])

    st.divider()
    cf1, cf2, cf3, cf4, cf5, cf6, cf7 = st.columns(7)
    cf1.metric("Active Projects", beta_metrics["active_projects"])
    cf2.metric("Production Queue", beta_metrics["creator_production_queue"])
    cf3.metric("Review Queue", beta_metrics["creator_review_queue"])
    cf4.metric("Export Queue", beta_metrics["creator_export_queue"])
    cf5.metric("Today's Output", beta_metrics["creator_today_output"])
    cf6.metric("Monthly Output", beta_metrics["creator_monthly_output"])
    cf7.metric("Average Runtime", f"{beta_metrics['creator_average_runtime']}m")

    pp1, pp2, pp3, pp4, pp5, pp6 = st.columns(6)
    pp1.metric("Running Pipeline Jobs", beta_metrics["running_pipeline_jobs"])
    pp2.metric("Pipeline Completed Today", beta_metrics["pipeline_completed_today"])
    pp3.metric("Average Pipeline Time", f"{beta_metrics['average_pipeline_time']}s")
    pp4.metric("Approval Waiting", beta_metrics["approval_waiting"])
    pp5.metric("Export Waiting", beta_metrics["export_waiting"])
    pp6.metric("Pipeline Failures", beta_metrics["pipeline_failures"])

    au1, au2, au3, au4, au5 = st.columns(5)
    au1.metric("Automation Running", beta_metrics["automation_running"])
    au2.metric("Today's Automation Count", beta_metrics["today_automation_count"])
    au3.metric("Automation Failures", beta_metrics["automation_failures"])
    au4.metric("Automation Queue", beta_metrics["automation_queue"])
    au5.metric("Next Scheduled Job", beta_metrics["next_scheduled_job"])

    current_job = worker.get("current_job_title") or "None"
    st.caption(f"Current Job: {current_job}")

    run_col1, run_col2, run_col3 = st.columns([1, 1, 4])
    with run_col1:
        if st.button("Run next local job", type="primary", use_container_width=True):
            result = BusinessWorker(store).execute_next()
            if result is None:
                st.info("No queued jobs.")
            elif result.status == "completed":
                st.success(result.message)
            else:
                st.error(result.message)
            st.rerun()
    with run_col2:
        if st.button("Process queue", use_container_width=True):
            results = BusinessWorker(store).process_queue(limit=10)
            st.success(f"Processed {len(results)} job(s).")
            st.rerun()

    st.divider()
    jobs = data.get("scheduled_jobs", [])
    retry_queue = data.get("retry_queue", [])
    j1, j2, j3, j4, j5 = st.columns(5)
    j1.metric("Pending", monitor["pending"])
    j2.metric("Running", monitor["running"])
    j3.metric("Completed", monitor["completed"])
    j4.metric("Failed", monitor["failed"])
    j5.metric("Retry Queue", len(retry_queue))

with tabs[1]:
    st.subheader("💰 Revenue Pipeline")
    with st.expander("Add revenue item", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            title = st.text_input("Title", key="be_rev_title")
            channel = st.selectbox("Channel", ["note", "sns", "affiliate", "sales", "other"], key="be_rev_channel")
            amount = st.number_input("Expected revenue", min_value=0, step=1000, key="be_rev_amount")
        with col_b:
            stage = st.selectbox("Stage", REVENUE_STAGES, key="be_rev_stage")
            due = st.date_input("Due date", value=date.today() + timedelta(days=7), key="be_rev_due")
            memo = st.text_area("Memo", height=80, key="be_rev_memo")
        if st.button("Add revenue item", type="primary"):
            if title:
                store.add_revenue_item(title, channel, int(amount), stage, due.isoformat(), memo=memo)
                st.success("Revenue item added.")
                st.rerun()
            else:
                st.warning("Title is required.")

    for item in data.get("revenue_pipeline", []):
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.markdown(f"**{item.get('title', '')}**  \n{item.get('channel', '')} / {item.get('memo', '')}")
            c2.metric("Stage", item.get("stage", ""))
            c3.metric("Expected", f"¥{int(item.get('expected_revenue', 0)):,}")
            c4.metric("Probability", f"{int(item.get('probability', 0))}%")

with tabs[2]:
    st.subheader("🗓️ Task Scheduler")
    daemon_state = scheduler.state()
    st.warning("Scheduler daemon is optional and disabled by default. It only runs local queued jobs when started.")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Scheduler Status", daemon_state.get("status", "stopped"))
    d2.metric("Heartbeat", daemon_state.get("heartbeat_at") or "None")
    d3.metric("Interval", f"{int(daemon_state.get('interval_seconds', 300))}s")
    d4.metric("Last Result", daemon_state.get("last_result", ""))

    ctl1, ctl2, ctl3, ctl4 = st.columns([1, 1, 1, 2])
    with ctl1:
        if st.button("Start scheduler", use_container_width=True):
            scheduler.start()
            st.success("Scheduler started in local-only mode.")
            st.rerun()
    with ctl2:
        if st.button("Stop scheduler", use_container_width=True):
            scheduler.stop()
            st.success("Scheduler stopped.")
            st.rerun()
    with ctl3:
        if st.button("Heartbeat", use_container_width=True):
            scheduler.heartbeat()
            st.success("Heartbeat recorded.")
            st.rerun()
    with ctl4:
        interval_seconds = st.number_input(
            "Job interval seconds",
            min_value=60,
            max_value=86400,
            value=int(daemon_state.get("interval_seconds", 300)),
            step=60,
            key="scheduler_interval_seconds",
        )
        if st.button("Save interval", use_container_width=True):
            scheduler.configure(int(interval_seconds))
            st.success("Scheduler interval saved.")
            st.rerun()

    if st.button("Run scheduler tick now", type="primary"):
        state = scheduler.tick(force=True)
        st.info(state.get("last_result", "Scheduler tick complete."))
        st.rerun()

    st.divider()
    with st.expander("Schedule job", expanded=False):
        sc1, sc2 = st.columns(2)
        with sc1:
            job_type = st.selectbox("Job type", JOB_TYPES, key="be_job_type")
            job_title = st.text_input("Job title", key="be_job_title")
        with sc2:
            due_date = st.date_input("Due date", value=date.today(), key="be_job_due")
            priority = st.selectbox("Priority", ["low", "normal", "high"], index=1, key="be_job_priority")
        if st.button("Schedule job", type="primary"):
            if job_title:
                store.schedule_job(job_type, job_title, due_date.isoformat(), priority)
                st.success("Job scheduled.")
                st.rerun()
            else:
                st.warning("Job title is required.")

    for job in data.get("scheduled_jobs", []):
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            c1.markdown(f"**{job.get('title', '')}**  \n`{job.get('job_type', '')}`")
            c2.metric("Status", job.get("status", ""))
            c3.metric("Due", job.get("due_date", ""))
            c4.metric("Attempts", job.get("attempts", 0))

with tabs[3]:
    st.subheader("🎯 Daily KPI Recording")
    k1, k2, k3, k4, k5 = st.columns(5)
    kpi_date = k1.date_input("Date", value=date.today(), key="be_kpi_date")
    revenue = k2.number_input("Revenue", min_value=0, step=1000, key="be_kpi_revenue")
    articles = k3.number_input("Articles", min_value=0, step=1, key="be_kpi_articles")
    sns_posts = k4.number_input("SNS posts", min_value=0, step=1, key="be_kpi_sns")
    clicks = k5.number_input("Affiliate clicks", min_value=0, step=1, key="be_kpi_clicks")
    notes = st.text_area("Notes", height=80, key="be_kpi_notes")
    if st.button("Record KPI", type="primary"):
        store.record_daily_kpi(kpi_date.isoformat(), int(revenue), int(articles), int(sns_posts), int(clicks), notes)
        st.success("KPI recorded.")
        st.rerun()

    for row in data.get("daily_kpis", [])[:14]:
        st.write(f"{row.get('date')} — ¥{int(row.get('revenue', 0)):,} / articles {row.get('articles', 0)} / SNS {row.get('sns_posts', 0)}")

with tabs[4]:
    st.subheader("📈 Earnings Forecast")
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Avg daily revenue", f"¥{forecast['avg_daily_revenue']:,}")
    f2.metric("Projected KPI revenue", f"¥{forecast['projected_kpi_revenue']:,}")
    f3.metric("Weighted pipeline", f"¥{forecast['weighted_pipeline']:,}")
    f4.metric("Forecast total", f"¥{forecast['forecast_total']:,}")

with tabs[5]:
    st.subheader("🧾 Execution History")
    history = data.get("execution_history", [])
    if not history:
        st.info("No executions recorded yet.")
    for record in history[:100]:
        st.write(f"{record.get('created_at')} — `{record.get('status')}` — {record.get('message', '')}")

with tabs[6]:
    st.subheader("🔁 Retry Queue")
    retry_queue = data.get("retry_queue", [])
    if not retry_queue:
        st.info("Retry queue is empty.")
    for retry in retry_queue:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"**{retry.get('title', '')}**  \n{retry.get('last_error', '')}")
            c2.metric("Status", retry.get("status", ""))
            c3.metric("Attempts", retry.get("attempts", 0))
            if st.button("Queue retry", key=f"retry_{retry.get('retry_id')}"):
                store.retry_job(retry["retry_id"])
                st.success("Retry queued.")
                st.rerun()

with tabs[7]:
    st.subheader("🤖 AI Revenue Automation")
    st.caption("Local-first queue preparation. No external APIs are called.")

    a1, a2 = st.columns(2)
    with a1:
        st.markdown("**Note Factory Automation**")
        note_topic = st.text_input("Article topic", key="auto_note_topic")
        note_keyword = st.text_input("Target keyword", key="auto_note_keyword")
        if st.button("Generate → Review → Approve → Queue article", type="primary"):
            if note_topic:
                article = automation.generate_article(note_topic, note_keyword)
                automation.review_article(article["article_id"])
                automation.approve_article(article["article_id"])
                automation.queue_article(article["article_id"])
                st.success("Article generated, reviewed, approved, and queued locally.")
                st.rerun()
            else:
                st.warning("Article topic is required.")

        st.markdown("**SNS Factory Automation**")
        sns_topic = st.text_input("SNS topic", key="auto_sns_topic")
        if st.button("Generate X / Threads / Instagram and schedule"):
            if sns_topic:
                posts = automation.generate_sns_posts(sns_topic)
                for post in posts:
                    automation.queue_post(post["post_id"])
                st.success(f"Generated and scheduled {len(posts)} local SNS posts.")
                st.rerun()
            else:
                st.warning("SNS topic is required.")

    with a2:
        st.markdown("**Affiliate Factory**")
        aff_title = st.text_input("Offer title", key="auto_aff_title")
        aff_url = st.text_input("Offer URL", value="https://example.com/product", key="auto_aff_url")
        aff_clicks = st.number_input("Expected clicks", min_value=0, value=100, step=10, key="auto_aff_clicks")
        aff_order = st.number_input("Average order value", min_value=0, value=5000, step=500, key="auto_aff_order")
        if st.button("Queue affiliate offer"):
            if aff_title:
                automation.create_affiliate_offer(aff_title, aff_url, expected_clicks=int(aff_clicks), average_order_value=int(aff_order))
                st.success("Affiliate offer queued locally.")
                st.rerun()
            else:
                st.warning("Offer title is required.")

        st.markdown("**SEO Factory**")
        seo_keyword = st.text_input("SEO keyword", key="auto_seo_keyword")
        if st.button("Queue keyword and rebuild SEO plan"):
            if seo_keyword:
                automation.add_keyword(seo_keyword)
                automation.cluster_topics()
                automation.build_internal_links()
                automation.build_content_calendar()
                st.success("SEO keyword queued, clustered, linked, and scheduled locally.")
                st.rerun()
            else:
                st.warning("SEO keyword is required.")

with tabs[8]:
    st.subheader("🧠 AI Runtime")
    st.caption("Gemini CLI runtime only. No OpenAI API, Anthropic API, Gemini Cloud SDK, Google Workspace, or publishing APIs are called here.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gemini CLI Status", gemini_health["status"])
    c2.metric("Gemini Version", gemini_health["version"] or "Unknown")
    c3.metric("Command", "Detected" if gemini_health["installed"] else "Missing")
    c4.metric("Average Cost", "¥0")
    st.code(gemini_health["command_path"] or "gemini CLI not found", language="text")

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Prompt Queue", ai_runtime["prompt_queue"])
    m2.metric("Running Jobs", ai_runtime["running_jobs"])
    m3.metric("Completed Jobs", ai_runtime["completed_jobs"])
    m4.metric("Failed Jobs", ai_runtime["failed_jobs"])
    m5.metric("Average Runtime", f"{ai_runtime['average_runtime_ms']} ms")
    m6.metric("Average Tokens", ai_runtime["average_tokens"])

    st.markdown("**Create runtime job**")
    rt1, rt2 = st.columns([1, 2])
    with rt1:
        runtime_job_type = st.selectbox(
            "Runtime job type",
            GEMINI_RUNTIME_JOB_TYPES,
            format_func=lambda value: {
                "gemini_note_article": "Generate Note Article",
                "gemini_sns_post": "Generate SNS Post",
                "gemini_seo_article": "Generate SEO Article",
                "gemini_affiliate_description": "Generate Affiliate Description",
                "gemini_business_report": "Generate Business Report",
            }.get(value, value),
            key="runtime_job_type",
        )
        runtime_title = st.text_input("Runtime title", value="AIOS local-first beta growth", key="runtime_title")
        runtime_timeout = st.number_input("Timeout seconds", min_value=5, max_value=600, value=60, step=5, key="runtime_timeout")
        runtime_retries = st.number_input("Retries", min_value=1, max_value=5, value=1, step=1, key="runtime_retries")
    with rt2:
        runtime_prompt = st.text_area(
            "Prompt",
            value="Create a practical, concise output for AIOS beta revenue automation. Keep it local-first and actionable.",
            height=120,
            key="runtime_prompt",
        )
    if st.button("Queue Gemini CLI runtime job", type="primary"):
        if runtime_prompt.strip():
            store.schedule_runtime_job(
                runtime_job_type,
                runtime_title,
                runtime_prompt,
                timeout_seconds=int(runtime_timeout),
                retries=int(runtime_retries),
            )
            st.success("Gemini CLI runtime job queued locally.")
            st.rerun()
        else:
            st.warning("Prompt is required.")

    st.markdown("**Runtime jobs**")
    runtime_jobs = [job for job in data.get("scheduled_jobs", []) if job.get("job_type") in GEMINI_RUNTIME_JOB_TYPES]
    if not runtime_jobs:
        st.info("No Gemini CLI runtime jobs queued yet.")
    for job in runtime_jobs[:50]:
        st.write(f"{job.get('created_at')} — `{job.get('status')}` — {job.get('title')} ({job.get('job_type')})")

    st.markdown("**Runtime logs**")
    for record in data.get("ai_runtime", {}).get("runtime_logs", [])[:50]:
        st.write(
            f"{record.get('created_at')} — `{record.get('status')}` — "
            f"{record.get('job_type')} — {record.get('duration_ms')} ms — "
            f"{record.get('total_tokens')} tokens — ¥{record.get('estimated_cost_yen', 0)}"
        )

with tabs[9]:
    st.subheader("🔌 Integration Adapters")
    st.caption("Interfaces are present for beta deployment readiness. All external adapters remain disabled until explicitly approved and configured.")

    for category, title in [
        ("publishing", "Publishing Adapters"),
        ("affiliate", "Affiliate Adapters"),
        ("seo", "SEO Providers"),
    ]:
        st.markdown(f"**{title}**")
        rows = adapter_registry.by_category(category)
        cols = st.columns(3)
        for idx, adapter in enumerate(rows):
            with cols[idx % 3]:
                st.container(border=True).markdown(
                    f"**{adapter.name}**  \n"
                    f"Status: `{adapter.api_status}`  \n"
                    f"Configured: `{adapter.configured}`"
                )
