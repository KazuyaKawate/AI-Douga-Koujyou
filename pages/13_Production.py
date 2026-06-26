import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PROJECT_ROOT
from src.utils.settings_manager import load_settings
from src.pipeline.script_pipeline import (
    get_image_prompts_path,
    get_srt_path,
    get_video_prompts_path,
    get_voice_script_path,
    load_episode_data,
)
from src.pipeline.audio_pipeline import is_audio_complete
from src.pipeline.image_pipeline import is_images_complete
from src.pipeline.video_pipeline import is_videos_complete
from src.pipeline.script_pipeline import is_script_complete
from src.pipeline.export_pipeline import (
    STAGE_LABELS,
    STAGE_ORDER,
    STATUS_LABELS,
    create_export_package,
    get_completion_pct,
    is_production_ready,
    load_production_report,
    load_production_state,
    mark_stage,
    save_production_state,
    validate_episode,
    validate_export_ready,
)
from src.providers.image_provider_manual import get_instructions as img_instructions
from src.providers.video_provider_manual import get_instructions as vid_instructions
from src.providers.audio_provider_manual import get_voice_instructions

st.set_page_config(page_title="制作管理", page_icon="🎬", layout="wide")
st.title("🎬 制作管理")
st.caption("エピソードの制作進捗管理・書き出しパッケージ作成 | v3.0")

_settings = load_settings()
_gen      = _settings["generation"]
_ai       = _settings["ai"]

# ── Scan episodes ──────────────────────────────────────────────────────────────

project_dir = PROJECT_ROOT / "project"
ep_dirs: list[Path] = sorted(
    [d for d in project_dir.iterdir() if d.is_dir() and (d / "episode.json").exists()],
    key=lambda d: d.name,
) if project_dir.exists() else []

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.subheader(f"📁 エピソード ({len(ep_dirs)})")

    if not ep_dirs:
        st.caption("エピソードがありません")
    else:
        for ep_dir_s in ep_dirs:
            state_s  = load_production_state(ep_dir_s)
            pct_s    = int(get_completion_pct(state_s) * 100)
            ready_s  = is_production_ready(state_s)
            report_s = load_production_report(ep_dir_s)
            prefix   = "📦 " if report_s else ("✅ " if ready_s else "")
            if st.button(
                f"{prefix}{ep_dir_s.name}  {pct_s}%",
                key=f"sb_{ep_dir_s.name}",
                use_container_width=True,
                type="primary" if st.session_state.get("prod_ep_id") == ep_dir_s.name else "secondary",
            ):
                st.session_state["prod_ep_id"] = ep_dir_s.name
                st.rerun()

    st.divider()
    st.caption(f"🖼️ 画像: `{_gen['image_provider']}`")
    st.caption(f"🎬 動画: `{_gen['video_provider']}`")
    st.caption(f"🎙️ 音声: `{_gen['voice_provider']}`")
    st.caption(f"🤖 モデル: `{_ai['model']}`")

# ── Episode selector ───────────────────────────────────────────────────────────

if not ep_dirs:
    st.info(
        "エピソードが見つかりません。\n\n"
        "⚡ 一発生成 または 🎞️ エピソード管理 でエピソードを作成してください。"
    )
    st.stop()

ep_names    = [d.name for d in ep_dirs]
default_ep  = st.session_state.get("prod_ep_id", ep_names[0])
default_idx = ep_names.index(default_ep) if default_ep in ep_names else 0

sel_ep_name = st.selectbox(
    "📁 管理するエピソードを選択",
    ep_names,
    index=default_idx,
    key="prod_ep_sel",
)
st.session_state["prod_ep_id"] = sel_ep_name

episode_dir  = project_dir / sel_ep_name
episode_data = load_episode_data(episode_dir)
state        = load_production_state(episode_dir)
report       = load_production_report(episode_dir)

pct     = get_completion_pct(state)
pct_int = int(pct * 100)
ready   = is_production_ready(state)
done_count = sum(1 for s in state["stages"].values() if s["status"] in ("done", "skipped"))

# ── Two-column layout ──────────────────────────────────────────────────────────

left_col, right_col = st.columns([3, 2])

# ════════════════════════════════════════════════════════════════
# LEFT: Episode info + Validation + Checklist
# ════════════════════════════════════════════════════════════════

with left_col:
    # ── Episode info ───────────────────────────────────────────────────────────

    ep_title  = (episode_data or {}).get("title", "（タイトル未設定）")
    ep_dur    = (episode_data or {}).get("total_duration_seconds", 0)
    ep_scenes = len((episode_data or {}).get("sections", []))
    ep_desc   = (episode_data or {}).get("description", "")

    hc1, hc2 = st.columns([3, 1])
    with hc1:
        st.subheader(ep_title)
        mins, secs = divmod(ep_dur, 60)
        dur_str = f"{mins}分{secs}秒" if mins else f"{secs}秒"
        st.caption(f"ID: `{sel_ep_name}` | {ep_scenes} シーン | {dur_str}")
        if ep_desc:
            st.caption(ep_desc[:120] + ("…" if len(ep_desc) > 120 else ""))
    with hc2:
        if report:
            st.success("📦 書き出し済")
        elif ready:
            st.success("🎬 制作可能")
        else:
            st.info(f"⏳ {pct_int}%")

    st.divider()

    # ── File validation ────────────────────────────────────────────────────────

    st.subheader("✅ ファイル検証")

    rescan_c, autodetect_c = st.columns(2)
    with rescan_c:
        if st.button("🔄 再スキャン", use_container_width=True):
            st.rerun()
    with autodetect_c:
        if st.button("🔍 自動検出して更新", use_container_width=True):
            if is_script_complete(episode_dir):
                mark_stage(episode_dir, "script", "done")
            if is_images_complete(episode_dir):
                mark_stage(episode_dir, "images", "done")
            if is_videos_complete(episode_dir):
                mark_stage(episode_dir, "videos", "done")
            if is_audio_complete(episode_dir):
                mark_stage(episode_dir, "voice", "done")
            st.success("自動検出が完了しました ✅")
            st.rerun()

    validation  = validate_episode(episode_dir)
    script_val  = validation["script"]
    img_val     = validation["images"]
    vid_val     = validation["videos"]
    aud_val     = validation["audio"]

    vc1, vc2 = st.columns(2)
    with vc1:
        st.caption("**必須スクリプトファイル**")
        for label, info in script_val.items():
            icon = "✅" if info["exists"] else "❌"
            st.markdown(f"{icon} {label}")
            for fn in info["files"][:1]:
                st.caption(f"   `{fn}`")

    with vc2:
        st.caption("**素材ファイル**")
        st.markdown(f"{'✅' if img_val['has_images'] else '⬜'} 画像 ({img_val['image_count']} 件)")
        st.markdown(f"{'✅' if vid_val['has_clips']  else '⬜'} 動画クリップ ({vid_val['clip_count']} 件)")
        st.markdown(f"{'✅' if aud_val['has_voice']  else '⬜'} 音声 ({aud_val['voice_file_count']} 件)")

    st.divider()

    # ── Production checklist ───────────────────────────────────────────────────

    st.subheader("🎬 制作チェックリスト")
    st.progress(
        pct,
        text=f"{pct_int}% 完了  ({done_count} / {len(STAGE_ORDER)} ステージ)",
    )

    st.caption("✅ 完了 | 🔄 進行中 | ⏭ スキップ | ⏸ 未着手にリセット")

    for stage_id in STAGE_ORDER:
        stage_info  = state["stages"].get(stage_id, {"status": "pending", "completed_at": None})
        cur_status  = stage_info["status"]
        stage_label = STAGE_LABELS[stage_id]
        status_lbl  = STATUS_LABELS.get(cur_status, cur_status)

        sc1, sc2, sc3 = st.columns([4, 2, 4])

        with sc1:
            st.markdown(f"**{stage_label}**")
            st.caption(status_lbl)

        with sc2:
            if stage_info.get("completed_at"):
                st.caption(f"✔ {stage_info['completed_at'][:10]}")

        with sc3:
            b1, b2, b3, b4 = st.columns(4)
            if b1.button("✅", key=f"done_{stage_id}_{sel_ep_name}",
                         help="完了", disabled=(cur_status == "done")):
                mark_stage(episode_dir, stage_id, "done")
                st.rerun()
            if b2.button("🔄", key=f"wip_{stage_id}_{sel_ep_name}",
                         help="進行中", disabled=(cur_status == "in_progress")):
                mark_stage(episode_dir, stage_id, "in_progress")
                st.rerun()
            if b3.button("⏭", key=f"skip_{stage_id}_{sel_ep_name}",
                         help="スキップ", disabled=(cur_status == "skipped")):
                mark_stage(episode_dir, stage_id, "skipped")
                st.rerun()
            if b4.button("⏸", key=f"reset_{stage_id}_{sel_ep_name}",
                         help="未着手にリセット", disabled=(cur_status == "pending")):
                mark_stage(episode_dir, stage_id, "pending")
                st.rerun()

        # Auto-detected hint
        auto_done = {
            "script": is_script_complete(episode_dir),
            "images": is_images_complete(episode_dir),
            "videos": is_videos_complete(episode_dir),
            "voice":  is_audio_complete(episode_dir),
        }
        if stage_id in auto_done and auto_done[stage_id] and cur_status == "pending":
            st.caption("   ↑ ファイルを検出 — 「✅」で完了マークを付けてください")

        st.divider()


# ════════════════════════════════════════════════════════════════
# RIGHT: Provider guide + Notes + Export
# ════════════════════════════════════════════════════════════════

with right_col:
    # ── Provider guide ─────────────────────────────────────────────────────────

    st.subheader("🛠️ 制作ガイド")

    img_path = get_image_prompts_path(episode_dir)
    vid_path = get_video_prompts_path(episode_dir)
    voi_path = get_voice_script_path(episode_dir)

    with st.expander("🖼️ 画像プロンプト"):
        if img_path:
            raw = img_path.read_text(encoding="utf-8", errors="replace")
            st.caption(img_instructions("（各シーンのプロンプトは以下）"))
            preview = raw[:2000] + ("…(省略)" if len(raw) > 2000 else "")
            st.code(preview, language=None)
            st.download_button(
                "⬇️ ダウンロード",
                data=raw,
                file_name=img_path.name,
                mime="text/plain",
                key=f"dl_img_{sel_ep_name}",
                use_container_width=True,
            )
        else:
            st.caption("画像プロンプトファイルが見つかりません")

    with st.expander("🎬 動画プロンプト"):
        if vid_path:
            raw = vid_path.read_text(encoding="utf-8", errors="replace")
            st.caption(vid_instructions("（各シーンのプロンプトは以下）"))
            preview = raw[:2000] + ("…(省略)" if len(raw) > 2000 else "")
            st.code(preview, language=None)
            st.download_button(
                "⬇️ ダウンロード",
                data=raw,
                file_name=vid_path.name,
                mime="text/plain",
                key=f"dl_vid_{sel_ep_name}",
                use_container_width=True,
            )
        else:
            st.caption("動画プロンプトファイルが見つかりません")

    with st.expander("🎙️ 音声台本"):
        if voi_path:
            raw = voi_path.read_text(encoding="utf-8", errors="replace")
            st.caption(get_voice_instructions("（以下の台本を使用）"))
            preview = raw[:2000] + ("…(省略)" if len(raw) > 2000 else "")
            st.code(preview, language=None)
            st.download_button(
                "⬇️ ダウンロード",
                data=raw,
                file_name=voi_path.name,
                mime="text/plain",
                key=f"dl_voi_{sel_ep_name}",
                use_container_width=True,
            )
        else:
            st.caption("音声台本ファイルが見つかりません")

    srt_path = get_srt_path(episode_dir)
    with st.expander("🔤 字幕 (SRT)"):
        if srt_path:
            raw = srt_path.read_text(encoding="utf-8", errors="replace")
            st.code(raw[:2000] + ("…(省略)" if len(raw) > 2000 else ""), language=None)
            st.download_button(
                "⬇️ ダウンロード",
                data=raw,
                file_name=srt_path.name,
                mime="text/plain",
                key=f"dl_srt_{sel_ep_name}",
                use_container_width=True,
            )
        else:
            st.caption("SRTファイルが見つかりません")

    st.divider()

    # ── Production notes ───────────────────────────────────────────────────────

    st.subheader("📌 制作ノート")
    new_notes = st.text_area(
        "ノート",
        value=state.get("notes", ""),
        height=100,
        key=f"notes_{sel_ep_name}",
        label_visibility="collapsed",
        placeholder="制作メモ・課題・次のステップ…",
    )
    if st.button("💾 ノートを保存", use_container_width=True, key="save_notes"):
        state["notes"] = new_notes
        save_production_state(episode_dir, state)
        st.success("保存しました ✅")

    st.divider()

    # ── Export package ─────────────────────────────────────────────────────────

    st.subheader("📤 書き出しパッケージ")

    export_check = validate_export_ready(episode_dir)

    if export_check["missing"]:
        st.warning(f"不足ファイル: {', '.join(export_check['missing'])}")
    else:
        st.caption("書き出しに必要なファイルが揃っています ✅")

    if report:
        rpt_date   = report.get("export_date", "")[:10]
        rpt_status = report.get("status", "")
        rpt_pct    = report.get("completion_pct", 0)
        st.info(
            f"前回書き出し: {rpt_date}  |  "
            f"完了率: {rpt_pct}%  |  "
            f"ステータス: {rpt_status}"
        )

    if st.button(
        "📦 パッケージを書き出す",
        type="primary",
        use_container_width=True,
        disabled=bool(export_check["missing"]),
        key="export_btn",
    ):
        with st.spinner("書き出し中..."):
            result = create_export_package(
                episode_dir=episode_dir,
                production_state=state,
                episode_data=episode_data,
            )
        n = len(result["copied"])
        export_rel = result["export_dir"].relative_to(PROJECT_ROOT)
        st.success(f"✅ {n} ファイルを `{export_rel}` に書き出しました")
        if result["skipped"]:
            st.caption(f"スキップ（未発見）: {', '.join(result['skipped'])}")
        st.rerun()

    # ── Export folder contents ─────────────────────────────────────────────────

    export_dir = episode_dir / "export"
    if export_dir.exists():
        with st.expander("📁 書き出しフォルダ"):
            st.code(str(export_dir), language=None)
            try:
                files_in_export = sorted(
                    (f for f in export_dir.iterdir() if f.is_file()),
                    key=lambda f: f.name,
                )
                for f in files_in_export:
                    kb = f.stat().st_size / 1024
                    icon = "📋" if f.suffix == ".json" else ("📄" if f.suffix == ".txt" else "📁")
                    st.caption(f"{icon} `{f.name}` ({kb:.1f} KB)")
            except Exception:
                st.caption("フォルダを読み込めませんでした")

    # ── Production report preview ──────────────────────────────────────────────

    if report:
        with st.expander("📊 制作レポート"):
            st.json(report)
