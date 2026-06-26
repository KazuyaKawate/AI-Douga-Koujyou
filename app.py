import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import FOLDERS, PROJECT_ROOT
from src.utils.file_manager import count_files

st.set_page_config(
    page_title="AI動画工場",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎬 AI動画工場")
st.caption("AIツールを組み合わせた動画制作自動化プラットフォーム | v1.1")

st.divider()

WORKFLOW = [
    ("🎞️", "エピソード管理", "EP制作フロー全体を管理", "project"),
    ("📝", "台本生成", "OpenAI GPT で台本を生成", "scripts"),
    ("🖼️", "画像・動画生成", "Runway で映像クリップを生成", "videos"),
    ("🎙️", "ナレーション", "Nano Banana で音声を生成", "voices"),
    ("🔤", "字幕生成", "Whisper で字幕を自動生成", "subtitles"),
    ("✂️", "動画組立", "FFmpeg で素材を結合", "output"),
    ("🚀", "公開・配信", "YouTube・SNS に投稿", "output"),
]

st.subheader("制作フロー")
cols = st.columns(len(WORKFLOW))
for col, (icon, title, desc, folder) in zip(cols, WORKFLOW):
    count = count_files(PROJECT_ROOT / folder)
    col.metric(label=f"{icon} {title}", value=count, help=desc)

st.divider()

st.subheader("フォルダ統計")
cols = st.columns(len(FOLDERS))
for col, (label, folder) in zip(cols, FOLDERS.items()):
    count = count_files(PROJECT_ROOT / folder)
    col.metric(label=label, value=f"{count} ファイル")

st.divider()

col1, col2 = st.columns([2, 1])
with col1:
    st.info("👈 左のサイドバーから各ページを選択して作業を開始してください。")
with col2:
    st.markdown("""
**クイックスタート v1.1**
1. 🎞️ エピソード管理 でEP01を新規作成
2. 📝 台本タブでセクションを追加
3. 🖼️/🎬 プロンプトを一括生成
4. 🎙️ 音声台本・字幕をエクスポート
5. 📦 project/EP01/ に全ファイルを書き出し
""")
