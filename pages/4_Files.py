import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import FOLDERS, PROJECT_ROOT
from src.utils.file_manager import file_info, list_files
from src.utils.settings_manager import load_settings

st.set_page_config(page_title="ファイル管理", page_icon="📁", layout="wide")
st.title("📁 ファイル管理")
st.caption("プロジェクト内のファイルを確認・管理します")

_settings = load_settings()
_p = _settings["project"]
st.sidebar.caption(f"⚙️ 出力: `{_p['default_output_folder']}/` | `{_p['resolution']}`")

col_summary, col_detail = st.columns([1, 2])

with col_summary:
    st.subheader("フォルダ概要")
    summary = []
    for label, folder in FOLDERS.items():
        path = PROJECT_ROOT / folder
        files = list_files(path)
        total_size = sum(f.stat().st_size for f in files) / 1024
        summary.append({"フォルダ": label, "ファイル数": len(files), "合計サイズ": f"{total_size:.0f} KB"})
    st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)

with col_detail:
    st.subheader("ファイル一覧")
    selected_label = st.selectbox("フォルダを選択", list(FOLDERS.keys()))
    folder_path = PROJECT_ROOT / FOLDERS[selected_label]

    files = list_files(folder_path)
    if files:
        df = pd.DataFrame([file_info(f) for f in files])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"合計 {len(files)} ファイル — {FOLDERS[selected_label]}/")
    else:
        st.info(f"`{FOLDERS[selected_label]}/` にファイルがありません")

st.divider()
st.subheader("ファイルプレビュー")
text_files = list_files(PROJECT_ROOT / FOLDERS.get("台本", "scripts"), [".txt", ".md"])
srt_files = list_files(PROJECT_ROOT / FOLDERS.get("字幕", "subtitles"), [".srt", ".vtt"])
previewable = text_files + srt_files

if previewable:
    selected_file = st.selectbox("プレビューするファイルを選択", [f.name for f in previewable])
    matched = next((f for f in previewable if f.name == selected_file), None)
    if matched:
        st.text_area("内容", value=matched.read_text(encoding="utf-8"), height=300)
else:
    st.info("プレビュー可能なテキストファイルがありません（台本・字幕ファイルが対象です）")
