import json
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PROJECT_ROOT
from src.utils.settings_manager import load_settings

from src.pipeline.export_pipeline import is_production_ready, load_production_report, load_production_state
from src.director.director_planner import plan_exists as director_plan_exists

st.set_page_config(page_title="制作ダッシュボード", page_icon="📊", layout="wide")
st.title("📊 制作ダッシュボード")
st.caption("全エピソードの制作進捗を一覧管理 | v4.4.1")

# ── Mission Control Summary (v4.2) ─────────────────────────────────────────────
try:
    from src.hq.task_manager import load_tasks, get_task_stats
    from src.hq.kpi_manager import load_kpi
    import json as _json

    _tasks = load_tasks()
    _stats = get_task_stats(_tasks)
    _kpi = load_kpi()
    _actuals = _kpi.get("actuals", {})
    _today_rev = 0
    _rev_path = Path(__file__).parent.parent / "config" / "revenue_expense.json"
    if _rev_path.exists():
        _today_rev = _json.loads(_rev_path.read_text(encoding="utf-8")).get("today", {}).get("revenue", 0)
    _open_tasks = _stats["pending"] + _stats["in_progress"]

    st.markdown("##### 🎯 Mission Control サマリー")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("✅ 今日の完了率", f"{_stats['pct']}%", help=f"{_stats['done']}/{_stats['total']} タスク完了")
    mc2.metric("📋 未完了タスク", _open_tasks)
    mc3.metric("💰 今日の売上", f"¥{_today_rev:,}")
    mc4.metric("🎬 動画制作数", _actuals.get("video_count", 0))
    st.page_link("pages/17_Mission_Control.py", label="🎯 Mission Controlを開く →")
    st.divider()
except Exception:
    pass

# ── SNS Factory Summary (v4.4) ─────────────────────────────────────────────────
try:
    import json as _json2
    _sns_path = Path(__file__).parent.parent / "config" / "sns_posts.json"
    if _sns_path.exists():
        _sns_data = _json2.loads(_sns_path.read_text(encoding="utf-8"))
        _sns_posts = _sns_data.get("posts", [])
        _sns_draft = sum(1 for p in _sns_posts if p.get("status") == "draft")
        _sns_sched = sum(1 for p in _sns_posts if p.get("status") == "scheduled")
        _sns_pub = sum(1 for p in _sns_posts if p.get("status") == "published")
        _sns_today = sum(1 for p in _sns_posts
                         if p.get("status") == "published"
                         and p.get("published_date") == __import__("datetime").date.today().isoformat())
        st.markdown("##### 📱 SNS Factory サマリー")
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("📄 下書き", _sns_draft)
        sc2.metric("🗓️ スケジュール済", _sns_sched)
        sc3.metric("✅ 累計公開", _sns_pub)
        sc4.metric("📅 今日の公開", _sns_today)
        st.page_link("pages/19_SNS_Factory.py", label="📱 SNS投稿工場を開く →")
        st.divider()
except Exception:
    pass

# ── Approval Assistant Summary (v4.4.1) ───────────────────────────────────────
try:
    from src.devtools.approval_analyzer import get_latest_risk
    _latest_approval = get_latest_risk()
    if _latest_approval:
        _a_icon = _latest_approval.get("risk_icon", "🟢")
        _a_ts = _latest_approval.get("timestamp", "")[:16].replace("T", " ")
        _a_summary = _latest_approval.get("summary", "")[:50]
        _a_rec = _latest_approval.get("recommendation", "yes")
        st.markdown("##### 🔍 承認アシスタント 直近の分析")
        _ac1, _ac2 = st.columns([3, 1])
        _ac1.caption(f"{_a_icon} {_a_ts} — {_a_summary}")
        _ac2.caption({"yes": "✅ 承認", "ask_revise": "🟠 修正依頼", "no": "🔴 拒否"}.get(_a_rec, ""))
        st.page_link("pages/20_Approval_Assistant.py", label="🔍 承認アシスタントを開く →")
        st.divider()
except Exception:
    pass

_settings = load_settings()
_gen = _settings["generation"]
st.sidebar.caption(
    f"⚙️ 画像: `{_gen['image_provider']}`"
    f" | 動画: `{_gen['video_provider']}`"
    f" | 音声: `{_gen['voice_provider']}`"
)

VIDEO_EXT = {".mp4", ".mov", ".webm", ".avi"}

STEPS_DEF = [
    ("台本",           "episode.json"),
    ("画像プロンプト", "*_image_prompts.txt"),
    ("動画プロンプト", "*_video_prompts.txt"),
    ("音声台本",       "*_voice_script.txt"),
    ("字幕",           "*.srt"),
    ("素材選定",       "asset_manifest.json"),
    ("完成動画",       None),
]

STATUS_ICON = {"完成": "🟢", "制作中": "🟡", "素材待ち": "🟠", "未着手": "⚪"}
STATUS_BADGE = {
    "完成":    "✅ 完成",
    "制作中":  "🔄 制作中",
    "素材待ち": "⏳ 素材待ち",
    "未着手":  "⏸ 未着手",
}


# ── Episode scanning ───────────────────────────────────────────────────────────

def _has(ep_dir: Path, pattern: str) -> bool:
    return bool(list(ep_dir.glob(pattern))) if "*" in pattern else (ep_dir / pattern).exists()


def _scan_episode(ep_dir: Path) -> dict | None:
    ep_id = ep_dir.name
    ep_json = ep_dir / "episode.json"
    if not ep_json.exists():
        return None

    ep_data: dict = {}
    try:
        ep_data = json.loads(ep_json.read_text(encoding="utf-8"))
    except Exception:
        pass

    sections = ep_data.get("sections", [])
    total_dur = ep_data.get("total_duration_seconds") or sum(
        s.get("duration_seconds", 0) for s in sections
    )

    flags: dict[str, bool] = {}
    for label, pattern in STEPS_DEF:
        if pattern is None:
            flags[label] = any(
                f.suffix.lower() in VIDEO_EXT for f in ep_dir.iterdir() if f.is_file()
            )
            if not flags[label]:
                out_dir = PROJECT_ROOT / "output"
                if out_dir.exists():
                    flags[label] = any(
                        f.suffix.lower() in VIDEO_EXT and ep_id.lower() in f.name.lower()
                        for f in out_dir.iterdir()
                        if f.is_file()
                    )
        else:
            flags[label] = _has(ep_dir, pattern)

    steps = [(label, flags[label]) for label, _ in STEPS_DEF]
    completed = sum(1 for _, done in steps if done)
    progress = completed / len(steps)

    if flags["完成動画"]:
        status = "完成"
    elif flags["素材選定"] or (
        flags["画像プロンプト"] and flags["動画プロンプト"] and flags["音声台本"]
    ):
        status = "制作中"
    elif flags["画像プロンプト"] or flags["動画プロンプト"]:
        status = "素材待ち"
    elif sections:
        status = "制作中"
    else:
        status = "未着手"

    ep_files = [f for f in ep_dir.iterdir() if f.is_file()]
    last_mtime = max(
        (f.stat().st_mtime for f in ep_files), default=ep_dir.stat().st_mtime
    )

    # Production state (v3.0) + Director plan (v3.1)
    prod_state  = load_production_state(ep_dir)
    prod_ready  = is_production_ready(prod_state)
    prod_report = load_production_report(ep_dir)
    has_director = director_plan_exists(ep_dir)

    return {
        "ep_id": ep_id,
        "title": ep_data.get("title", ""),
        "description": ep_data.get("description", ""),
        "scene_count": len(sections),
        "total_duration": total_dur,
        "last_mtime": last_mtime,
        "last_modified": datetime.fromtimestamp(last_mtime).strftime("%Y-%m-%d %H:%M"),
        "steps": steps,
        "progress": progress,
        "completed_steps": completed,
        "total_steps": len(steps),
        "status": status,
        "ep_dir": ep_dir,
        "has_image_prompts": flags["画像プロンプト"],
        "has_video_prompts": flags["動画プロンプト"],
        "has_srt": flags["字幕"],
        "has_asset_manifest": flags["素材選定"],
        "production_ready": prod_ready,
        "has_export":       prod_report is not None,
        "has_director":     has_director,
    }


def load_episodes() -> list[dict]:
    project_dir = PROJECT_ROOT / "project"
    if not project_dir.exists():
        return []
    results = []
    for d in sorted(project_dir.iterdir()):
        if d.is_dir():
            try:
                ep = _scan_episode(d)
                if ep:
                    results.append(ep)
            except Exception:
                pass
    return results


# ── Load ───────────────────────────────────────────────────────────────────────

episodes = load_episodes()

total = len(episodes)
done_count = sum(1 for e in episodes if e["status"] == "完成")
wip_count = sum(1 for e in episodes if e["status"] == "制作中")
waiting_count = sum(1 for e in episodes if e["status"] == "素材待ち")

# ── Summary metrics ────────────────────────────────────────────────────────────

m1, m2, m3, m4 = st.columns(4)
m1.metric("📁 総エピソード数", total)
m2.metric("🔄 制作中", wip_count)
m3.metric("✅ 完成", done_count)
m4.metric("⏳ 素材待ち", waiting_count)

st.divider()

# ── Filters ────────────────────────────────────────────────────────────────────

fc1, fc2, fc3 = st.columns(3)
with fc1:
    status_filter = st.selectbox(
        "ステータスで絞り込み",
        ["すべて", "未着手", "制作中", "素材待ち", "完成"],
        key="dash_status",
    )
with fc2:
    id_search = st.text_input(
        "エピソードIDで検索", placeholder="例: EP01", key="dash_search"
    )
with fc3:
    sort_label = st.selectbox(
        "並び替え",
        ["最終更新（新しい順）", "最終更新（古い順）", "エピソードID", "進捗（高い順）", "進捗（低い順）"],
        key="dash_sort",
    )

filtered = episodes[:]
if status_filter != "すべて":
    filtered = [e for e in filtered if e["status"] == status_filter]
if id_search:
    filtered = [e for e in filtered if id_search.lower() in e["ep_id"].lower()]

_sort_map = {
    "最終更新（新しい順）": (lambda e: e["last_mtime"], True),
    "最終更新（古い順）":   (lambda e: e["last_mtime"], False),
    "エピソードID":        (lambda e: e["ep_id"], False),
    "進捗（高い順）":      (lambda e: e["progress"], True),
    "進捗（低い順）":      (lambda e: e["progress"], False),
}
_sort_fn, _sort_rev = _sort_map[sort_label]
filtered.sort(key=_sort_fn, reverse=_sort_rev)

st.caption(f"{len(filtered)} / {total} エピソードを表示")

if not filtered:
    if total == 0:
        st.info(
            "エピソードがまだありません。\n\n"
            "⚡ 一発生成 または 🎞️ エピソード管理 でエピソードを作成してください。"
        )
    else:
        st.warning("フィルター条件に一致するエピソードがありません")
    st.stop()

st.divider()

# ── Episode cards ──────────────────────────────────────────────────────────────

for ep in filtered:
    icon = STATUS_ICON.get(ep["status"], "⚪")
    pct = int(ep["progress"] * 100)
    prod_badge = (
        "　|　📦 **書き出し済**" if ep.get("has_export")
        else ("　|　🎬 **制作可能**" if ep.get("production_ready") else "")
    )
    dir_badge = "　|　🎬 **Director**" if ep.get("has_director") else ""
    header = (
        f"{icon} **{ep['ep_id']}**"
        f" — {ep['title'] or '（タイトル未設定）'}"
        f"　|　{STATUS_BADGE.get(ep['status'], ep['status'])}"
        f"　|　進捗 {pct}%"
        f"{prod_badge}"
        f"{dir_badge}"
    )

    with st.expander(header, expanded=(ep["status"] in ("制作中", "素材待ち"))):
        c_info, c_prog, c_links = st.columns([2, 2, 2])

        # ── Episode info ───────────────────────────────────────────────
        with c_info:
            st.markdown(f"**ID:** `{ep['ep_id']}`")
            st.markdown(f"**タイトル:** {ep['title'] or '（未設定）'}")
            if ep["description"]:
                short = ep["description"][:120]
                if len(ep["description"]) > 120:
                    short += "…"
                st.markdown(f"**概要:** {short}")
            st.markdown(f"**シーン数:** {ep['scene_count']} シーン")
            if ep["total_duration"] > 0:
                mins, secs = divmod(ep["total_duration"], 60)
                dur_str = f"{mins}分{secs}秒" if mins else f"{secs}秒"
                st.markdown(f"**推定尺:** {dur_str}")
            st.markdown(f"**最終更新:** {ep['last_modified']}")
            st.markdown(f"**ステータス:** {STATUS_BADGE.get(ep['status'], ep['status'])}")

        # ── Progress ───────────────────────────────────────────────────
        with c_prog:
            st.markdown("**制作チェックリスト**")
            for step_name, done in ep["steps"]:
                mark = "✅" if done else "⬜"
                st.markdown(f"{mark} {step_name}")
            st.divider()
            st.progress(ep["progress"])
            st.caption(
                f"進捗 {pct}%　({ep['completed_steps']} / {ep['total_steps']} 完了)"
            )

        # ── Quick links ────────────────────────────────────────────────
        with c_links:
            st.markdown("**フォルダパス**")
            st.code(str(ep["ep_dir"]), language=None)
            st.markdown("**ファイル一覧**")
            ep_dir = ep["ep_dir"]
            try:
                ep_files_list = sorted(
                    (f for f in ep_dir.iterdir() if f.is_file()), key=lambda f: f.name
                )
                for f in ep_files_list:
                    kb = f.stat().st_size / 1024
                    st.caption(f"• `{f.name}` ({kb:.1f} KB)")
            except Exception:
                st.caption("ファイル一覧を取得できませんでした")

        # ── File previews (tabs, not nested expanders) ─────────────────
        tab_labels: list[str] = []
        tab_paths: list[Path] = []

        img_files = list(ep_dir.glob("*_image_prompts.txt"))
        if img_files:
            tab_labels.append("🖼️ 画像プロンプト")
            tab_paths.append(img_files[0])

        vid_files = list(ep_dir.glob("*_video_prompts.txt"))
        if vid_files:
            tab_labels.append("🎬 動画プロンプト")
            tab_paths.append(vid_files[0])

        srt_files = list(ep_dir.glob("*.srt"))
        if srt_files:
            tab_labels.append("🔤 字幕 SRT")
            tab_paths.append(srt_files[0])

        manifest_path = ep_dir / "asset_manifest.json"
        if manifest_path.exists():
            tab_labels.append("📋 素材マニフェスト")
            tab_paths.append(manifest_path)

        if tab_labels:
            st.markdown("---")
            st.markdown("**ファイルプレビュー**")
            tabs = st.tabs(tab_labels)
            for tab, fpath in zip(tabs, tab_paths):
                with tab:
                    try:
                        raw = fpath.read_text(encoding="utf-8", errors="replace")
                        if fpath.suffix == ".json":
                            st.json(json.loads(raw))
                        else:
                            preview = raw[:3000]
                            if len(raw) > 3000:
                                preview += "\n...(省略)"
                            st.code(preview, language=None)
                    except Exception as exc:
                        st.error(f"読み込みエラー: {exc}")

    st.divider()
