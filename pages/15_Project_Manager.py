import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PROJECT_ROOT
from src.utils.settings_manager import load_settings
from src.utils.project_manager import (
    GENRE_OPTIONS,
    LANGUAGE_OPTIONS,
    add_episode_to_series,
    add_series,
    delete_series,
    get_project_info,
    list_series,
    load_project_settings,
    remove_episode_from_series,
    save_project_settings,
    set_episode_order_in_series,
    update_project_info,
    update_series,
)
from src.pipeline.export_pipeline import (
    create_export_package,
    load_production_state,
    mark_stage,
    STAGE_ORDER,
    STATUS_OPTIONS,
    STATUS_LABELS,
)
from src.pipeline.script_pipeline import load_episode_data
from src.director.director_planner import plan_exists as director_plan_exists

st.set_page_config(page_title="プロジェクト管理", page_icon="📁", layout="wide")
st.title("📁 プロジェクト管理")
st.caption("プロジェクト全体の統計・シリーズ管理・一括操作・プロジェクト設定 | v3.1")

_settings = load_settings()

# ── Scan all episodes ──────────────────────────────────────────────────────────

_project_dir = PROJECT_ROOT / "project"

@st.cache_data(ttl=30)
def _scan_all_episodes() -> list[dict]:
    """Light scan of all episodes — cached for 30 s."""
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
        sections   = ep_data.get("sections", [])
        total_dur  = ep_data.get("total_duration_seconds") or sum(
            s.get("duration_seconds", 0) for s in sections
        )
        # File counts
        img_dir   = d / "assets" / "images"
        vid_dir   = d / "videos"
        voi_dir   = d / "voices"
        IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
        CLIP_EXT  = {".mp4", ".mov", ".webm", ".avi", ".mkv"}
        AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".aac"}
        img_count  = sum(1 for f in img_dir.iterdir() if f.suffix.lower() in IMAGE_EXT) if img_dir.exists() else 0
        vid_count  = sum(1 for f in vid_dir.iterdir() if f.suffix.lower() in CLIP_EXT)  if vid_dir.exists() else 0
        voi_count  = sum(1 for f in voi_dir.iterdir() if f.suffix.lower() in AUDIO_EXT) if voi_dir.exists() else 0
        # Total folder size (MB)
        total_bytes = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        # Status flags
        VIDEO_EXT = {".mp4", ".mov", ".webm", ".avi"}
        has_final = any(f.suffix.lower() in VIDEO_EXT for f in d.iterdir() if f.is_file())
        if not has_final:
            out = PROJECT_ROOT / "output"
            has_final = out.exists() and any(
                f.suffix.lower() in VIDEO_EXT and d.name.lower() in f.name.lower()
                for f in out.iterdir() if f.is_file()
            )
        has_img_prompts = bool(list(d.glob("*_image_prompts.txt")))
        if has_final:
            status = "完成"
        elif has_img_prompts:
            status = "制作中"
        elif sections:
            status = "制作中"
        else:
            status = "未着手"
        results.append({
            "ep_id":         d.name,
            "title":         ep_data.get("title", ""),
            "scene_count":   len(sections),
            "total_dur":     total_dur,
            "status":        status,
            "img_count":     img_count,
            "vid_count":     vid_count,
            "voi_count":     voi_count,
            "has_director":  director_plan_exists(d),
            "has_export":    (d / "export" / "production_report.json").exists(),
            "total_mb":      total_bytes / (1024 * 1024),
            "ep_dir":        d,
        })
    return results


episodes     = _scan_all_episodes()
proj_info    = get_project_info()
series_list  = list_series()

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_overview, tab_series, tab_batch, tab_settings = st.tabs([
    "📊 プロジェクト概要",
    "📺 シリーズ管理",
    "⚡ 一括操作",
    "⚙️ プロジェクト設定",
])


# ════════════════════════════════════════════════════════════════
# TAB 1 — Project Overview / Stats
# ════════════════════════════════════════════════════════════════

with tab_overview:
    # ── Top metrics ────────────────────────────────────────────────────────────

    total_eps    = len(episodes)
    done_eps     = sum(1 for e in episodes if e["status"] == "完成")
    wip_eps      = sum(1 for e in episodes if e["status"] == "制作中")
    total_images = sum(e["img_count"]   for e in episodes)
    total_videos = sum(e["vid_count"]   for e in episodes)
    total_voices = sum(e["voi_count"]   for e in episodes)
    with_dir     = sum(1 for e in episodes if e["has_director"])
    with_export  = sum(1 for e in episodes if e["has_export"])
    total_gb     = sum(e["total_mb"] for e in episodes) / 1024

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("📁 エピソード",   total_eps)
    m2.metric("✅ 完成",         done_eps)
    m3.metric("🔄 制作中",       wip_eps)
    m4.metric("🎭 Director計画", with_dir)
    m5.metric("📦 エクスポート", with_export)
    m6.metric("💾 合計サイズ",   f"{total_gb:.2f} GB")

    st.divider()

    # ── Asset stats ────────────────────────────────────────────────────────────

    st.subheader("🗂️ 素材統計")

    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        st.metric("🖼️ 画像ファイル",  total_images)
        st.caption("全エピソード合計")
    with ac2:
        st.metric("🎬 動画クリップ",   total_videos)
        st.caption("全エピソード合計")
    with ac3:
        st.metric("🎙️ 音声ファイル",   total_voices)
        st.caption("全エピソード合計")

    st.divider()

    # ── Progress overview ──────────────────────────────────────────────────────

    st.subheader("📈 制作進捗サマリー")

    if episodes:
        dir_pct    = int(with_dir    / total_eps * 100) if total_eps else 0
        export_pct = int(with_export / total_eps * 100) if total_eps else 0
        done_pct   = int(done_eps    / total_eps * 100) if total_eps else 0

        pc1, pc2, pc3 = st.columns(3)
        with pc1:
            st.metric("演出計画カバー率", f"{dir_pct}%")
            st.progress(dir_pct / 100)
        with pc2:
            st.metric("エクスポート完了率", f"{export_pct}%")
            st.progress(export_pct / 100)
        with pc3:
            st.metric("完成率", f"{done_pct}%")
            st.progress(done_pct / 100)

    st.divider()

    # ── Episode table ──────────────────────────────────────────────────────────

    st.subheader("📋 エピソード一覧")

    if not episodes:
        st.info("エピソードがありません。⚡ 一発生成 でエピソードを作成してください。")
    else:
        # Simple table view
        for ep in episodes:
            mins, secs = divmod(ep["total_dur"], 60)
            dur_str = f"{mins}分{secs}秒" if mins else f"{secs}秒"
            badges  = []
            if ep["has_export"]:
                badges.append("📦")
            if ep["has_director"]:
                badges.append("🎭")
            badge_str = " ".join(badges)

            rc1, rc2, rc3, rc4, rc5, rc6 = st.columns([2, 4, 2, 2, 2, 1])
            rc1.caption(f"`{ep['ep_id']}`")
            rc2.caption(ep["title"][:40] or "（タイトル未設定）")
            rc3.caption(ep["status"])
            rc4.caption(f"🖼️{ep['img_count']} 🎬{ep['vid_count']} 🎙️{ep['voi_count']}")
            rc5.caption(f"{ep['total_mb']:.1f} MB | {dur_str}")
            rc6.caption(badge_str)

        if st.button("🔄 キャッシュを更新", key="overview_refresh"):
            st.cache_data.clear()
            st.rerun()

    # ── Series overview ────────────────────────────────────────────────────────

    if series_list:
        st.divider()
        st.subheader("📺 シリーズ概要")
        for s in series_list:
            n_eps = len(s["episode_ids"])
            st.caption(f"**{s['name']}** — {n_eps} エピソード | {s.get('description','')[:60]}")


# ════════════════════════════════════════════════════════════════
# TAB 2 — Series Management
# ════════════════════════════════════════════════════════════════

with tab_series:

    left_s, right_s = st.columns([2, 3])

    with left_s:
        st.subheader("📺 シリーズ一覧")

        if not series_list:
            st.info("シリーズがありません。右の「新規作成」で追加してください。")
        else:
            for s in series_list:
                n_eps   = len(s["episode_ids"])
                is_sel  = st.session_state.get("pm_sel_series_id") == s["id"]
                if st.button(
                    f"**{s['name']}**  ({n_eps} EP)",
                    key=f"pm_sb_{s['id']}",
                    use_container_width=True,
                    type="primary" if is_sel else "secondary",
                ):
                    st.session_state["pm_sel_series_id"] = s["id"]
                    st.rerun()

        st.divider()
        st.subheader("➕ 新規シリーズ")
        new_name = st.text_input("シリーズ名", key="pm_new_series_name", placeholder="例: Python入門シリーズ")
        new_desc = st.text_input("説明（任意）", key="pm_new_series_desc", placeholder="例: Pythonの基礎を解説するシリーズ")
        if st.button("✚ シリーズを作成", use_container_width=True, key="pm_create_series"):
            if not new_name.strip():
                st.error("シリーズ名を入力してください")
            else:
                new_s = add_series(new_name, new_desc)
                st.session_state["pm_sel_series_id"] = new_s["id"]
                st.success(f"「{new_s['name']}」を作成しました")
                st.rerun()

    with right_s:
        sel_sid = st.session_state.get("pm_sel_series_id")
        if not sel_sid:
            st.info("左のリストからシリーズを選択するか、新規作成してください。")
        else:
            # Re-load fresh
            sel_series = next((s for s in list_series() if s["id"] == sel_sid), None)
            if not sel_series:
                st.session_state.pop("pm_sel_series_id", None)
                st.rerun()
            else:
                st.subheader(f"📺 {sel_series['name']}")

                # Edit name/description
                with st.expander("✏️ 編集"):
                    edit_name = st.text_input(
                        "シリーズ名",
                        value=sel_series["name"],
                        key=f"pm_edit_name_{sel_sid}",
                    )
                    edit_desc = st.text_input(
                        "説明",
                        value=sel_series.get("description", ""),
                        key=f"pm_edit_desc_{sel_sid}",
                    )
                    if st.button("💾 保存", key=f"pm_edit_save_{sel_sid}", use_container_width=True):
                        update_series(sel_sid, {"name": edit_name, "description": edit_desc})
                        st.success("更新しました")
                        st.rerun()

                # Episodes in this series
                ep_ids_in = sel_series.get("episode_ids", [])
                ep_all_ids = [e["ep_id"] for e in episodes]

                st.markdown(f"**エピソード順序** ({len(ep_ids_in)} 件)")

                # Show episodes already in series with remove button
                for i, eid in enumerate(ep_ids_in):
                    ep_info = next((e for e in episodes if e["ep_id"] == eid), None)
                    title   = ep_info["title"][:30] if ep_info else ""
                    rc1, rc2, rc3, rc4 = st.columns([1, 4, 1, 1])
                    rc1.caption(f"#{i+1}")
                    rc2.caption(f"`{eid}` {title}")
                    # Move up / remove
                    if i > 0 and rc3.button("↑", key=f"pm_up_{sel_sid}_{eid}"):
                        new_order = list(ep_ids_in)
                        new_order[i - 1], new_order[i] = new_order[i], new_order[i - 1]
                        set_episode_order_in_series(sel_sid, new_order)
                        st.rerun()
                    if rc4.button("✕", key=f"pm_rm_{sel_sid}_{eid}", help="シリーズから削除"):
                        remove_episode_from_series(sel_sid, eid)
                        st.rerun()

                # Add episodes not yet in this series
                ep_ids_not_in = [eid for eid in ep_all_ids if eid not in ep_ids_in]
                if ep_ids_not_in:
                    st.divider()
                    st.caption("**エピソードを追加**")
                    add_cols = st.columns([3, 1])
                    add_ep = add_cols[0].selectbox(
                        "エピソード",
                        ep_ids_not_in,
                        key=f"pm_add_ep_{sel_sid}",
                        label_visibility="collapsed",
                    )
                    if add_cols[1].button("追加", key=f"pm_add_ep_btn_{sel_sid}", use_container_width=True):
                        add_episode_to_series(sel_sid, add_ep)
                        st.rerun()

                st.divider()

                # Delete series
                with st.expander("⚠️ シリーズを削除"):
                    confirm_del = st.checkbox(
                        f"「{sel_series['name']}」を削除することを確認",
                        key=f"pm_del_confirm_{sel_sid}",
                    )
                    if st.button(
                        "🗑️ 削除する",
                        disabled=not confirm_del,
                        key=f"pm_del_btn_{sel_sid}",
                        use_container_width=True,
                    ):
                        delete_series(sel_sid)
                        st.session_state.pop("pm_sel_series_id", None)
                        st.success("シリーズを削除しました")
                        st.rerun()


# ════════════════════════════════════════════════════════════════
# TAB 3 — Batch Operations
# ════════════════════════════════════════════════════════════════

with tab_batch:
    st.subheader("⚡ 一括操作")

    if not episodes:
        st.info("エピソードがありません。")
    else:
        # ── Episode selection ──────────────────────────────────────────────────

        st.caption("操作するエピソードを選択してください")

        sel_all_key = "pm_batch_sel_all"
        if st.checkbox("すべて選択", key=sel_all_key):
            for e in episodes:
                st.session_state[f"pm_batch_chk_{e['ep_id']}"] = True

        selected_ep_ids: list[str] = []
        cols_per_row = 3
        ep_rows = [episodes[i:i + cols_per_row] for i in range(0, len(episodes), cols_per_row)]
        for row in ep_rows:
            row_cols = st.columns(cols_per_row)
            for col, ep in zip(row_cols, row):
                checked = col.checkbox(
                    f"`{ep['ep_id']}` {ep['title'][:20] or '未設定'}",
                    key=f"pm_batch_chk_{ep['ep_id']}",
                    value=st.session_state.get(f"pm_batch_chk_{ep['ep_id']}", False),
                )
                if checked:
                    selected_ep_ids.append(ep["ep_id"])

        st.caption(f"{len(selected_ep_ids)} / {len(episodes)} 件を選択中")
        st.divider()

        # ── Batch actions ──────────────────────────────────────────────────────

        if not selected_ep_ids:
            st.info("上のチェックボックスでエピソードを選択してください。")
        else:
            st.subheader(f"選択中: {', '.join(selected_ep_ids)}")

            action_tab1, action_tab2, action_tab3 = st.tabs([
                "📦 書き出しパッケージ",
                "🎬 制作ステージ更新",
                "📺 シリーズに追加",
            ])

            with action_tab1:
                st.caption("選択したエピソードの書き出しパッケージを一括作成します。")
                if st.button(
                    f"📦 {len(selected_ep_ids)} 件を書き出す",
                    type="primary",
                    use_container_width=True,
                    key="pm_batch_export",
                ):
                    results_ok:   list[str] = []
                    results_fail: list[str] = []
                    prog = st.progress(0)
                    for i, eid in enumerate(selected_ep_ids):
                        ep_dir   = _project_dir / eid
                        ep_data  = load_episode_data(ep_dir)
                        prod_st  = load_production_state(ep_dir)
                        try:
                            create_export_package(
                                episode_dir=ep_dir,
                                production_state=prod_st,
                                episode_data=ep_data,
                            )
                            results_ok.append(eid)
                        except Exception as exc:
                            results_fail.append(f"{eid} ({exc})")
                        prog.progress((i + 1) / len(selected_ep_ids))
                    if results_ok:
                        st.success(f"✅ 書き出し完了: {', '.join(results_ok)}")
                    if results_fail:
                        st.error(f"❌ 失敗: {', '.join(results_fail)}")
                    st.cache_data.clear()

            with action_tab2:
                st.caption("選択したエピソードの制作ステージを一括更新します。")
                bc1, bc2, bc3 = st.columns(3)
                with bc1:
                    batch_stage = st.selectbox(
                        "ステージ",
                        STAGE_ORDER,
                        key="pm_batch_stage",
                    )
                with bc2:
                    batch_status = st.selectbox(
                        "新しいステータス",
                        STATUS_OPTIONS,
                        format_func=lambda x: STATUS_LABELS.get(x, x),
                        key="pm_batch_status",
                    )
                with bc3:
                    st.write("")
                    st.write("")
                    if st.button("更新する", type="primary", use_container_width=True, key="pm_batch_stage_btn"):
                        updated: list[str] = []
                        for eid in selected_ep_ids:
                            ep_dir = _project_dir / eid
                            if ep_dir.exists():
                                mark_stage(ep_dir, batch_stage, batch_status)
                                updated.append(eid)
                        st.success(f"✅ {len(updated)} 件の「{batch_stage}」ステージを「{STATUS_LABELS.get(batch_status, batch_status)}」に更新しました")

            with action_tab3:
                if not series_list:
                    st.info("シリーズがありません。「シリーズ管理」タブで作成してください。")
                else:
                    sc1, sc2 = st.columns([3, 1])
                    with sc1:
                        target_sid = st.selectbox(
                            "追加先シリーズ",
                            [s["id"] for s in series_list],
                            format_func=lambda x: next((s["name"] for s in series_list if s["id"] == x), x),
                            key="pm_batch_series_target",
                        )
                    with sc2:
                        st.write("")
                        st.write("")
                        if st.button("追加する", type="primary", use_container_width=True, key="pm_batch_series_btn"):
                            for eid in selected_ep_ids:
                                add_episode_to_series(target_sid, eid)
                            st.success(f"✅ {len(selected_ep_ids)} 件をシリーズに追加しました")
                            st.rerun()


# ════════════════════════════════════════════════════════════════
# TAB 4 — Project Settings
# ════════════════════════════════════════════════════════════════

with tab_settings:
    st.subheader("⚙️ プロジェクト設定")

    data     = load_project_settings()
    proj     = data["project"]

    pc1, pc2 = st.columns(2)
    with pc1:
        new_name = st.text_input(
            "プロジェクト名",
            value=proj.get("name", ""),
            key="pm_proj_name",
            placeholder="例: AIチュートリアルチャンネル",
        )
        new_desc = st.text_area(
            "プロジェクト説明",
            value=proj.get("description", ""),
            height=100,
            key="pm_proj_desc",
            placeholder="チャンネルや動画シリーズの説明",
        )
        new_channel = st.text_input(
            "ターゲットチャンネル",
            value=proj.get("target_channel", ""),
            key="pm_proj_channel",
            placeholder="例: @my_youtube_channel",
        )

    with pc2:
        _genre_idx = GENRE_OPTIONS.index(proj.get("genre", GENRE_OPTIONS[0])) \
            if proj.get("genre") in GENRE_OPTIONS else 0
        new_genre = st.selectbox(
            "ジャンル",
            GENRE_OPTIONS,
            index=_genre_idx,
            key="pm_proj_genre",
        )
        _lang_idx = LANGUAGE_OPTIONS.index(proj.get("language", "ja")) \
            if proj.get("language") in LANGUAGE_OPTIONS else 0
        new_lang = st.selectbox(
            "言語",
            LANGUAGE_OPTIONS,
            index=_lang_idx,
            key="pm_proj_lang",
        )
        st.caption(f"**作成日:** {proj.get('created_at', '')[:10]}")
        st.caption(f"**更新日:** {proj.get('updated_at', '')[:10]}")

    if st.button("💾 プロジェクト設定を保存", type="primary", use_container_width=True, key="pm_save_proj"):
        update_project_info({
            "name":           new_name.strip(),
            "description":    new_desc.strip(),
            "target_channel": new_channel.strip(),
            "genre":          new_genre,
            "language":       new_lang,
        })
        st.success("プロジェクト設定を保存しました ✅")
        st.rerun()

    st.divider()

    # ── Project-level JSON preview ─────────────────────────────────────────────

    with st.expander("📄 project_settings.json"):
        from src.utils.project_manager import PROJECT_SETTINGS_PATH
        if PROJECT_SETTINGS_PATH.exists():
            raw = PROJECT_SETTINGS_PATH.read_text(encoding="utf-8")
            st.download_button(
                "⬇️ ダウンロード",
                data=raw,
                file_name="project_settings.json",
                mime="application/json",
                key="dl_proj_settings",
            )
            st.code(raw[:3000] + ("…" if len(raw) > 3000 else ""), language="json")
        else:
            st.caption("まだ保存されていません")

    st.divider()

    # ── Project health check ───────────────────────────────────────────────────

    st.subheader("🩺 プロジェクト整合性チェック")
    st.caption("scripts/check_project.py と同じチェックをブラウザで実行します。")

    if st.button("🔍 チェック実行", use_container_width=True, key="pm_health_check"):
        REQUIRED_FOLDERS = [
            "assets", "assets/images", "assets/videos", "assets/voices",
            "config", "pages", "project", "src",
            "src/core", "src/utils", "src/pipeline", "src/providers", "src/director",
        ]
        REQUIRED_FILES = [
            "app.py", "requirements.txt",
            "pages/6_Produce.py", "pages/8_Dashboard.py", "pages/12_Prompt_Builder.py",
            "pages/13_Production.py", "pages/14_Director.py",
            "src/core/ai_pipeline.py", "src/utils/character_manager.py",
            "src/utils/background_manager.py", "src/utils/prompt_builder.py",
            "src/pipeline/export_pipeline.py", "src/director/director_planner.py",
        ]
        all_ok = True
        folder_results, file_results = [], []
        for rel in REQUIRED_FOLDERS:
            ok = (PROJECT_ROOT / rel).is_dir()
            folder_results.append((rel, ok))
            if not ok:
                all_ok = False
        for rel in REQUIRED_FILES:
            ok = (PROJECT_ROOT / rel).exists()
            file_results.append((rel, ok))
            if not ok:
                all_ok = False

        hc1, hc2 = st.columns(2)
        with hc1:
            st.caption("**フォルダ**")
            for rel, ok in folder_results:
                st.caption(f"{'✅' if ok else '❌'} `{rel}`")
        with hc2:
            st.caption("**ファイル**")
            for rel, ok in file_results:
                st.caption(f"{'✅' if ok else '❌'} `{rel}`")

        if all_ok:
            st.success("✅ すべての必須フォルダ・ファイルが揃っています")
        else:
            st.error("❌ 不足しているフォルダ・ファイルがあります")
