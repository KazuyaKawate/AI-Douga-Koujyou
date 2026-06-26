"""
AI Studio — Multi-Agent Production Command Center
AI動画工場 v4.0

Tabs:
  🏭 ダッシュボード  — system health, agent cards, pipeline diagram
  🚀 パイプライン   — start/monitor a new pipeline run
  📋 タスクキュー   — full task list with run/retry/delete actions
  ⚙️ エージェント設定 — enable/disable, re-route next agents, DI config
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PROJECT_ROOT
from src.agents.base_agent import (
    ALL_STATUSES, STATUS_LABELS,
    TASK_PENDING, TASK_RUNNING, TASK_DONE, TASK_FAILED, TASK_SKIPPED,
    Task, TaskQueue,
)
from src.agents.agent_registry import AgentRegistry, create_default_registry
from src.pipeline.export_pipeline import STAGE_ORDER

st.set_page_config(page_title="AI Studio", page_icon="🤖", layout="wide")

APP_VERSION = "4.0"

# ── Shared singletons (per session) ──────────────────────────────────────────

if "ai_studio_registry" not in st.session_state:
    st.session_state["ai_studio_registry"] = create_default_registry()
if "ai_studio_queue" not in st.session_state:
    st.session_state["ai_studio_queue"] = TaskQueue()

registry: AgentRegistry = st.session_state["ai_studio_registry"]
queue:    TaskQueue      = st.session_state["ai_studio_queue"]

# ── Header ────────────────────────────────────────────────────────────────────

st.title("🤖 AI Studio")
st.caption(
    f"マルチエージェント制作スタジオ | AI動画工場 v{APP_VERSION} | "
    f"エージェント: {registry.active_count()}/{len(registry.list_all())} 稼働中"
)

hdr_r = st.columns([1, 1, 1])
with hdr_r[2]:
    if st.button("🔄 全体更新", key="studio_refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Agent cards cache ─────────────────────────────────────────────────────────

PIPELINE_ORDER = [
    "ProducerAgent", "DirectorAgent", "ScriptAgent",
    "PromptAgent",   "EditorAgent",   "PublisherAgent",
]

STATUS_COLOR = {
    TASK_PENDING: "#888888",
    TASK_RUNNING: "#f0a500",
    TASK_DONE:    "#27ae60",
    TASK_FAILED:  "#e74c3c",
    TASK_SKIPPED: "#7f8c8d",
}


def _last_task_for_agent(agent_name: str) -> Task | None:
    tasks = queue.list_all(agent=agent_name)
    return tasks[0] if tasks else None


def _current_task_for_agent(agent_name: str) -> Task | None:
    tasks = queue.list_all(agent=agent_name, status=TASK_RUNNING)
    return tasks[0] if tasks else None


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_dash, tab_pipeline, tab_queue, tab_settings = st.tabs([
    "🏭 ダッシュボード",
    "🚀 パイプライン実行",
    "📋 タスクキュー",
    "⚙️ エージェント設定",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

with tab_dash:

    # ── System health metrics ─────────────────────────────────────────────────

    stats        = queue.stats()
    total_tasks  = stats["total"]
    by_status    = stats["by_status"]
    avg_secs     = stats["avg_seconds"]
    active_count = registry.active_count()
    total_agents = len(registry.list_all())
    health_pct   = int(active_count / total_agents * 100) if total_agents else 0

    st.subheader("システムヘルス")
    dm = st.columns(6)
    dm[0].metric("🤖 稼働エージェント", f"{active_count}/{total_agents}")
    dm[1].metric("⏳ キュー",           by_status.get(TASK_PENDING, 0))
    dm[2].metric("🔄 実行中",           by_status.get(TASK_RUNNING, 0))
    dm[3].metric("✅ 完了済",           by_status.get(TASK_DONE, 0))
    dm[4].metric("❌ 失敗",             by_status.get(TASK_FAILED, 0))
    dm[5].metric("⏱ 平均処理時間",     f"{avg_secs:.1f}s" if avg_secs else "N/A")

    if health_pct == 100:
        st.success(f"✅ システム正常 — 全エージェント稼働中 ({APP_VERSION})")
    elif health_pct >= 50:
        st.warning(f"⚠️ 一部エージェント無効 — {active_count}/{total_agents} 稼働中")
    else:
        st.error(f"❌ システム異常 — エージェントが不足しています ({active_count}/{total_agents})")

    st.divider()

    # ── Agent cards ───────────────────────────────────────────────────────────

    st.subheader("エージェント一覧")
    agents = [registry.get(n) for n in PIPELINE_ORDER if registry.get(n)]
    cols_per_row = 3
    for row_start in range(0, len(agents), cols_per_row):
        row_agents = agents[row_start:row_start + cols_per_row]
        cols = st.columns(cols_per_row)
        for col, agent in zip(cols, row_agents):
            info        = agent.get_info()
            last_task   = _last_task_for_agent(agent.NAME)
            current_task = _current_task_for_agent(agent.NAME)

            with col:
                status_badge = "🟢 有効" if info["enabled"] else "🔴 無効"
                st.markdown(
                    f"**{info['icon']} {info['name']}**  {status_badge}"
                )
                st.caption(info["role"])
                st.caption(f"v{info['version']} | 次: {', '.join(info['next_agents']) or '（終端）'}")

                if current_task:
                    st.caption(f"🔄 実行中: `{current_task.id}`")
                    st.progress(current_task.progress)
                elif last_task:
                    st_lbl = STATUS_LABELS.get(last_task.status, last_task.status)
                    st.caption(f"最終タスク: `{last_task.id}` — {st_lbl}")
                    if last_task.status == TASK_DONE:
                        ep = last_task.output.get("episode_id", "")
                        if ep:
                            st.caption(f"エピソード: `{ep}`")
                else:
                    st.caption("タスク履歴なし")

                # Quick enable/disable
                new_enabled = st.toggle(
                    "有効",
                    value=info["enabled"],
                    key=f"dash_toggle_{agent.NAME}",
                )
                if new_enabled != info["enabled"]:
                    if new_enabled:
                        registry.enable(agent.NAME)
                    else:
                        registry.disable(agent.NAME)
                    st.rerun()

    st.divider()

    # ── Pipeline flow diagram ──────────────────────────────────────────────────

    st.subheader("パイプラインフロー")
    flow_cols = st.columns(len(PIPELINE_ORDER) * 2 - 1)
    for i, name in enumerate(PIPELINE_ORDER):
        agent = registry.get(name)
        col_i = i * 2
        with flow_cols[col_i]:
            if agent:
                info   = agent.get_info()
                cur    = _current_task_for_agent(name)
                last   = _last_task_for_agent(name)
                status = "🔄" if cur else ("✅" if (last and last.status == TASK_DONE) else ("🔴" if not info["enabled"] else "⬜"))
                st.markdown(f"**{info['icon']}**\n\n{status}\n\n`{name[:8]}`")
        if i < len(PIPELINE_ORDER) - 1:
            flow_cols[col_i + 1].markdown("**→**")

    # ── Recent activity ────────────────────────────────────────────────────────

    st.divider()
    st.subheader("最近のタスク")
    recent = queue.list_all()[:8]
    if not recent:
        st.info("タスク履歴がありません。「パイプライン実行」タブから開始してください。")
    for t in recent:
        tc = st.columns([2, 3, 2, 2, 1])
        tc[0].caption(f"`{t.id}`")
        tc[1].caption(t.label or t.agent)
        tc[2].caption(STATUS_LABELS.get(t.status, t.status))
        tc[3].caption(t.updated[:16] if t.updated else "")
        if t.status == TASK_PENDING and tc[4].button("▶️", key=f"dash_run_{t.id}"):
            with st.spinner(f"{t.agent} を実行中..."):
                registry.run_task(t, queue)
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PIPELINE EXECUTION
# ══════════════════════════════════════════════════════════════════════════════

with tab_pipeline:

    st.subheader("🚀 新規パイプラインを開始")

    pl_l, pl_r = st.columns([2, 3])

    with pl_l:
        # ── Episode config ─────────────────────────────────────────────────────

        st.caption("**エピソード設定**")

        _project_dir = PROJECT_ROOT / "project"
        existing_eps = []
        if _project_dir.exists():
            existing_eps = [
                d.name for d in sorted(_project_dir.iterdir())
                if d.is_dir() and (d / "episode.json").exists()
            ]

        use_existing = st.checkbox("既存のエピソードを使用（生成ステップをスキップ）",
                                   key="pl_use_existing")

        if use_existing and existing_eps:
            ep_id = st.selectbox("エピソードを選択", existing_eps, key="pl_ep_sel")
            topic = ""
        else:
            ep_id = st.text_input("エピソードID", value="EP01", key="pl_ep_id",
                                   placeholder="例: EP01")
            topic = st.text_input("テーマ・タイトル", key="pl_topic",
                                   placeholder="例: Pythonの基礎を学ぼう")

        duration   = st.selectbox("動画の長さ", ["1分", "2分", "3分", "5分", "10分"],
                                   index=2, key="pl_duration")
        num_scenes = st.slider("シーン数", 2, 8, 3, key="pl_scenes")
        style      = st.selectbox("スタイル",
                                  ["解説・教育", "エンタメ", "ニュース・情報",
                                   "ビジネス・マーケティング", "Vlog・日常"],
                                  key="pl_style")
        cost_saving = st.checkbox("コスト節約モード", key="pl_cost", value=False)

        st.caption("**演出設定（DirectorAgent用）**")
        overall_tone   = st.selectbox("全体トーン",
                                      ["educational", "entertaining", "serious",
                                       "emotional", "calm", "urgent"],
                                      key="pl_tone")
        visual_style   = st.selectbox("ビジュアルスタイル",
                                      ["cinematic", "anime", "documentary",
                                       "educational", "realistic", "watercolor"],
                                      key="pl_vstyle")
        pacing         = st.selectbox("ペーシング",
                                      ["slow", "moderate", "fast", "varied"],
                                      index=1, key="pl_pacing")

        st.caption("**エージェント選択**")
        enabled_agents = {}
        for name in PIPELINE_ORDER:
            agent = registry.get(name)
            if agent:
                enabled_agents[name] = st.checkbox(
                    f"{agent.get_info()['icon']} {name}",
                    value=agent.is_enabled(),
                    key=f"pl_use_{name}",
                )

        auto_chain = st.checkbox("自動チェーン（タスク完了後に次のエージェントを自動実行）",
                                 key="pl_autochain", value=False)

    with pl_r:
        # ── Pipeline visualization ─────────────────────────────────────────────

        st.caption("**パイプラインフロー**")

        # Find active pipeline_id in session
        sel_pipeline = st.session_state.get("pl_active_pipeline_id")

        if sel_pipeline:
            pipeline_tasks = {t.agent: t for t in queue.list_all(pipeline_id=sel_pipeline)}
            st.caption(f"Pipeline ID: `{sel_pipeline}`")

            for name in PIPELINE_ORDER:
                t = pipeline_tasks.get(name)
                agent = registry.get(name)
                if not agent:
                    continue
                info = agent.get_info()
                if t:
                    st_lbl = STATUS_LABELS.get(t.status, t.status)
                    pc = st.columns([4, 2, 2])
                    pc[0].markdown(f"{info['icon']} **{name}** — {st_lbl}")
                    if t.status == TASK_PENDING:
                        if pc[1].button("▶️ 実行", key=f"pl_run_{t.id}",
                                        use_container_width=True):
                            with st.spinner(f"{name} を実行中..."):
                                registry.run_task(t, queue)
                                if auto_chain:
                                    # Auto-chain: run all pending follow-ups
                                    _safety = 0
                                    while _safety < 10:
                                        next_pending = queue.list_pending()
                                        pipeline_pending = [
                                            tp for tp in next_pending
                                            if tp.pipeline_id == sel_pipeline
                                        ]
                                        if not pipeline_pending:
                                            break
                                        registry.run_task(pipeline_pending[0], queue)
                                        _safety += 1
                            st.rerun()
                    elif t.status == TASK_RUNNING:
                        st.progress(t.progress)
                    if t.status == TASK_DONE and t.output:
                        ep = t.output.get("episode_id", "")
                        pc[2].caption(f"✅ `{ep}`" if ep else "✅")
                    elif t.status == TASK_FAILED:
                        st.caption(f"❌ {t.error[:80]}")
                else:
                    st.markdown(f"{info['icon']} **{name}** — ⬜ 未スケジュール")

            st.divider()
            if st.button("🔄 このパイプラインをリセット",
                         key="pl_reset", use_container_width=True):
                for t in queue.list_all(pipeline_id=sel_pipeline):
                    queue.delete(t.id)
                st.session_state.pop("pl_active_pipeline_id", None)
                st.rerun()

        else:
            # Placeholder flow
            for name in PIPELINE_ORDER:
                agent = registry.get(name)
                if agent:
                    info = agent.get_info()
                    st.markdown(f"{info['icon']} **{name}** — ⬜ 待機中")
            st.info("左のフォームを入力して「🚀 パイプライン開始」をクリックしてください。")

        st.divider()

        # ── Start button ───────────────────────────────────────────────────────

        if st.button("🚀 パイプラインを開始", type="primary", use_container_width=True,
                     key="pl_start"):
            if not ep_id:
                st.error("エピソードIDを入力してください")
            elif not use_existing and not topic:
                st.error("テーマを入力してください")
            else:
                import uuid as _uuid
                pipeline_id = f"pipeline_{_uuid.uuid4().hex[:8]}"

                # Determine first agent
                first_agent = None
                for name in PIPELINE_ORDER:
                    if enabled_agents.get(name, True):
                        first_agent = name
                        break

                if not first_agent:
                    st.error("実行するエージェントを少なくとも1つ有効にしてください")
                else:
                    # If using existing episode, skip ProducerAgent
                    if use_existing and first_agent == "ProducerAgent":
                        first_agent = "DirectorAgent"

                    input_data = {
                        "episode_id":    ep_id,
                        "topic":         topic,
                        "duration":      duration,
                        "num_scenes":    num_scenes,
                        "style":         style,
                        "cost_saving":   cost_saving,
                        "overall_tone":  overall_tone,
                        "visual_style":  visual_style,
                        "pacing":        pacing,
                    }

                    t = queue.create(
                        agent       = first_agent,
                        input_data  = input_data,
                        pipeline_id = pipeline_id,
                        label       = f"{first_agent} — {ep_id}",
                    )
                    st.session_state["pl_active_pipeline_id"] = pipeline_id

                    if auto_chain:
                        with st.spinner("パイプラインを自動実行中..."):
                            _t = t
                            for _ in range(20):
                                _t = registry.run_task(_t, queue)
                                if not _t or _t.status == TASK_FAILED:
                                    break
                                next_p = [
                                    tp for tp in queue.list_pending()
                                    if tp.pipeline_id == pipeline_id
                                ]
                                if not next_p:
                                    break
                                _t = next_p[0]

                    st.success(f"✅ パイプライン `{pipeline_id}` を開始しました")
                    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — TASK QUEUE
# ══════════════════════════════════════════════════════════════════════════════

with tab_queue:

    st.subheader("📋 タスクキュー")

    # ── Filter + actions bar ──────────────────────────────────────────────────

    q_filter_col, q_action_col = st.columns([3, 2])
    with q_filter_col:
        filter_status = st.selectbox(
            "フィルター",
            ["すべて"] + ALL_STATUSES,
            format_func=lambda x: STATUS_LABELS.get(x, "すべて"),
            key="q_filter",
        )
        filter_agent = st.selectbox(
            "エージェント",
            ["すべて"] + PIPELINE_ORDER,
            key="q_agent_filter",
        )
    with q_action_col:
        st.write("")
        if st.button("🗑️ 完了済みをクリア", use_container_width=True, key="q_clear_done"):
            cleared = queue.clear_completed()
            st.success(f"✅ {cleared} 件のタスクを削除しました")
            st.rerun()
        if st.button("🔄 更新", use_container_width=True, key="q_refresh"):
            st.rerun()

    # ── Task list ─────────────────────────────────────────────────────────────

    tasks = queue.list_all(
        status = None if filter_status == "すべて" else filter_status,
        agent  = None if filter_agent  == "すべて" else filter_agent,
    )

    if not tasks:
        st.info("タスクがありません。")
    else:
        st.caption(f"{len(tasks)} 件のタスク")
        for t in tasks:
            agent_info = {}
            if a := registry.get(t.agent):
                agent_info = a.get_info()
            icon = agent_info.get("icon", "🤖")
            st_lbl = STATUS_LABELS.get(t.status, t.status)

            with st.expander(
                f"{icon} `{t.id}` — {t.agent} — {st_lbl} — {t.created[:16]}",
                expanded=(t.status == TASK_RUNNING),
            ):
                qc = st.columns([2, 2, 2, 1, 1, 1])
                qc[0].caption(f"**Pipeline:** `{t.pipeline_id or '(なし)'}`")
                qc[1].caption(f"**作成:** {t.created[:19]}")
                qc[2].caption(f"**更新:** {t.updated[:19]}")

                if t.status == TASK_RUNNING:
                    st.progress(t.progress, text=f"{int(t.progress*100)}%")

                if t.error:
                    st.error(f"エラー: {t.error}")

                # Action buttons
                if t.status == TASK_PENDING:
                    if qc[3].button("▶️ 実行", key=f"q_run_{t.id}",
                                    use_container_width=True):
                        with st.spinner(f"{t.agent} を実行中..."):
                            registry.run_task(t, queue)
                        st.rerun()

                if t.status in (TASK_FAILED, TASK_DONE):
                    if qc[4].button("🔁 再試行", key=f"q_retry_{t.id}",
                                    use_container_width=True):
                        queue.update(t.id, status=TASK_PENDING, error="",
                                     output={}, progress=0.0)
                        st.rerun()

                if qc[5].button("🗑️", key=f"q_del_{t.id}", help="削除"):
                    queue.delete(t.id)
                    st.rerun()

                # Input / output detail
                detail_col1, detail_col2 = st.columns(2)
                with detail_col1:
                    st.caption("**Input**")
                    st.json(t.input, expanded=False)
                with detail_col2:
                    st.caption("**Output**")
                    st.json(t.output if t.output else {}, expanded=False)

                if t.depends_on:
                    st.caption(f"依存: {', '.join(t.depends_on)}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — AGENT SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

with tab_settings:

    st.subheader("⚙️ エージェント設定")
    st.caption(
        "各エージェントの有効化・無効化、次エージェントのルーティング変更（依存性注入）を設定します。"
        "変更は `config/agent_registry.json` に永続化されます。"
    )

    for name in PIPELINE_ORDER:
        agent = registry.get(name)
        if not agent:
            continue
        info = agent.get_info()
        with st.expander(
            f"{info['icon']} {info['name']}  —  {'🟢 有効' if info['enabled'] else '🔴 無効'}",
            expanded=False,
        ):
            sc = st.columns([3, 2])
            with sc[0]:
                st.markdown(f"**役割:** {info['role']}")
                st.caption(info.get("description", ""))
                st.caption(f"バージョン: v{info['version']}")

                new_en = st.toggle(
                    "エージェントを有効にする",
                    value=info["enabled"],
                    key=f"cfg_en_{name}",
                )
                if new_en != info["enabled"]:
                    if new_en:
                        registry.enable(name)
                    else:
                        registry.disable(name)
                    st.success(f"{'有効化' if new_en else '無効化'}しました")
                    st.rerun()

            with sc[1]:
                # Next-agents routing (dependency injection)
                st.caption("**次エージェント（ルーティング）**")
                available_next = [n for n in PIPELINE_ORDER if n != name]
                current_next   = info["next_agents"]

                new_next = st.multiselect(
                    "次エージェント",
                    available_next,
                    default=current_next,
                    key=f"cfg_next_{name}",
                    label_visibility="collapsed",
                )
                if sorted(new_next) != sorted(current_next):
                    if st.button(f"✅ {name} のルーティングを更新",
                                 key=f"cfg_next_save_{name}",
                                 use_container_width=True):
                        registry.set_next_agents(name, new_next)
                        st.success(f"ルーティングを更新しました: {new_next}")
                        st.rerun()

            # Config JSON editor (for future advanced settings)
            with st.expander(f"🔧 {name} 高度な設定 (config JSON)"):
                current_cfg_str = json.dumps(agent.config, ensure_ascii=False, indent=2)
                new_cfg_str = st.text_area(
                    "Config JSON",
                    value=current_cfg_str,
                    height=100,
                    key=f"cfg_json_{name}",
                    label_visibility="collapsed",
                )
                if st.button(f"💾 保存", key=f"cfg_json_save_{name}",
                             use_container_width=True):
                    try:
                        new_cfg = json.loads(new_cfg_str)
                        agent.config.update(new_cfg)
                        registry.save_state()
                        st.success("設定を保存しました")
                    except json.JSONDecodeError as exc:
                        st.error(f"JSON エラー: {exc}")

    st.divider()

    # ── Registry config viewer ─────────────────────────────────────────────────

    from src.agents.agent_registry import REGISTRY_CONFIG_PATH
    st.subheader("📄 config/agent_registry.json")
    if REGISTRY_CONFIG_PATH.exists():
        raw = REGISTRY_CONFIG_PATH.read_text(encoding="utf-8")
        dl1, dl2 = st.columns([3, 1])
        dl1.caption(f"保存先: `{REGISTRY_CONFIG_PATH.relative_to(PROJECT_ROOT)}`")
        dl2.download_button("⬇️ ダウンロード", data=raw,
                            file_name="agent_registry.json",
                            mime="application/json", key="cfg_dl")
        st.code(raw, language="json")
    else:
        st.info("まだ保存されていません。エージェント設定を変更すると作成されます。")

    st.divider()

    # ── Version info ───────────────────────────────────────────────────────────

    st.subheader("ℹ️ システム情報")
    vi = st.columns(3)
    vi[0].metric("AI動画工場バージョン", f"v{APP_VERSION}")
    vi[1].metric("登録エージェント数",   len(registry.list_all()))
    vi[2].metric("タスクキュー合計",     queue.stats()["total"])

    with st.expander("🩺 アーキテクチャ情報"):
        st.code("""
エージェント通信: Task オブジェクト (project/tasks/*.json)
依存性注入:       agent.set_next_agents(["AgentName", ...])
状態永続化:       config/agent_registry.json
拡張ポイント:
  - CloudAgent: BaseAgent.run() をオーバーライドしてリモート実行
  - MultiUser:  AgentRegistry.run_task() に認証チェックを追加
  - Subscription: ProjectContext.can_use(agent.NAME) でゲート
  - Fan-out:    TaskQueue.create_many() で並列ブランチ
""", language="text")
