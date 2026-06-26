import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import OPENAI_API_KEY, PROJECT_ROOT
from src.core import episode_manager as em
from src.core import ai_pipeline

st.set_page_config(page_title="一発生成", page_icon="⚡", layout="wide")
st.title("⚡ 一発生成")
st.caption("テーマを入力するだけで台本・シーン分割・画像/動画プロンプト・字幕・音声台本を全自動生成 | v2.0")

if not OPENAI_API_KEY:
    st.error("OpenAI API キーが未設定です。`.env` ファイルに `OPENAI_API_KEY` を設定してください。")
    st.stop()

# ── Input form ────────────────────────────────────────────────────────────────

with st.form("produce_form"):
    col1, col2 = st.columns([3, 2])
    with col1:
        topic = st.text_input(
            "テーマ・タイトル *",
            placeholder="例: Pythonで始める機械学習入門",
        )
        target = st.text_input(
            "ターゲット視聴者",
            placeholder="例: プログラミング初心者、20-35歳",
        )
        episode_id = st.text_input(
            "エピソードID",
            value="EP01",
            help="project/ フォルダ内に保存されるサブフォルダ名",
        )
    with col2:
        duration = st.selectbox("動画の長さ", ["1分", "2分", "3分", "5分"])
        style = st.selectbox(
            "スタイル",
            ["解説・教育", "エンタメ", "ニュース", "ドキュメンタリー", "Vlog"],
        )
        num_scenes = st.slider(
            "シーン数",
            min_value=2,
            max_value=8,
            value=4,
            help="シーンが多いほど構造的になりますが各シーンは短くなります",
        )
        overwrite = st.checkbox("同名エピソードを上書きする", value=False)

    submitted = st.form_submit_button(
        "⚡ 一発生成スタート",
        type="primary",
        use_container_width=True,
    )

# ── Run pipeline ──────────────────────────────────────────────────────────────

if submitted:
    if not topic:
        st.error("テーマを入力してください")
        st.stop()
    if not episode_id:
        st.error("エピソードIDを入力してください")
        st.stop()
    if em.load_episode(episode_id) is not None and not overwrite:
        st.warning(
            f"`{episode_id}` は既に存在します。"
            "「同名エピソードを上書きする」を有効にするか、別のIDを使用してください。"
        )
        st.stop()

    progress = st.progress(0, text="準備中...")
    try:
        progress.progress(10, text="🤖 OpenAI でスクリプト・シーン分割・プロンプトを生成中... (10〜30秒)")

        ep, written = ai_pipeline.generate_episode_ai(
            topic=topic,
            episode_id=episode_id,
            duration=duration,
            style=style,
            target=target,
            num_scenes=num_scenes,
        )

        progress.progress(100, text="✅ 全工程完了！")
        st.session_state[f"produced_ep_{episode_id}"] = ep
        st.session_state[f"produced_written_{episode_id}"] = written
        st.session_state["last_produced_id"] = episode_id

    except Exception as exc:
        progress.empty()
        st.error(f"エラーが発生しました: {exc}")
        st.exception(exc)
        st.stop()

# ── Results ───────────────────────────────────────────────────────────────────

last_id = st.session_state.get("last_produced_id")
if not last_id:
    st.stop()

ep = st.session_state.get(f"produced_ep_{last_id}")
written = st.session_state.get(f"produced_written_{last_id}", {})
if ep is None:
    st.stop()

st.divider()
st.success(
    f"**{ep['title']}** の生成が完了しました！"
    f" {len(written)} ファイルを `project/{ep['episode_id']}/` に書き出しました。"
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("シーン数", len(ep["sections"]))
c2.metric("合計尺", f"{ep['total_duration_seconds']}秒")
c3.metric("台本文字数", f"{sum(len(s['narration_text']) for s in ep['sections'])}文字")
c4.metric("エピソードID", ep["episode_id"])

st.divider()

# Scene cards
st.subheader("📋 シーン一覧")
for s in ep["sections"]:
    with st.expander(
        f"[{s['id']}] {s['title']} — {s['duration_seconds']}秒",
        expanded=(s["id"] == 1),
    ):
        left, right = st.columns([2, 1])
        with left:
            st.caption("🎙️ ナレーション")
            st.write(s["narration_text"])
        with right:
            if s.get("image_prompt"):
                st.caption("🖼️ 画像プロンプト")
                st.code(s["image_prompt"], language=None)
            if s.get("video_prompt"):
                st.caption("🎬 動画プロンプト（Runway）")
                st.code(s["video_prompt"], language=None)

st.divider()

# File downloads — read from disk (avoids widget state / key collision issues)
ep_id = ep["episode_id"]
ep_folder = PROJECT_ROOT / "project" / ep_id

dl_left, dl_right = st.columns(2)

with dl_left:
    st.subheader("🎙️ 音声台本")
    voice_path = ep_folder / f"{ep_id}_voice_script.txt"
    if voice_path.exists():
        voice_text = voice_path.read_text(encoding="utf-8")
        st.text_area("音声台本", value=voice_text, height=260, key=f"v_{ep_id}")
        st.download_button(
            f"⬇️ {ep_id}_voice_script.txt",
            data=voice_text,
            file_name=f"{ep_id}_voice_script.txt",
            mime="text/plain",
            use_container_width=True,
        )

with dl_right:
    st.subheader("🔤 字幕 SRT")
    srt_path = ep_folder / f"{ep_id}.srt"
    if srt_path.exists():
        srt_text = srt_path.read_text(encoding="utf-8")
        st.text_area("字幕 SRT", value=srt_text, height=260, key=f"s_{ep_id}")
        st.download_button(
            f"⬇️ {ep_id}.srt",
            data=srt_text,
            file_name=f"{ep_id}.srt",
            mime="text/plain",
            use_container_width=True,
        )

st.divider()
st.info(
    f"全ファイルは `project/{ep_id}/` に保存済みです。"
    " **🎞️ エピソード管理** ページで内容を確認・編集できます。"
)
