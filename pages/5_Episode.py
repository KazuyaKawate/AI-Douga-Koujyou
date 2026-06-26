import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import episode_manager as em
from src.utils.config import PROJECT_ROOT
from src.utils.file_manager import list_files

st.set_page_config(page_title="エピソード管理", page_icon="🎞️", layout="wide")
st.title("🎞️ エピソード管理")
st.caption("Episode 制作フロー — v1.1 | 台本 → プロンプト → 音声台本 → 字幕 → エクスポート")

STATUS_LABEL = {"pending": "⏸ 未着手", "draft": "✏️ 作業中", "done": "✅ 完了"}
STEP_NAMES = {
    "script": "台本",
    "image_prompts": "画像",
    "video_prompts": "動画",
    "voice_script": "音声",
    "subtitles": "字幕",
}

# ── Sidebar: load / create ──────────────────────────────────────────────────────
with st.sidebar:
    st.header("エピソード")
    episode_list = em.get_episode_list()

    if episode_list:
        sel = st.selectbox("読み込む", episode_list)
        if st.button("📂 読み込む", use_container_width=True):
            st.session_state.episode = em.load_episode(sel)
            st.session_state.pop("voice_text_area", None)
            st.session_state.pop("srt_text_area", None)
            st.success(f"{sel} を読み込みました")
    else:
        st.info("まだエピソードがありません")

    st.divider()
    st.subheader("新規作成")
    new_id = st.text_input("エピソードID", value="EP01", key="new_ep_id")
    new_title = st.text_input("タイトル", key="new_ep_title")
    new_desc = st.text_area("概要", key="new_ep_desc", height=80)
    new_audience = st.text_input("対象視聴者", key="new_ep_audience")

    if st.button("✨ 新規作成", type="primary", use_container_width=True):
        if not new_id:
            st.error("IDを入力してください")
        elif em.load_episode(new_id) is not None:
            st.error(f"{new_id} は既に存在します")
        else:
            ep = em.create_new_episode(new_id, new_title, new_desc, new_audience)
            em.save_episode(ep)
            st.session_state.episode = ep
            st.session_state.pop("voice_text_area", None)
            st.session_state.pop("srt_text_area", None)
            st.success(f"{new_id} を作成しました")
            st.rerun()

# ── Guard ───────────────────────────────────────────────────────────────────────
if "episode" not in st.session_state or st.session_state.episode is None:
    st.info("👈 サイドバーでエピソードを読み込むか、新規作成してください")
    st.stop()

ep = st.session_state.episode

# ── Status bar ──────────────────────────────────────────────────────────────────
em.recalculate_total_duration(ep)
st.caption(
    f"**{ep['episode_id']}** — {ep['title'] or '（タイトル未設定）'} "
    f"| 合計 {ep['total_duration_seconds']}秒 "
    f"| {len(ep['sections'])} セクション"
)
status_cols = st.columns(5)
for col, (key, label) in zip(status_cols, STEP_NAMES.items()):
    col.metric(label, STATUS_LABEL[ep["steps"].get(key, "pending")])

st.divider()

# ── Tabs ────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "⚙️ 設定", "📝 台本", "🖼️ 画像プロンプト",
    "🎬 動画プロンプト", "🎙️ 音声・字幕", "📦 エクスポート",
])

# ════════════════════════════════════════════════════════════════
# TAB 1 — 設定
# ════════════════════════════════════════════════════════════════
with tab1:
    with st.form("episode_meta_form"):
        c1, c2 = st.columns(2)
        with c1:
            f_id = st.text_input("エピソードID", value=ep["episode_id"])
            f_title = st.text_input("タイトル", value=ep["title"])
            f_audience = st.text_input("対象視聴者", value=ep.get("target_audience", ""))
        with c2:
            f_desc = st.text_area("概要", value=ep.get("description", ""), height=130)
        if st.form_submit_button("💾 保存", type="primary"):
            ep["episode_id"] = f_id
            ep["title"] = f_title
            ep["description"] = f_desc
            ep["target_audience"] = f_audience
            em.save_episode(ep)
            st.session_state.episode = ep
            st.success("保存しました")

    st.divider()

    with st.expander("ステータスを手動変更"):
        step_sel = st.selectbox("ステップ", list(STEP_NAMES.keys()), format_func=lambda x: STEP_NAMES[x])
        status_sel = st.selectbox("ステータス", ["pending", "draft", "done"], format_func=lambda x: STATUS_LABEL[x])
        if st.button("ステータスを更新"):
            em.update_step_status(ep, step_sel, status_sel)
            em.save_episode(ep)
            st.session_state.episode = ep
            st.success("更新しました")

    st.divider()
    st.subheader("episode.json プレビュー")
    st.json(ep)

# ════════════════════════════════════════════════════════════════
# TAB 2 — 台本
# ════════════════════════════════════════════════════════════════
with tab2:
    em.recalculate_total_duration(ep)
    st.metric("合計尺", f"{ep['total_duration_seconds']}秒")

    with st.expander("＋ セクションを追加", expanded=not ep["sections"]):
        with st.form("add_section_form"):
            s_title = st.text_input("タイトル *")
            s_label = st.text_input("ラベル（任意）", placeholder="例: intro / main_1 / outro")
            s_narr = st.text_area("ナレーション", height=100)
            s_dur = st.number_input("長さ（秒）", min_value=1, max_value=600, value=30, step=5)
            if st.form_submit_button("追加"):
                if s_title:
                    em.add_section(ep, s_title, s_narr, s_dur, s_label)
                    em.save_episode(ep)
                    st.session_state.episode = ep
                    st.rerun()
                else:
                    st.error("タイトルを入力してください")

    if not ep["sections"]:
        st.info("上の「＋ セクションを追加」からセクションを作成してください")

    for s in ep["sections"]:
        with st.expander(f"[{s['id']}] {s['title'] or '(無題)'} — {s['duration_seconds']}秒"):
            with st.form(f"sec_edit_{s['id']}"):
                e_title = st.text_input("タイトル", value=s["title"], key=f"et_{s['id']}")
                e_label = st.text_input("ラベル", value=s["label"], key=f"el_{s['id']}")
                e_narr = st.text_area("ナレーション", value=s["narration_text"], height=150, key=f"en_{s['id']}")
                e_notes = st.text_input("メモ", value=s.get("notes", ""), key=f"eno_{s['id']}")
                e_dur = st.number_input("長さ（秒）", min_value=1, max_value=600, value=s["duration_seconds"], step=5, key=f"ed_{s['id']}")
                c1, c2 = st.columns(2)
                saved = c1.form_submit_button("💾 保存", use_container_width=True)
                deleted = c2.form_submit_button("🗑️ 削除", use_container_width=True)

            if saved:
                em.update_section(ep, s["id"], title=e_title, label=e_label,
                                  narration_text=e_narr, notes=e_notes, duration_seconds=e_dur)
                em.update_step_status(ep, "script", "draft")
                em.save_episode(ep)
                st.session_state.episode = ep
                st.success("保存しました")
                st.rerun()

            if deleted:
                em.remove_section(ep, s["id"])
                em.save_episode(ep)
                st.session_state.episode = ep
                st.rerun()

    if ep["sections"]:
        st.divider()
        if st.button("📝 台本ステップを完了にする", type="primary"):
            em.update_step_status(ep, "script", "done")
            em.save_episode(ep)
            st.session_state.episode = ep
            st.success("台本ステップを完了にしました ✅")

# ════════════════════════════════════════════════════════════════
# TAB 3 — 画像プロンプト
# ════════════════════════════════════════════════════════════════
with tab3:
    if not ep["sections"]:
        st.warning("先に「📝 台本」タブでセクションを作成してください")
    else:
        style_img = st.text_input(
            "スタイルサフィックス",
            value="cinematic photography, 8K resolution, --ar 16:9",
            key="img_style",
        )
        c1, c2 = st.columns(2)
        if c1.button("⚡ 全セクション一括生成", type="primary", key="img_gen"):
            em.generate_image_prompts(ep, style_img)
            em.save_episode(ep)
            st.session_state.episode = ep
            st.success("画像プロンプトを生成しました")
        if c2.button("♻️ 全て上書き生成", key="img_force"):
            em.generate_image_prompts(ep, style_img, force=True)
            em.save_episode(ep)
            st.session_state.episode = ep
            st.success("全プロンプトを上書き生成しました")

        st.divider()

        for s in ep["sections"]:
            with st.expander(f"[{s['id']}] {s['title']}"):
                new_prompt = st.text_area(
                    "画像プロンプト",
                    value=s.get("image_prompt", ""),
                    height=100,
                    key=f"imgp_{s['id']}",
                )
                if st.button("💾 保存", key=f"imgp_save_{s['id']}"):
                    em.update_section(ep, s["id"], image_prompt=new_prompt)
                    em.update_step_status(ep, "image_prompts", "draft")
                    em.save_episode(ep)
                    st.session_state.episode = ep
                    st.success("保存しました")

        st.divider()
        with st.expander("📋 全プロンプトをまとめてコピー"):
            all_img = "\n\n".join(
                f"[{s['id']}] {s['title']}\n{s.get('image_prompt') or '（未設定）'}"
                for s in ep["sections"]
            )
            st.text_area("全プロンプト", value=all_img, height=300, key="img_all")

        if st.button("🖼️ 画像プロンプトステップを完了にする"):
            em.update_step_status(ep, "image_prompts", "done")
            em.save_episode(ep)
            st.session_state.episode = ep
            st.success("完了にしました ✅")

# ════════════════════════════════════════════════════════════════
# TAB 4 — 動画プロンプト
# ════════════════════════════════════════════════════════════════
with tab4:
    if not ep["sections"]:
        st.warning("先に「📝 台本」タブでセクションを作成してください")
    else:
        style_vid = st.text_input(
            "スタイルサフィックス",
            value="cinematic motion, smooth camera movement, Runway Gen-3 Alpha",
            key="vid_style",
        )
        c1, c2 = st.columns(2)
        if c1.button("⚡ 全セクション一括生成", type="primary", key="vid_gen"):
            em.generate_video_prompts(ep, style_vid)
            em.save_episode(ep)
            st.session_state.episode = ep
            st.success("動画プロンプトを生成しました")
        if c2.button("♻️ 全て上書き生成", key="vid_force"):
            em.generate_video_prompts(ep, style_vid, force=True)
            em.save_episode(ep)
            st.session_state.episode = ep
            st.success("全プロンプトを上書き生成しました")

        st.divider()

        for s in ep["sections"]:
            with st.expander(f"[{s['id']}] {s['title']} — {s['duration_seconds']}秒"):
                new_vprompt = st.text_area(
                    "動画プロンプト（Runway）",
                    value=s.get("video_prompt", ""),
                    height=100,
                    key=f"vidp_{s['id']}",
                )
                if st.button("💾 保存", key=f"vidp_save_{s['id']}"):
                    em.update_section(ep, s["id"], video_prompt=new_vprompt)
                    em.update_step_status(ep, "video_prompts", "draft")
                    em.save_episode(ep)
                    st.session_state.episode = ep
                    st.success("保存しました")

        st.divider()
        with st.expander("📋 全プロンプトをまとめてコピー（Runway用）"):
            all_vid = "\n\n".join(
                f"[{s['id']}] {s['title']} ({s['duration_seconds']}秒)\n{s.get('video_prompt') or '（未設定）'}"
                for s in ep["sections"]
            )
            st.text_area("全動画プロンプト", value=all_vid, height=300, key="vid_all")

        if st.button("🎬 動画プロンプトステップを完了にする"):
            em.update_step_status(ep, "video_prompts", "done")
            em.save_episode(ep)
            st.session_state.episode = ep
            st.success("完了にしました ✅")

# ════════════════════════════════════════════════════════════════
# TAB 5 — 音声台本 & 字幕
# ════════════════════════════════════════════════════════════════
with tab5:
    c_voice, c_srt = st.columns(2)

    with c_voice:
        st.subheader("🎙️ 音声台本")
        st.caption("Nano Banana などの TTS に貼り付けるテキスト")

        if st.button("音声台本を生成", type="primary", key="gen_voice"):
            st.session_state["voice_text_area"] = em.build_voice_script(ep)
            em.save_episode(ep)
            st.session_state.episode = ep

        voice_text = st.text_area(
            "音声台本（編集可）",
            height=420,
            key="voice_text_area",
        )
        if voice_text:
            st.download_button(
                "⬇️ .txt をダウンロード",
                data=voice_text,
                file_name=f"{ep['episode_id']}_voice_script.txt",
                mime="text/plain",
                use_container_width=True,
            )
            if st.button("音声ステップを完了にする", key="voice_done"):
                em.update_step_status(ep, "voice_script", "done")
                em.save_episode(ep)
                st.session_state.episode = ep
                st.success("完了にしました ✅")

    with c_srt:
        st.subheader("🔤 字幕 SRT")
        st.caption("タイミングは duration_seconds から推定（音声なし）")

        if st.button("字幕を生成", type="primary", key="gen_srt"):
            st.session_state["srt_text_area"] = em.build_srt(ep)
            em.save_episode(ep)
            st.session_state.episode = ep

        srt_text = st.text_area(
            "SRT プレビュー（編集可）",
            height=420,
            key="srt_text_area",
        )
        if srt_text:
            st.download_button(
                "⬇️ .srt をダウンロード",
                data=srt_text,
                file_name=f"{ep['episode_id']}.srt",
                mime="text/plain",
                use_container_width=True,
            )
            if st.button("字幕ステップを完了にする", key="srt_done"):
                em.update_step_status(ep, "subtitles", "done")
                em.save_episode(ep)
                st.session_state.episode = ep
                st.success("完了にしました ✅")

# ════════════════════════════════════════════════════════════════
# TAB 6 — エクスポート
# ════════════════════════════════════════════════════════════════
with tab6:
    ep_id = ep["episode_id"]
    st.subheader(f"📦 project/{ep_id}/ にエクスポート")

    checklist = [
        {
            "ファイル": "episode.json",
            "ステータス": STATUS_LABEL["done"],
            "出力": "✅ 常に出力",
        }
    ]
    for filename, step_key in [
        (f"{ep_id}_voice_script.txt", "voice_script"),
        (f"{ep_id}_image_prompts.txt", "image_prompts"),
        (f"{ep_id}_video_prompts.txt", "video_prompts"),
        (f"{ep_id}.srt", "subtitles"),
    ]:
        st_val = ep["steps"].get(step_key, "pending")
        checklist.append({
            "ファイル": filename,
            "ステータス": STATUS_LABEL[st_val],
            "出力": "✅ 出力" if st_val != "pending" else "⏸ スキップ（pending）",
        })

    st.dataframe(pd.DataFrame(checklist), use_container_width=True, hide_index=True)
    st.divider()

    if st.button(f"📦 project/{ep_id}/ にエクスポート", type="primary", use_container_width=True):
        written = em.export_episode(ep)
        st.session_state.episode = ep
        st.success(f"{len(written)} ファイルをエクスポートしました 🎉")
        for key, path in written.items():
            st.code(str(path).replace(str(PROJECT_ROOT) + "\\", ""))

    st.divider()
    st.subheader("エクスポート済みファイル")
    ep_folder = PROJECT_ROOT / "project" / ep_id
    if ep_folder.exists():
        files = sorted(
            [f for f in ep_folder.iterdir() if f.is_file()],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        if files:
            rows = [{"ファイル名": f.name, "サイズ": f"{f.stat().st_size/1024:.1f} KB"} for f in files]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("まだエクスポートされたファイルがありません")
    else:
        st.info("エピソードフォルダが存在しません")
