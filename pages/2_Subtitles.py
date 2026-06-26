import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PROJECT_ROOT
from src.utils.file_manager import list_files

st.set_page_config(page_title="字幕生成", page_icon="🎙️", layout="wide")
st.title("🎙️ 字幕生成")
st.caption("Whisper で音声ファイルから字幕（SRT形式）を自動生成します")

AUDIO_EXTS = [".mp3", ".wav", ".m4a", ".mp4", ".mov", ".flac"]
LANG_LABELS = {"ja": "日本語", "en": "英語", "auto": "自動検出"}

tab1, tab2 = st.tabs(["📤 ファイルをアップロード", "📁 プロジェクトから選択"])

def run_transcription(audio_path: Path, lang: str):
    from src.core.whisper_client import transcribe_audio
    with st.spinner("Whisper で文字起こし中... （初回はモデルのダウンロードに時間がかかります）"):
        try:
            return transcribe_audio(audio_path, lang)
        except Exception as e:
            st.error(f"エラー: {e}")
            return None

def save_and_download(srt: str, stem: str):
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{stem}.srt"
    save_path = PROJECT_ROOT / "subtitles" / filename
    col1, col2 = st.columns(2)
    if col1.button("💾 subtitles/ に保存", use_container_width=True):
        save_path.write_text(srt, encoding="utf-8")
        st.success(f"保存しました: `subtitles/{filename}`")
    col2.download_button("⬇️ ダウンロード", data=srt, file_name=filename, mime="text/plain", use_container_width=True)

with tab1:
    uploaded = st.file_uploader("音声・動画ファイルをアップロード", type=[e.lstrip(".") for e in AUDIO_EXTS])
    lang = st.selectbox("言語", list(LANG_LABELS.keys()), format_func=lambda x: LANG_LABELS[x], key="lang_upload")

    if uploaded and st.button("字幕を生成する 🚀", type="primary", key="gen_upload"):
        temp_path = PROJECT_ROOT / "temp" / uploaded.name
        temp_path.parent.mkdir(exist_ok=True)
        temp_path.write_bytes(uploaded.read())

        srt = run_transcription(temp_path, lang)
        if srt:
            st.success("字幕の生成が完了しました！")
            st.text_area("生成された SRT", value=srt, height=350)
            save_and_download(srt, Path(uploaded.name).stem)
            temp_path.unlink(missing_ok=True)

with tab2:
    audio_files = list_files(PROJECT_ROOT / "voices", AUDIO_EXTS)
    if audio_files:
        selected_name = st.selectbox("音声ファイルを選択", [f.name for f in audio_files])
        selected_path = next(f for f in audio_files if f.name == selected_name)
        lang2 = st.selectbox("言語", list(LANG_LABELS.keys()), format_func=lambda x: LANG_LABELS[x], key="lang_project")

        if st.button("字幕を生成する 🚀", type="primary", key="gen_project"):
            srt = run_transcription(selected_path, lang2)
            if srt:
                st.success("字幕の生成が完了しました！")
                st.text_area("生成された SRT", value=srt, height=350)
                save_and_download(srt, selected_path.stem)
    else:
        st.info("voices/ フォルダに音声ファイルがありません")

st.divider()
st.subheader("保存済み字幕ファイル")
srt_files = list_files(PROJECT_ROOT / "subtitles", [".srt", ".vtt"])
if srt_files:
    selected_srt = st.selectbox("ファイルを選択", [f.name for f in srt_files])
    if selected_srt:
        content = (PROJECT_ROOT / "subtitles" / selected_srt).read_text(encoding="utf-8")
        st.text_area("内容", value=content, height=250)
else:
    st.info("subtitles/ に字幕ファイルがありません")
