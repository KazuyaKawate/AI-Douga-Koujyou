"""Project Manager — Central control hub for AI動画工場.

Tabs:
  🏠 概要         — project overview, quick stats, dashboard widgets
  📺 シリーズ     — series management (create / archive / duplicate / rename)
  📊 アナリティクス — production analytics and export history
  💾 バックアップ  — auto + manual backup, restore, backup history
  📦 パッケージ   — export / import / validate project ZIP
  ⚡ 一括操作     — batch export / archive / duplicate / delete / rename

Future-ready design:
  - ProjectContext (version / user_id / cloud_endpoint / subscription_tier)
    is stored in session state and passed conceptually to every action.
  - All data I/O goes through manager functions, never direct file access.
  - Feature flags in ctx["features"] gate future capabilities without
    changing any calling code.
  - Backup MANIFEST.json reserves fields for user_id, license_key,
    cloud_backup_id so remote backup can be added without schema changes.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PROJECT_ROOT
from src.utils.project_manager import (
    GENRE_OPTIONS,
    LANGUAGE_OPTIONS,
    ProjectContext,
    add_episode_to_series,
    add_series,
    archive_episode,
    archive_series,
    batch_rename_episodes,
    delete_episode,
    delete_series,
    duplicate_episode,
    duplicate_series,
    get_backup_settings,
    get_project_info,
    list_all_series,
    list_series,
    remove_episode_from_series,
    set_episode_order_in_series,
    update_backup_settings,
    update_project_info,
    update_series,
)
from src.utils.backup_manager import (
    APP_VERSION,
    BACKUP_DIR,
    create_backup,
    delete_backup,
    export_project_zip,
    get_recent_activity,
    hours_since_last_backup,
    import_project_zip,
    list_backups,
    list_packages,
    restore_backup,
    validate_package,
)
from src.pipeline.export_pipeline import (
    STAGE_ORDER,
    STATUS_LABELS,
    STATUS_OPTIONS,
    create_export_package,
    load_production_state,
    mark_stage,
)
from src.pipeline.script_pipeline import load_episode_data
from src.director.director_planner import plan_exists as director_plan_exists

st.set_page_config(
    page_title="プロジェクト管理",
    page_icon="📁",
    layout="wide",
)

# ── ProjectContext — future-ready session object ───────────────────────────────

if "pm_ctx" not in st.session_state:
    ctx_obj = ProjectContext()
    st.session_state["pm_ctx"] = ctx_obj.as_dict()
ctx: dict = st.session_state["pm_ctx"]

# ── Header ─────────────────────────────────────────────────────────────────────

proj_info = get_project_info()
st.title("📁 プロジェクト管理")
_hdr = st.columns([4, 1])
with _hdr[0]:
    st.caption(
        f"**{proj_info.get('name', '')}**  |  "
        f"{proj_info.get('target_channel', '') or '(チャンネル未設定)'}  |  "
        f"v{ctx['version']}  |  モード: {ctx['subscription_tier']}"
    )
with _hdr[1]:
    if st.button("🔄 更新", key="pm_global_refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ── Auto-backup (once per session) ────────────────────────────────────────────

bkp_settings = get_backup_settings()
if bkp_settings.get("auto_enabled", True) and not st.session_state.get("pm_auto_backup_done"):
    h_check = hours_since_last_backup()
    threshold = bkp_settings.get("interval_hours", 24)
    if h_check is None or h_check > threshold:
        try:
            create_backup(
                label="自動バックアップ",
                include_project=bkp_settings.get("include_project_json", True),
            )
        except Exception:
            pass
    st.session_state["pm_auto_backup_done"] = True

# ── Episode scan (cached) ─────────────────────────────────────────────────────

_project_dir = PROJECT_ROOT / "project"
_IMAGE_EXT   = {".png", ".jpg", ".jpeg", ".webp"}
_CLIP_EXT    = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
_AUDIO_EXT   = {".mp3", ".wav", ".m4a", ".ogg", ".aac"}


@st.cache_data(ttl=60)
def _scan_episodes() -> list[dict]:
    results: list[dict] = []
    if not _project_dir.exists():
        return results
    for d in sorted(_project_dir.iterdir()):
        if not d.is_dir():
            continue
        ep_json = d / "episode.json"
        if not ep_json.exists():
            continue
        ep_data: dict = {}
        try:
            ep_data = json.loads(ep_json.read_text(encoding="utf-8"))
        except Exception:
            pass
        sections  = ep_data.get("sections", [])
        total_dur = ep_data.get("total_duration_seconds") or sum(
            s.get("duration_seconds", 0) for s in sections
        )
        img_dir = d / "assets" / "images"
        vid_dir = d / "videos"
        voi_dir = d / "voices"
        img_c = sum(1 for f in img_dir.iterdir() if f.suffix.lower() in _IMAGE_EXT) if img_dir.exists() else 0
        vid_c = sum(1 for f in vid_dir.iterdir() if f.suffix.lower() in _CLIP_EXT)  if vid_dir.exists() else 0
        voi_c = sum(1 for f in voi_dir.iterdir() if f.suffix.lower() in _AUDIO_EXT) if voi_dir.exists() else 0
        total_bytes = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        prod_state  = load_production_state(d)
        archived    = prod_state.get("archived", False)
        has_export  = (d / "export" / "production_report.json").exists()
        has_dir     = director_plan_exists(d)
        # Status
        has_final = any(f.suffix.lower() in {".mp4", ".mov", ".webm"} for f in d.iterdir() if f.is_file())
        if archived:
            status = "アーカイブ"
        elif has_final:
            status = "完成"
        elif sections:
            status = "制作中"
        else:
            status = "未着手"
        # Production time estimate
        prod_time_h: float | None = None
        done_ats = [
            s.get("completed_at")
            for s in prod_state.get("stages", {}).values()
            if s.get("completed_at") and s.get("status") == "done"
        ]
        if done_ats:
            try:
                ctime    = ep_json.stat().st_ctime
                last_done = max(datetime.fromisoformat(t) for t in done_ats)
                prod_time_h = max(0.0, (last_done - datetime.fromtimestamp(ctime)).total_seconds() / 3600)
            except Exception:
                pass
        results.append({
            "ep_id":      d.name,
            "title":      ep_data.get("title", ""),
            "scenes":     len(sections),
            "total_dur":  total_dur,
            "status":     status,
            "archived":   archived,
            "img_count":  img_c,
            "vid_count":  vid_c,
            "voi_count":  voi_c,
            "has_dir":    has_dir,
            "has_export": has_export,
            "total_mb":   total_bytes / 1024 / 1024,
            "prod_time_h": prod_time_h,
            "ep_dir":     d,
            "prod_state": prod_state,
        })
    return results


@st.cache_data(ttl=120)
def _count_config(cfg: str, key: str) -> int:
    p = PROJECT_ROOT / "config" / cfg
    if not p.exists():
        return 0
    try:
        return len(json.loads(p.read_text(encoding="utf-8")).get(key, []))
    except Exception:
        return 0


episodes     = _scan_episodes()
series_list  = list_all_series()

# ── Tabs ──────────────────────────────────────────────────────────────────────

(
    tab_ov, tab_series, tab_analytics,
    tab_backup, tab_package, tab_batch,
) = st.tabs([
    "🏠 概要",
    "📺 シリーズ",
    "📊 アナリティクス",
    "💾 バックアップ",
    "📦 パッケージ",
    "⚡ 一括操作",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — PROJECT OVERVIEW
# ══════════════════════════════════════════════════════════════════════════════

with tab_ov:

    total_eps = len(episodes)
    done_eps  = sum(1 for e in episodes if e["status"] == "完成")
    wip_eps   = sum(1 for e in episodes if e["status"] == "制作中")
    arch_eps  = sum(1 for e in episodes if e["archived"])
    with_dir  = sum(1 for e in episodes if e["has_dir"])
    with_exp  = sum(1 for e in episodes if e["has_export"])
    n_chars   = _count_config("characters.json",       "characters")
    n_bgs     = _count_config("backgrounds.json",      "backgrounds")
    n_tmpl    = _count_config("prompt_templates.json", "templates")
    n_series  = len([s for s in series_list if not s.get("archived", False)])
    total_imgs = sum(e["img_count"] for e in episodes)
    total_vids = sum(e["vid_count"] for e in episodes)
    total_vois = sum(e["voi_count"] for e in episodes)
    total_gb   = sum(e["total_mb"]  for e in episodes) / 1024

    # ── Top metric row ─────────────────────────────────────────────────────────
    st.subheader("アクティブプロジェクト")
    m = st.columns(8)
    m[0].metric("📁 エピソード", total_eps)
    m[1].metric("✅ 完成",       done_eps)
    m[2].metric("🔄 制作中",     wip_eps)
    m[3].metric("🧑 キャラ",     n_chars)
    m[4].metric("🏞️ 背景",       n_bgs)
    m[5].metric("📝 テンプレ",   n_tmpl)
    m[6].metric("📺 シリーズ",   n_series)
    m[7].metric("💾 合計",       f"{total_gb:.2f} GB")

    st.divider()

    left_ov, right_ov = st.columns([3, 2])

    with left_ov:
        # ── Assets ─────────────────────────────────────────────────────────────
        st.subheader("素材統計")
        ac = st.columns(3)
        ac[0].metric("🖼️ 画像", total_imgs)
        ac[1].metric("🎬 動画", total_vids)
        ac[2].metric("🎙️ 音声", total_vois)

        # ── Progress bars ──────────────────────────────────────────────────────
        st.subheader("制作進捗")
        for label, val, total in [
            ("演出計画カバー率",     with_dir, total_eps),
            ("エクスポート完了率",   with_exp, total_eps),
            ("完成率",               done_eps, total_eps),
        ]:
            pct = int(val / total * 100) if total else 0
            st.caption(label)
            st.progress(pct / 100, text=f"{pct}%  ({val}/{total})")

        st.divider()

        # ── Recent exports ─────────────────────────────────────────────────────
        st.subheader("📦 最近の書き出し")
        exp_reports: list[dict] = []
        if _project_dir.exists():
            for ep_dir in _project_dir.iterdir():
                rp = ep_dir / "export" / "production_report.json"
                if rp.exists():
                    try:
                        d = json.loads(rp.read_text(encoding="utf-8"))
                        exp_reports.append({"ep_id": ep_dir.name,
                                            "date": d.get("created_at", ""),
                                            "files": len(d.get("files", {}))})
                    except Exception:
                        pass
        exp_reports.sort(key=lambda x: x["date"], reverse=True)
        for r in exp_reports[:5]:
            st.caption(f"📦 `{r['ep_id']}` — {r['date'][:16]}  ({r['files']} files)")
        if not exp_reports:
            st.caption("書き出し履歴なし")

        st.divider()

        # ── Recent backups ─────────────────────────────────────────────────────
        st.subheader("💾 最近のバックアップ")
        for b in list_backups()[:4]:
            lbl = f" [{b['label']}]" if b["label"] else ""
            st.caption(f"💾 `{b['name'][:32]}`{lbl} — {b['created_at'][:16]}  {b['size_mb']:.1f} MB")
        if not list_backups():
            st.caption("バックアップなし")

    with right_ov:
        # ── Recent activity ────────────────────────────────────────────────────
        st.subheader("📋 最近のアクティビティ")
        for item in get_recent_activity(max_items=20):
            st.caption(f"📄 `{item['path']}` — {item['mtime_dt']}")

        st.divider()

        # ── Project info card ──────────────────────────────────────────────────
        st.subheader("⚙️ プロジェクト情報")
        info = get_project_info()
        st.caption(f"**名前:** {info.get('name', '')}")
        st.caption(f"**チャンネル:** {info.get('target_channel', '') or '(未設定)'}")
        st.caption(f"**ジャンル:** {info.get('genre', '')}")
        st.caption(f"**言語:** {info.get('language', '')}")
        st.caption(f"**バージョン:** v{ctx['version']}")
        st.caption(f"**更新日:** {info.get('updated_at', '')[:10]}")
        if st.button("✏️ 設定を編集", key="pm_ov_edit_settings", use_container_width=True):
            # Redirect user to settings section via a flag
            st.session_state["pm_goto_settings"] = True
            st.info("ページ下部の「⚙️ プロジェクト設定」で編集できます。")

        st.divider()
        st.caption("**拡張ステータス (FUTURE)**")
        for feat, enabled in ctx["features"].items():
            icon = "✅" if enabled else "⬜"
            st.caption(f"{icon} {feat}")
        st.caption("*cloud sync / multi-user / auto-publish — 将来の拡張ポイント*")

    # ── Project settings form (shown below) ────────────────────────────────────
    st.divider()
    st.subheader("⚙️ プロジェクト設定")
    ps1, ps2 = st.columns(2)
    with ps1:
        p_name = st.text_input("プロジェクト名", value=info.get("name", ""), key="pm_ps_name")
        p_desc = st.text_area("説明", value=info.get("description", ""), height=80, key="pm_ps_desc")
        p_ch   = st.text_input("チャンネル", value=info.get("target_channel", ""),
                               key="pm_ps_ch", placeholder="@channel_name")
    with ps2:
        _gi = GENRE_OPTIONS.index(info.get("genre", GENRE_OPTIONS[0])) \
              if info.get("genre") in GENRE_OPTIONS else 0
        _li = LANGUAGE_OPTIONS.index(info.get("language", "ja")) \
              if info.get("language") in LANGUAGE_OPTIONS else 0
        p_genre = st.selectbox("ジャンル", GENRE_OPTIONS, index=_gi, key="pm_ps_genre")
        p_lang  = st.selectbox("言語", LANGUAGE_OPTIONS, index=_li, key="pm_ps_lang")
        st.caption(f"作成日: {info.get('created_at', '')[:10]}")
    if st.button("💾 プロジェクト設定を保存", type="primary", use_container_width=True, key="pm_ps_save"):
        update_project_info({
            "name":           p_name.strip(),
            "description":    p_desc.strip(),
            "target_channel": p_ch.strip(),
            "genre":          p_genre,
            "language":       p_lang,
        })
        st.success("保存しました ✅")
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SERIES MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════

with tab_series:

    s_l, s_r = st.columns([2, 3])

    with s_l:
        st.subheader("📺 シリーズ一覧")
        show_arch_s = st.checkbox("アーカイブ済みを表示", key="pm_s_arch_toggle")
        disp_series = list_all_series() if show_arch_s else list_series()

        if not disp_series:
            st.info("シリーズがありません。")
        else:
            for s in disp_series:
                n = len(s.get("episode_ids", []))
                badge = " 📦" if s.get("archived") else ""
                is_sel = st.session_state.get("pm_sel_sid") == s["id"]
                if st.button(
                    f"**{s['name']}**{badge}  ({n} EP)",
                    key=f"pm_slist_{s['id']}",
                    use_container_width=True,
                    type="primary" if is_sel else "secondary",
                ):
                    st.session_state["pm_sel_sid"] = s["id"]
                    st.rerun()

        st.divider()
        st.subheader("➕ 新規作成")
        ns_name = st.text_input("シリーズ名", key="pm_ns_name", placeholder="例: Python入門シリーズ")
        ns_desc = st.text_input("説明（任意）", key="pm_ns_desc")
        if st.button("✚ 作成", use_container_width=True, key="pm_ns_create"):
            if not ns_name.strip():
                st.error("シリーズ名を入力してください")
            else:
                ns = add_series(ns_name, ns_desc)
                st.session_state["pm_sel_sid"] = ns["id"]
                st.success(f"「{ns['name']}」を作成しました")
                st.rerun()

    with s_r:
        sel_sid = st.session_state.get("pm_sel_sid")
        if not sel_sid:
            st.info("左のシリーズを選択するか、新規作成してください。")
        else:
            sel_s = next((s for s in list_all_series() if s["id"] == sel_sid), None)
            if not sel_s:
                st.session_state.pop("pm_sel_sid", None)
                st.rerun()
            else:
                arch_tag = " (アーカイブ済)" if sel_s.get("archived") else ""
                st.subheader(f"📺 {sel_s['name']}{arch_tag}")

                # Edit name/desc
                with st.expander("✏️ 名前・説明を編集"):
                    e_name = st.text_input("名前", value=sel_s["name"],
                                           key=f"pm_se_name_{sel_sid}")
                    e_desc = st.text_input("説明", value=sel_s.get("description",""),
                                           key=f"pm_se_desc_{sel_sid}")
                    if st.button("💾 保存", key=f"pm_se_save_{sel_sid}",
                                 use_container_width=True):
                        update_series(sel_sid, {"name": e_name, "description": e_desc})
                        st.success("更新しました")
                        st.rerun()

                # Quick actions
                qa = st.columns(3)
                arch_label = "📦 アーカイブ" if not sel_s.get("archived") else "♻️ 復元"
                if qa[0].button(arch_label, key=f"pm_s_arch_{sel_sid}",
                                use_container_width=True):
                    archive_series(sel_sid, not sel_s.get("archived", False))
                    st.rerun()
                if qa[1].button("📋 複製", key=f"pm_s_dup_{sel_sid}",
                                use_container_width=True):
                    dup = duplicate_series(sel_sid)
                    if dup:
                        st.success(f"「{dup['name']}」を作成しました")
                        st.session_state["pm_sel_sid"] = dup["id"]
                        st.rerun()
                if qa[2].button("📤 一括書き出し", key=f"pm_s_export_{sel_sid}",
                                use_container_width=True):
                    ok_ids: list[str] = []
                    ng_ids: list[str] = []
                    for eid in sel_s.get("episode_ids", []):
                        ep_dir = _project_dir / eid
                        if not ep_dir.exists():
                            continue
                        try:
                            create_export_package(
                                episode_dir=ep_dir,
                                production_state=load_production_state(ep_dir),
                                episode_data=load_episode_data(ep_dir),
                            )
                            ok_ids.append(eid)
                        except Exception as exc:
                            ng_ids.append(f"{eid}({exc})")
                    if ok_ids:
                        st.success(f"✅ {', '.join(ok_ids)}")
                    if ng_ids:
                        st.error(f"❌ {', '.join(ng_ids)}")

                st.divider()

                # Episode order
                ep_ids_in = sel_s.get("episode_ids", [])
                ep_all    = [e["ep_id"] for e in episodes]
                st.caption(f"**エピソード順序** ({len(ep_ids_in)} 件)")

                for i, eid in enumerate(ep_ids_in):
                    ep_info = next((e for e in episodes if e["ep_id"] == eid), None)
                    title   = ep_info["title"][:28] if ep_info else ""
                    rc = st.columns([1, 4, 1, 1, 1])
                    rc[0].caption(f"#{i+1}")
                    rc[1].caption(f"`{eid}` {title}")
                    if i > 0 and rc[2].button("↑", key=f"pm_up_{sel_sid}_{eid}"):
                        order = list(ep_ids_in)
                        order[i-1], order[i] = order[i], order[i-1]
                        set_episode_order_in_series(sel_sid, order)
                        st.rerun()
                    if i < len(ep_ids_in)-1 and rc[3].button("↓", key=f"pm_dn_{sel_sid}_{eid}"):
                        order = list(ep_ids_in)
                        order[i], order[i+1] = order[i+1], order[i]
                        set_episode_order_in_series(sel_sid, order)
                        st.rerun()
                    if rc[4].button("✕", key=f"pm_srm_{sel_sid}_{eid}",
                                    help="シリーズから削除"):
                        remove_episode_from_series(sel_sid, eid)
                        st.rerun()

                # Batch rename episodes in series
                if ep_ids_in:
                    with st.expander("✏️ 一括リネーム（タイトル変更）"):
                        renames: dict[str, str] = {}
                        for eid in ep_ids_in:
                            ep_info   = next((e for e in episodes if e["ep_id"] == eid), None)
                            cur_title = ep_info["title"] if ep_info else ""
                            new_t     = st.text_input(f"`{eid}`", value=cur_title,
                                                      key=f"pm_brn_{sel_sid}_{eid}")
                            if new_t.strip() != cur_title:
                                renames[eid] = new_t
                        if renames and st.button("💾 リネームを適用",
                                                  key=f"pm_brn_apply_{sel_sid}",
                                                  use_container_width=True):
                            updated = batch_rename_episodes(renames)
                            st.success(f"✅ {len(updated)} 件を更新しました")
                            st.cache_data.clear()
                            st.rerun()

                # Add episode
                ep_not_in = [eid for eid in ep_all if eid not in ep_ids_in]
                if ep_not_in:
                    st.divider()
                    ac = st.columns([3, 1])
                    add_ep = ac[0].selectbox("エピソードを追加", ep_not_in,
                                             key=f"pm_sadd_{sel_sid}",
                                             label_visibility="collapsed")
                    if ac[1].button("追加", key=f"pm_sadd_btn_{sel_sid}",
                                    use_container_width=True):
                        add_episode_to_series(sel_sid, add_ep)
                        st.rerun()

                # Delete series
                st.divider()
                with st.expander("⚠️ シリーズを削除"):
                    del_chk_s = st.checkbox(
                        f"「{sel_s['name']}」を削除（エピソードは削除されません）",
                        key=f"pm_sdel_chk_{sel_sid}",
                    )
                    if st.button("🗑️ 削除する", disabled=not del_chk_s,
                                 key=f"pm_sdel_btn_{sel_sid}", use_container_width=True):
                        delete_series(sel_sid)
                        st.session_state.pop("pm_sel_sid", None)
                        st.success("シリーズを削除しました")
                        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — PRODUCTION ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

with tab_analytics:

    st.subheader("📊 制作アナリティクス")

    an_eps = [e for e in episodes if not e["archived"]]
    n_done = sum(1 for e in an_eps if e["status"] == "完成")
    n_wip  = sum(1 for e in an_eps if e["status"] == "制作中")
    n_none = sum(1 for e in an_eps if e["status"] == "未着手")
    times  = [e["prod_time_h"] for e in an_eps if e["prod_time_h"] is not None]
    avg_h  = sum(times) / len(times) if times else None

    done_pct3 = int(n_done / len(an_eps) * 100) if an_eps else 0
    wip_pct3  = int(n_wip  / len(an_eps) * 100) if an_eps else 0

    am = st.columns(5)
    am[0].metric("✅ 完成",    n_done, f"{done_pct3}%")
    am[1].metric("🔄 制作中", n_wip,  f"{wip_pct3}%")
    am[2].metric("⏸ 未着手", n_none)
    am[3].metric("🗄️ アーカイブ", arch_eps)
    am[4].metric("⏱ 平均制作時間",
                 f"{avg_h:.1f}h" if avg_h is not None else "N/A",
                 help="ステージ完了タイムスタンプから推定")

    st.divider()

    # ── Episode table ──────────────────────────────────────────────────────────

    st.subheader("エピソード別詳細")
    _hdr_cols = st.columns([2, 4, 2, 2, 2, 2, 2])
    for label, col in zip(
        ["**ID**", "**タイトル**", "**ステータス**", "**素材**", "**サイズ/尺**", "**制作時間**", "**フラグ**"],
        _hdr_cols
    ):
        col.caption(label)

    for ep in episodes:
        mins, secs = divmod(int(ep["total_dur"]), 60)
        dur_str = f"{mins}:{secs:02d}"
        pt_str  = f"{ep['prod_time_h']:.1f}h" if ep["prod_time_h"] is not None else "--"
        flags   = ("📦" if ep["has_export"] else "") + ("🎭" if ep["has_dir"] else "")
        row = st.columns([2, 4, 2, 2, 2, 2, 2])
        row[0].caption(f"`{ep['ep_id']}`")
        row[1].caption(ep["title"][:35] or "（未設定）")
        row[2].caption(f"{'🗄️' if ep['archived'] else ''}{ep['status']}")
        row[3].caption(f"🖼{ep['img_count']} 🎬{ep['vid_count']} 🎙{ep['voi_count']}")
        row[4].caption(f"{ep['total_mb']:.1f}MB  {dur_str}")
        row[5].caption(pt_str)
        row[6].caption(flags or "—")

    st.divider()

    # ── Stage completion ───────────────────────────────────────────────────────

    st.subheader("制作ステージ完了状況")
    STAGE_JP = {"script":"台本","images":"画像","videos":"動画","voice":"音声","bgm":"BGM","se":"効果音"}
    stage_done = {stage: 0 for stage in STAGE_ORDER}
    for ep in an_eps:
        for stage in STAGE_ORDER:
            if ep["prod_state"].get("stages", {}).get(stage, {}).get("status") == "done":
                stage_done[stage] += 1

    if an_eps:
        sc = st.columns(len(STAGE_ORDER))
        for col, stage in zip(sc, STAGE_ORDER):
            cnt = stage_done[stage]
            pct = int(cnt / len(an_eps) * 100) if an_eps else 0
            col.metric(STAGE_JP.get(stage, stage), cnt)
            col.progress(pct / 100)

    st.divider()

    # ── Export history ─────────────────────────────────────────────────────────

    st.subheader("📦 書き出し履歴")
    exports: list[dict] = []
    if _project_dir.exists():
        for ep_dir in _project_dir.iterdir():
            rp = ep_dir / "export" / "production_report.json"
            if rp.exists():
                try:
                    d = json.loads(rp.read_text(encoding="utf-8"))
                    exports.append({
                        "ep":    ep_dir.name,
                        "date":  d.get("created_at", ""),
                        "files": len(d.get("files", {})),
                        "dir":   "director" in d,
                    })
                except Exception:
                    pass
    exports.sort(key=lambda x: x["date"], reverse=True)

    if not exports:
        st.info("書き出し履歴がありません。🎬 制作管理 ページで書き出しを実行してください。")
    else:
        eh = st.columns([2, 4, 2, 1])
        for label in ["**エピソード**", "**書き出し日時**", "**ファイル数**", "**Dir**"]:
            eh[next(iter(range(4)))].caption(label)
        eh = st.columns([2, 4, 2, 1])
        eh[0].caption("**エピソード**")
        eh[1].caption("**書き出し日時**")
        eh[2].caption("**ファイル数**")
        eh[3].caption("**Dir**")
        for ex in exports:
            ec = st.columns([2, 4, 2, 1])
            ec[0].caption(f"`{ex['ep']}`")
            ec[1].caption(ex["date"][:19])
            ec[2].caption(str(ex["files"]))
            ec[3].caption("🎭" if ex["dir"] else "—")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — BACKUP & RESTORE
# ══════════════════════════════════════════════════════════════════════════════

with tab_backup:

    b_l, b_r = st.columns([3, 2])

    with b_l:
        st.subheader("💾 バックアップ履歴")

        # Status banner
        h_since  = hours_since_last_backup()
        bk_set   = get_backup_settings()
        interval = bk_set.get("interval_hours", 24)
        if h_since is None:
            st.warning("バックアップがまだ存在しません。今すぐ作成してください。")
        elif h_since > interval:
            st.warning(f"最後のバックアップから {h_since:.0f} 時間が経過しています。")
        else:
            st.success(f"最終バックアップ: {h_since:.1f} 時間前 ✅")

        # Manual backup trigger
        bc = st.columns([3, 1])
        bk_label = bc[0].text_input("ラベル（任意）", key="pm_bk_label",
                                     placeholder="例: リリース前")
        bc[1].write("")
        bc[1].write("")
        if bc[1].button("💾 今すぐバックアップ", key="pm_bk_now",
                        use_container_width=True, type="primary"):
            with st.spinner("作成中..."):
                try:
                    res = create_backup(
                        label=bk_label,
                        include_project=bk_set.get("include_project_json", True),
                    )
                    st.success(f"✅ `{res['path'].name}` ({res['size_mb']:.1f} MB)")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as exc:
                    st.error(f"失敗: {exc}")

        st.divider()

        # Backup list
        backups = list_backups()
        if not backups:
            st.info("バックアップがありません。")
        for bk in backups:
            lbl = f" [{bk['label']}]" if bk["label"] else ""
            bc2 = st.columns([5, 1, 1, 1])
            bc2[0].caption(
                f"💾 `{bk['name'][:28]}`{lbl}\n\n"
                f"{bk['created_at'][:16]} · {bk['size_mb']:.1f} MB · "
                f"v{bk['app_version']} · {bk['episode_count']} EP"
            )
            # Download
            bk_uid = bk.get("backup_id") or bk["name"]
            try:
                bc2[1].download_button("⬇️", data=bk["path"].read_bytes(),
                                       file_name=bk["name"], mime="application/zip",
                                       key=f"pm_bkdl_{bk_uid}")
            except Exception:
                bc2[1].caption("—")
            if bc2[2].button("♻️", key=f"pm_bk_rst_{bk['name']}",
                             help="このバックアップから復元"):
                st.session_state["pm_restore_target"] = str(bk["path"])
                st.rerun()
            if bc2[3].button("🗑️", key=f"pm_bk_del_{bk['name']}",
                             help="削除"):
                delete_backup(bk["path"])
                st.rerun()

    with b_r:
        st.subheader("♻️ 復元")
        restore_target = st.session_state.get("pm_restore_target")
        if restore_target:
            rp = Path(restore_target)
            st.info(f"復元対象: `{rp.name}`")
            v = validate_package(rp)
            for e in v["errors"]:
                st.error(e)
            for w in v["warnings"]:
                st.warning(w)
            if v["manifest"]:
                m = v["manifest"]
                st.caption(
                    f"v{m.get('app_version')} | "
                    f"{m.get('backup_date','')[:16]} | "
                    f"{m.get('episode_count')} EP"
                )
            if v["is_valid"]:
                r_cfg = st.checkbox("設定ファイルを上書き (config/)", value=True,
                                    key="pm_rst_cfg")
                r_prj = st.checkbox("プロジェクトJSONを上書き (project/)", value=False,
                                    key="pm_rst_prj")
                st.warning("復元を実行すると現在のデータが上書きされます。")
                rc = st.columns(2)
                if rc[0].button("✅ 復元を実行", type="primary",
                                key="pm_rst_run", use_container_width=True):
                    with st.spinner("復元中..."):
                        try:
                            res = restore_backup(rp, overwrite_config=r_cfg,
                                                 overwrite_project=r_prj)
                            st.success(f"✅ {len(res['restored'])} ファイルを復元しました")
                            if res["skipped"]:
                                st.caption(f"スキップ: {len(res['skipped'])} ファイル")
                            st.cache_data.clear()
                            st.session_state.pop("pm_restore_target", None)
                            st.rerun()
                        except Exception as exc:
                            st.error(f"復元失敗: {exc}")
                if rc[1].button("キャンセル", key="pm_rst_cancel",
                                use_container_width=True):
                    st.session_state.pop("pm_restore_target", None)
                    st.rerun()
        else:
            st.info("左の ♻️ ボタンで復元対象を選択してください。")

        st.divider()
        st.subheader("⚙️ バックアップ設定")
        bk_set    = get_backup_settings()
        auto_en   = st.checkbox("自動バックアップ", value=bk_set.get("auto_enabled", True),
                                key="pm_bks_auto")
        interval2 = st.number_input("間隔（時間）", min_value=1, max_value=168,
                                    value=bk_set.get("interval_hours", 24), key="pm_bks_int")
        max_keep  = st.number_input("最大保存数", min_value=3, max_value=100,
                                    value=bk_set.get("max_keep", 20), key="pm_bks_max")
        inc_prj   = st.checkbox("プロジェクトJSONを含める",
                                value=bk_set.get("include_project_json", True), key="pm_bks_prj")
        if st.button("💾 設定を保存", key="pm_bks_save", use_container_width=True):
            update_backup_settings({
                "auto_enabled": auto_en, "interval_hours": int(interval2),
                "max_keep": int(max_keep), "include_project_json": inc_prj,
            })
            st.success("設定を保存しました ✅")

        st.divider()
        total_bk_mb = sum(b["size_mb"] for b in list_backups())
        st.caption(f"保存先: `{BACKUP_DIR.relative_to(PROJECT_ROOT)}/`")
        st.caption(f"使用容量: {total_bk_mb:.1f} MB ({len(backups)} 件)")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — PROJECT PACKAGE
# ══════════════════════════════════════════════════════════════════════════════

with tab_package:

    pk_l, pk_r = st.columns(2)

    with pk_l:
        st.subheader("📤 パッケージをエクスポート")
        st.caption(
            "設定・エピソードJSON・テキスト出力をZIPに書き出します。"
            "メディアファイル（画像・動画・音声）は含まれません。"
        )
        pk_label = st.text_input("ラベル（任意）", key="pm_pk_label",
                                  placeholder="例: version_3_1_release")
        if st.button("📦 ZIPを作成", type="primary", use_container_width=True,
                     key="pm_pk_export"):
            with st.spinner("作成中..."):
                try:
                    zip_path = export_project_zip(label=pk_label)
                    st.session_state["pm_pk_ready"] = str(zip_path)
                    st.success(f"✅ `{zip_path.name}`")
                    st.rerun()
                except Exception as exc:
                    st.error(f"エラー: {exc}")

        if st.session_state.get("pm_pk_ready"):
            pkp = Path(st.session_state["pm_pk_ready"])
            if pkp.exists():
                st.download_button(
                    "⬇️ ZIPをダウンロード",
                    data=pkp.read_bytes(),
                    file_name=pkp.name,
                    mime="application/zip",
                    use_container_width=True,
                    key="pm_pk_dl",
                )

        st.divider()
        st.subheader("📋 既存パッケージ")
        pkgs = list_packages()
        for pkg in pkgs[:6]:
            pc = st.columns([5, 2])
            pc[0].caption(f"📦 `{pkg['name'][:30]}`  {pkg['created_at'][:16]}  {pkg['size_mb']:.1f} MB")
            try:
                pc[1].download_button("⬇️", data=Path(pkg["path"]).read_bytes(),
                                      file_name=pkg["name"], mime="application/zip",
                                      key=f"pm_pkdl_{pkg['name']}")
            except Exception:
                pass
        if not pkgs:
            st.caption("パッケージなし")

    with pk_r:
        st.subheader("📥 パッケージをインポート")
        st.caption("ZIPをアップロードして設定・エピソードデータを復元します。")
        uploaded = st.file_uploader("ZIPファイル", type=["zip"], key="pm_pk_upload")
        if uploaded:
            raw = uploaded.read()
            # Validate
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                tmp.write(raw)
                tmp_path = Path(tmp.name)
            try:
                v = validate_package(tmp_path)
            finally:
                try:
                    tmp_path.unlink(missing_ok=True)
                except Exception:
                    pass

            st.subheader("🔍 検証結果")
            for err in v["errors"]:
                st.error(err)
            for warn in v["warnings"]:
                st.warning(warn)
            if v["is_valid"]:
                st.success("✅ パッケージが有効です")
            if v["manifest"]:
                m = v["manifest"]
                st.caption(
                    f"バージョン: {m.get('app_version', '不明')} | "
                    f"作成: {(m.get('export_date') or m.get('backup_date', ''))[:16]} | "
                    f"{m.get('episode_count', '?')} EP | {m.get('file_count', '?')} files"
                )
                # Version compatibility
                pkg_ver = m.get("app_version", "")
                if pkg_ver == APP_VERSION:
                    st.caption(f"✅ バージョン互換: {APP_VERSION}")
                elif pkg_ver:
                    st.warning(
                        f"バージョン不一致: パッケージ={pkg_ver} / 現在={APP_VERSION}。"
                        "インポートは可能ですが一部の設定が正しく動作しない場合があります。"
                    )

            if v["is_valid"]:
                imp_cfg = st.checkbox("設定ファイルを上書き (config/)", value=True,
                                      key="pm_imp_cfg")
                imp_prj = st.checkbox("プロジェクトJSONを上書き (project/)", value=False,
                                      key="pm_imp_prj")
                st.warning("インポートを実行すると既存データが上書きされます。")
                if st.button("📥 インポートを実行", type="primary",
                             use_container_width=True, key="pm_imp_run"):
                    with st.spinner("インポート中..."):
                        result = import_project_zip(raw,
                                                    overwrite_config=imp_cfg,
                                                    overwrite_project=imp_prj)
                    if result["success"]:
                        st.success(f"✅ {len(result['restored'])} ファイルをインポートしました")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        for e in result["errors"]:
                            st.error(e)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — BATCH OPERATIONS
# ══════════════════════════════════════════════════════════════════════════════

with tab_batch:

    st.subheader("⚡ 一括操作")

    if not episodes:
        st.info("エピソードがありません。")
    else:
        show_arch_b = st.checkbox("アーカイブ済みも表示", key="pm_batch_arch_toggle")
        pool        = episodes if show_arch_b else [e for e in episodes if not e["archived"]]

        if st.checkbox("すべて選択", key="pm_batch_all"):
            for e in pool:
                st.session_state[f"pm_bchk_{e['ep_id']}"] = True

        cols_n = 4
        sel_ids: list[str] = []
        rows = [pool[i:i+cols_n] for i in range(0, len(pool), cols_n)]
        for row in rows:
            rcols = st.columns(cols_n)
            for col, ep in zip(rcols, row):
                arch_tag = " 🗄️" if ep["archived"] else ""
                checked  = col.checkbox(
                    f"`{ep['ep_id']}`{arch_tag}\n{ep['title'][:16] or '（未設定）'}",
                    key=f"pm_bchk_{ep['ep_id']}",
                    value=st.session_state.get(f"pm_bchk_{ep['ep_id']}", False),
                )
                if checked:
                    sel_ids.append(ep["ep_id"])

        st.caption(f"**{len(sel_ids)} / {len(pool)} 件を選択中**")

        if not sel_ids:
            st.info("上のチェックボックスでエピソードを選択してください。")
        else:
            st.divider()
            (
                bt1, bt2, bt3, bt4, bt5
            ) = st.tabs(["📦 書き出し", "🗄️ アーカイブ", "📋 複製", "✏️ リネーム", "🗑️ 削除"])

            # ── Batch Export ───────────────────────────────────────────────────
            with bt1:
                st.caption("選択したエピソードの書き出しパッケージを一括作成します。")
                if st.button(f"📦 {len(sel_ids)} 件を書き出し", type="primary",
                             use_container_width=True, key="pm_bt_export"):
                    ok_l: list[str] = []
                    ng_l: list[str] = []
                    prog = st.progress(0)
                    for i, eid in enumerate(sel_ids):
                        ep_dir = _project_dir / eid
                        try:
                            create_export_package(
                                episode_dir=ep_dir,
                                production_state=load_production_state(ep_dir),
                                episode_data=load_episode_data(ep_dir),
                            )
                            ok_l.append(eid)
                        except Exception as exc:
                            ng_l.append(f"{eid}({exc})")
                        prog.progress((i+1)/len(sel_ids))
                    if ok_l:
                        st.success(f"✅ {', '.join(ok_l)}")
                    if ng_l:
                        st.error(f"❌ {', '.join(ng_l)}")
                    st.cache_data.clear()

            # ── Batch Archive ──────────────────────────────────────────────────
            with bt2:
                st.caption("選択したエピソードをアーカイブします（ファイルは保持されます）。")
                arch_mode = st.radio("操作", ["アーカイブ", "アーカイブ解除"],
                                     key="pm_bt_arch_mode", horizontal=True)
                if st.button(
                    f"🗄️ {len(sel_ids)} 件を{arch_mode}",
                    type="primary", use_container_width=True, key="pm_bt_arch"
                ):
                    done_a = [eid for eid in sel_ids
                              if archive_episode(eid, arch_mode == "アーカイブ")]
                    st.success(f"✅ {len(done_a)} 件を{arch_mode}しました")
                    st.cache_data.clear()
                    st.rerun()

            # ── Batch Duplicate ────────────────────────────────────────────────
            with bt3:
                st.caption("JSONとテキストファイルを複製します。メディアは複製されません。")
                if st.button(
                    f"📋 {len(sel_ids)} 件を複製",
                    type="primary", use_container_width=True, key="pm_bt_dup"
                ):
                    dup_ok:   list[str] = []
                    dup_fail: list[str] = []
                    for eid in sel_ids:
                        new_id = duplicate_episode(eid)
                        if new_id:
                            dup_ok.append(f"{eid}→{new_id}")
                        else:
                            dup_fail.append(eid)
                    if dup_ok:
                        st.success("✅ 複製完了:\n" + "\n".join(dup_ok))
                    if dup_fail:
                        st.error(f"❌ 失敗: {', '.join(dup_fail)}")
                    st.cache_data.clear()
                    st.rerun()

            # ── Batch Rename ───────────────────────────────────────────────────
            with bt4:
                st.caption("選択したエピソードのタイトルを一括変更します。")
                renames_bt: dict[str, str] = {}
                for eid in sel_ids:
                    ep_info   = next((e for e in episodes if e["ep_id"] == eid), None)
                    cur_title = ep_info["title"] if ep_info else ""
                    new_t     = st.text_input(f"`{eid}`", value=cur_title,
                                              key=f"pm_brn2_{eid}")
                    if new_t.strip() != cur_title:
                        renames_bt[eid] = new_t
                if renames_bt:
                    if st.button("✏️ リネームを適用", type="primary",
                                 use_container_width=True, key="pm_bt_rn_apply"):
                        updated = batch_rename_episodes(renames_bt)
                        st.success(f"✅ {len(updated)} 件を更新しました")
                        st.cache_data.clear()
                        st.rerun()
                else:
                    st.caption("変更なし")

            # ── Batch Delete ───────────────────────────────────────────────────
            with bt5:
                st.error("⚠️ この操作は取り消せません。エピソードフォルダが完全に削除されます。")
                st.caption("削除対象: " + ", ".join(f"`{e}`" for e in sel_ids))
                del_chk_b = st.checkbox(
                    f"上記 {len(sel_ids)} 件を完全に削除することを確認します",
                    key="pm_del_chk_b",
                )
                del_text_b = st.text_input(
                    '確認のため「DELETE」と入力してください',
                    key="pm_del_text_b",
                    placeholder="DELETE",
                )
                can_del = del_chk_b and del_text_b.strip() == "DELETE"
                if st.button(
                    f"🗑️ {len(sel_ids)} 件を完全削除",
                    disabled=not can_del,
                    type="primary",
                    use_container_width=True,
                    key="pm_bt_del",
                ):
                    del_ok_l:   list[str] = []
                    del_fail_l: list[str] = []
                    for eid in sel_ids:
                        if delete_episode(eid):
                            del_ok_l.append(eid)
                            st.session_state.pop(f"pm_bchk_{eid}", None)
                        else:
                            del_fail_l.append(eid)
                    if del_ok_l:
                        st.success(f"✅ 削除完了: {', '.join(del_ok_l)}")
                    if del_fail_l:
                        st.error(f"❌ 削除失敗: {', '.join(del_fail_l)}")
                    st.session_state.pop("pm_del_chk_b",  None)
                    st.session_state.pop("pm_del_text_b", None)
                    st.cache_data.clear()
                    st.rerun()
