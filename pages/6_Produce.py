import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import OPENAI_API_KEY, PROJECT_ROOT
from src.utils.settings_manager import load_settings
from src.utils.character_manager import get_character, load_characters
from src.core import episode_manager as em
from src.core import ai_pipeline

st.set_page_config(page_title="一発生成", page_icon="⚡", layout="wide")
st.title("⚡ 一発生成")
st.caption("テーマを入力するだけで台本・シーン分割・画像/動画プロンプト・字幕・音声台本を全自動生成 | v2.6")

settings = load_settings()
_ai  = settings["ai"]
_gen = settings["generation"]
_p   = settings["project"]

# ── Dev mode banner ───────────────────────────────────────────────────────────

if _ai["dev_mode"]:
    st.warning(
        f"**開発モード:** 外部生成API（画像・動画・音声）は無効です。"
        f" プロンプトを手動でコピーして各ツールで生成してください。"
        f" （画像: {_gen['image_provider']} / 動画: {_gen['video_provider']}"
        f" / 音声: {_gen['voice_provider']}）",
        icon="⚠️",
    )

with st.sidebar:
    # ── Character selection ────────────────────────────────────────────────────
    st.subheader("🧑 キャラクター")
    _char_data = load_characters()
    _all_chars = _char_data["characters"]
    _default_char_id = _char_data.get("default_character_id")

    if _all_chars:
        _char_id_opts = [None] + [c["id"] for c in _all_chars]
        _char_name_map = {None: "（なし）"}
        _char_name_map.update({c["id"]: c["basic"]["display_name"] for c in _all_chars})
        _def_idx = _char_id_opts.index(_default_char_id) if _default_char_id in _char_id_opts else 0

        _sel_char_id = st.selectbox(
            "使用するキャラクター",
            _char_id_opts,
            format_func=lambda x: _char_name_map.get(x, "不明"),
            index=_def_idx,
            key="produce_char_id",
            label_visibility="collapsed",
        )
        _sel_char = get_character(_sel_char_id) if _sel_char_id else None
        if _sel_char:
            b = _sel_char["basic"]
            p = _sel_char["personality"]
            st.caption(f"役割: {b.get('role','-')}")
            st.caption(f"話し方: {p.get('speaking_style','-')}")
            st.caption(f"一人称: {p.get('first_person','-')}")
    else:
        st.caption("キャラクターがありません")
        st.caption("🧑 キャラクター管理 で追加してください")
        _sel_char = None

    st.divider()
    st.caption(
        f"⚙️ `{_ai['model']}` | "
        f"{'節約' if _ai['cost_saving'] else '標準'}モード | "
        f"{'🔧 開発' if _ai['dev_mode'] else '🚀 本番'}"
    )

if not OPENAI_API_KEY:
    st.error("OpenAI API キーが未設定です。`.env` ファイルに `OPENAI_API_KEY` を設定してください。")
    st.stop()

# ── Input form ────────────────────────────────────────────────────────────────

_dur_opts = ["1分", "2分", "3分", "5分"]
_dur_default = _dur_opts.index(_p["default_episode_length"]) if _p["default_episode_length"] in _dur_opts else 2

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
        duration = st.selectbox("動画の長さ", _dur_opts, index=_dur_default)
        style = st.selectbox(
            "スタイル",
            ["解説・教育", "エンタメ", "ニュース", "ドキュメンタリー", "Vlog"],
        )
        num_scenes = st.slider(
            "シーン数",
            min_value=2,
            max_value=8,
            value=int(_p["default_scene_count"]),
            help="コスト節約モードでは 2〜3 を推奨",
        )
        cost_saving = st.checkbox(
            "コスト節約モード",
            value=bool(_ai["cost_saving"]),
            help="プロンプトを短くして OpenAI トークン消費を削減します（2〜3シーン推奨）",
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
            " 「同名エピソードを上書きする」を有効にするか、別のIDを使用してください。"
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
            cost_saving=cost_saving,
            character=_sel_char,
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

ep_id = ep["episode_id"]
ep_folder = PROJECT_ROOT / "project" / ep_id

st.divider()
st.success(
    f"**{ep['title']}** の生成が完了しました！"
    f" {len(written)} ファイルを `project/{ep_id}/` に書き出しました。"
)
if _sel_char:
    st.info(
        f"🧑 キャラクター **{_sel_char['basic']['display_name']}**"
        f"（{_sel_char['basic'].get('role','')}）"
        f" の設定をプロンプトに適用しました。"
    )

c1, c2, c3, c4 = st.columns(4)
c1.metric("シーン数", len(ep["sections"]))
c2.metric("合計尺", f"{ep['total_duration_seconds']}秒")
c3.metric("台本文字数", f"{sum(len(s['narration_text']) for s in ep['sections'])}文字")
c4.metric("エピソードID", ep_id)

st.divider()

# Scene overview (collapsed by default except first)
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

# ── Manual Production Guide ───────────────────────────────────────────────────

st.header("🛠️ 手動制作ガイド")
st.caption(
    "開発モード: 以下のプロンプトをコピーして各ツールで手動生成してください。"
    " 右上のコピーボタンでクリップボードにコピーできます。"
)

img_tab, vid_tab, voice_tab, srt_tab = st.tabs([
    "🖼️ 画像プロンプト",
    "🎬 動画プロンプト",
    "🎙️ 音声台本",
    "🔤 字幕 SRT",
])

with img_tab:
    st.caption("Nano Banana / Midjourney / DALL-E 等にコピーして画像を生成してください")
    img_path = ep_folder / f"{ep_id}_image_prompts.txt"
    if img_path.exists():
        img_text = img_path.read_text(encoding="utf-8")
        st.code(img_text, language=None)
        st.download_button(
            f"⬇️ {ep_id}_image_prompts.txt をダウンロード",
            data=img_text,
            file_name=f"{ep_id}_image_prompts.txt",
            mime="text/plain",
            use_container_width=True,
            key=f"dl_img_{ep_id}",
        )
    else:
        st.info("画像プロンプトファイルが見つかりません。エピソード管理ページから再エクスポートしてください。")

with vid_tab:
    st.caption("Runway Gen-3 Alpha にコピーして動画クリップを生成してください（各シーン1クリップ）")
    vid_path = ep_folder / f"{ep_id}_video_prompts.txt"
    if vid_path.exists():
        vid_text = vid_path.read_text(encoding="utf-8")
        st.code(vid_text, language=None)
        st.download_button(
            f"⬇️ {ep_id}_video_prompts.txt をダウンロード",
            data=vid_text,
            file_name=f"{ep_id}_video_prompts.txt",
            mime="text/plain",
            use_container_width=True,
            key=f"dl_vid_{ep_id}",
        )
    else:
        st.info("動画プロンプトファイルが見つかりません。")

with voice_tab:
    st.caption("Nano Banana / ElevenLabs / VOICEVOX 等のTTSツールにコピーして音声を生成してください")
    voice_path = ep_folder / f"{ep_id}_voice_script.txt"
    if voice_path.exists():
        voice_text = voice_path.read_text(encoding="utf-8")
        st.code(voice_text, language=None)
        st.download_button(
            f"⬇️ {ep_id}_voice_script.txt をダウンロード",
            data=voice_text,
            file_name=f"{ep_id}_voice_script.txt",
            mime="text/plain",
            use_container_width=True,
            key=f"dl_voice_{ep_id}",
        )
    else:
        st.info("音声台本ファイルが見つかりません。")

with srt_tab:
    st.caption("完成動画に字幕として追加するSRTファイルです。動画編集ソフトにインポートしてください。")
    srt_path = ep_folder / f"{ep_id}.srt"
    if srt_path.exists():
        srt_text = srt_path.read_text(encoding="utf-8")
        st.code(srt_text, language=None)
        st.download_button(
            f"⬇️ {ep_id}.srt をダウンロード",
            data=srt_text,
            file_name=f"{ep_id}.srt",
            mime="text/plain",
            use_container_width=True,
            key=f"dl_srt_{ep_id}",
        )
    else:
        st.info("SRTファイルが見つかりません。")

st.divider()

# ── Production Checklist ──────────────────────────────────────────────────────

st.header("✅ 制作チェックリスト")

CHECKLIST = [
    ("img_copied",  "🖼️ 画像プロンプトをコピーした"),
    ("img_done",    "🎨 画像を手動生成した（Nano Banana / Midjourney 等）"),
    ("vid_copied",  "🎬 動画プロンプトをコピーした"),
    ("vid_done",    "📽️ 動画クリップを手動生成した（Runway Gen-3 Alpha 等）"),
    ("voice_done",  "🎙️ 音声ナレーションを手動生成した（Nano Banana 等）"),
    ("ready",       "📦 全ての最終素材が揃った"),
]

checked_count = sum(
    1 for key, _ in CHECKLIST
    if st.session_state.get(f"chk_{ep_id}_{key}", False)
)
st.progress(
    checked_count / len(CHECKLIST),
    text=f"{checked_count} / {len(CHECKLIST)} 完了",
)

chk_col1, chk_col2 = st.columns(2)
for i, (key, label) in enumerate(CHECKLIST):
    col = chk_col1 if i % 2 == 0 else chk_col2
    with col:
        st.checkbox(label, key=f"chk_{ep_id}_{key}")

if checked_count == len(CHECKLIST):
    st.success(
        "全ての素材が揃いました！ **✂️ 動画組立** ページで最終動画を組み立ててください。"
    )

st.divider()
st.info(
    f"全ファイルは `project/{ep_id}/` に保存済みです。"
    " **🎞️ エピソード管理** ページで内容を確認・編集できます。"
)
