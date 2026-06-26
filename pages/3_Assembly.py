import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import PROJECT_ROOT
from src.utils.file_manager import list_files

st.set_page_config(page_title="動画組立", page_icon="🎬", layout="wide")
st.title("🎬 動画組立")
st.caption("FFmpeg で動画・音声・字幕を組み合わせて最終動画を作成します")

VIDEO_EXTS = [".mp4", ".mov", ".avi", ".mkv"]
AUDIO_EXTS = [".mp3", ".wav", ".m4a", ".aac"]
SUB_EXTS = [".srt", ".vtt"]

video_files = list_files(PROJECT_ROOT / "videos", VIDEO_EXTS)
audio_files = list_files(PROJECT_ROOT / "voices", AUDIO_EXTS)
sub_files = list_files(PROJECT_ROOT / "subtitles", SUB_EXTS)

col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("素材選択")

    video_options = ["（なし）"] + [f.name for f in video_files]
    video_sel = st.selectbox("🎬 動画ファイル", video_options)
    video_path = next((f for f in video_files if f.name == video_sel), None)

    audio_options = ["（なし）"] + [f.name for f in audio_files]
    audio_sel = st.selectbox("🔊 音声ファイル", audio_options)
    audio_path = next((f for f in audio_files if f.name == audio_sel), None)

    sub_options = ["（なし）"] + [f.name for f in sub_files]
    sub_sel = st.selectbox("🔤 字幕ファイル（任意）", sub_options)
    sub_path = next((f for f in sub_files if f.name == sub_sel), None)

    st.divider()
    output_name = st.text_input("出力ファイル名", value="output.mp4")

    can_process = video_path is not None or audio_path is not None
    if st.button("動画を組立てる ▶️", type="primary", disabled=not can_process, use_container_width=True):
        from src.core.ffmpeg_utils import combine_video_audio_subtitle

        output_path = PROJECT_ROOT / "output" / output_name
        with st.spinner("FFmpeg で処理中..."):
            success = combine_video_audio_subtitle(video_path, audio_path, sub_path, output_path)

        if success:
            st.success(f"完成！ `output/{output_name}` に保存しました 🎉")
        else:
            st.error("処理中にエラーが発生しました。FFmpeg がインストールされているか確認してください。")

with col_right:
    st.subheader("動画情報")
    if video_path:
        from src.core.ffmpeg_utils import get_video_info
        info = get_video_info(video_path)
        if info:
            for k, v in info.items():
                st.metric(label=k, value=v)
        else:
            st.info("動画情報を取得できません（FFmpeg が必要です）")
    else:
        st.info("動画ファイルを選択すると情報が表示されます")

st.divider()
st.subheader("完成動画")
output_files = list_files(PROJECT_ROOT / "output", VIDEO_EXTS)
if output_files:
    st.write(f"合計 **{len(output_files)}** ファイル")
    for f in output_files:
        col1, col2 = st.columns([3, 1])
        col1.write(f.name)
        col2.write(f"{f.stat().st_size / (1024*1024):.1f} MB")
else:
    st.info("output/ に完成動画がありません")
