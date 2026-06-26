import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import FOLDERS, PROJECT_ROOT
from src.utils.file_manager import count_files
from src.utils.settings_manager import CONFIG_PATH, load_settings

st.set_page_config(
    page_title="AI動画工場",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎬 AI動画工場")
st.caption("AIツールを組み合わせた動画制作自動化プラットフォーム | v2.6")

st.divider()

WORKFLOW = [
    ("⚡", "一発生成",           "AIで全工程を自動生成",              "project"),
    ("🎞️", "エピソード管理",    "EP制作フロー全体を管理",            "project"),
    ("📚", "素材ライブラリ",    "素材を管理・エピソードにアサイン",   "assets/images"),
    ("🖼️", "画像・動画生成",   "Runway で映像クリップを生成",        "videos"),
    ("🎙️", "ナレーション",      "Nano Banana で音声を生成",          "voices"),
    ("🔤", "字幕生成",           "Whisper で字幕を自動生成",          "subtitles"),
    ("✂️", "動画組立",           "FFmpeg で素材を結合",               "output"),
    ("📊", "制作ダッシュボード", "全エピソードの進捗を一覧管理",       "project"),
    ("⚙️", "スタジオ設定",     "プロジェクト・AI・プロバイダー設定",  "config"),
]

st.subheader("制作フロー")
cols = st.columns(len(WORKFLOW))
for col, (icon, title, desc, folder) in zip(cols, WORKFLOW):
    if title == "制作ダッシュボード":
        ep_root = PROJECT_ROOT / folder
        count = (
            sum(
                1 for d in ep_root.iterdir()
                if d.is_dir() and (d / "episode.json").exists()
            )
            if ep_root.exists() else 0
        )
    elif title == "スタジオ設定":
        count = 1 if CONFIG_PATH.exists() else 0
    else:
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
**クイックスタート v2.6**
1. ⚙️ スタジオ設定 でプロジェクト・AI・プロバイダーを設定
2. ⚡ 一発生成 でテーマを入力 → 台本・プロンプト・字幕を全自動生成
3. 🛠️ プロンプトをコピーして Runway / Nano Banana で手動生成
4. 📚 素材ライブラリ で生成素材を管理・メモ・エピソードにアサイン
5. 🎞️ エピソード管理 で内容を確認・編集
6. ✂️ 動画組立 で最終動画を書き出し (FFmpeg)
7. 📊 制作ダッシュボード で全エピソードの進捗を一覧確認
""")
