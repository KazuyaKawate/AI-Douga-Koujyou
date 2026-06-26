import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import FOLDERS, PROJECT_ROOT
from src.utils.file_manager import count_files
from src.utils.settings_manager import CONFIG_PATH, load_settings

st.set_page_config(
    page_title="Creator Factory OS",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎯 Creator Factory OS")
st.caption("AIツールを組み合わせた動画制作自動化プラットフォーム | v4.3 — Note Factory")

st.divider()

WORKFLOW = [
    ("🎯", "Mission Control",    "毎日のKPI・タスク・工場状態を一覧管理",    None),
    ("📝", "note投稿工場",       "記事管理・スコア・収益・コンテンツ転用",    None),
    ("⚡", "一発生成",           "AIで全工程を自動生成",                    "project"),
    ("🎞️", "エピソード管理",    "EP制作フロー全体を管理",                  "project"),
    ("📚", "素材ライブラリ",    "素材を管理・エピソードにアサイン",         "assets/images"),
    ("🖼️", "画像・動画生成",   "Runway で映像クリップを生成",              "videos"),
    ("🎙️", "ナレーション",      "Nano Banana で音声を生成",                "voices"),
    ("🔤", "字幕生成",           "Whisper で字幕を自動生成",                "subtitles"),
    ("✂️", "動画組立",           "FFmpeg で素材を結合",                     "output"),
    ("📊", "制作ダッシュボード", "全エピソードの進捗を一覧管理",             "project"),
    ("⚙️", "スタジオ設定",     "プロジェクト・AI・プロバイダー設定",        "config"),
    ("🧑", "キャラクター管理", "動画キャラクターを作成・管理",               None),
    ("🏞️", "背景管理",        "ロケーション・カメラ・シーンテンプレート",   None),
    ("📝", "プロンプトビルダー", "キャラ×背景×ムード×スタイルを合成",          None),
    ("🎬", "制作管理",          "進捗管理・書き出しパッケージ作成",           None),
    ("🎭", "AI Director",      "シーン演出計画・ビジュアルディレクション",   None),
    ("📁", "プロジェクト管理", "シリーズ管理・一括操作・統計・設定",         None),
    ("🤖", "AI Studio",        "マルチエージェント制作スタジオ",             None),
]

st.subheader("制作フロー")
cols = st.columns(len(WORKFLOW))
for col, (icon, title, desc, folder) in zip(cols, WORKFLOW):
    if title == "Mission Control":
        try:
            from src.hq.task_manager import load_tasks, get_task_stats
            _td = load_tasks()
            _stats = get_task_stats(_td)
            count = _stats["done"]
        except Exception:
            count = 0
    elif title == "note投稿工場":
        try:
            import json as _json
            _np = PROJECT_ROOT / "config" / "note_articles.json"
            _nd = _json.loads(_np.read_text(encoding="utf-8")) if _np.exists() else {}
            count = len([a for a in _nd.get("articles", []) if a.get("status") == "published"])
        except Exception:
            count = 0
    elif title == "制作ダッシュボード":
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
    elif title == "キャラクター管理":
        try:
            import json as _json
            _cp = PROJECT_ROOT / "config" / "characters.json"
            count = len(_json.loads(_cp.read_text(encoding="utf-8")).get("characters", [])) if _cp.exists() else 0
        except Exception:
            count = 0
    elif title == "背景管理":
        try:
            import json as _json
            _bp = PROJECT_ROOT / "config" / "backgrounds.json"
            count = len(_json.loads(_bp.read_text(encoding="utf-8")).get("backgrounds", [])) if _bp.exists() else 0
        except Exception:
            count = 0
    elif title == "プロンプトビルダー":
        try:
            import json as _json
            _tp = PROJECT_ROOT / "config" / "prompt_templates.json"
            count = len(_json.loads(_tp.read_text(encoding="utf-8")).get("templates", [])) if _tp.exists() else 0
        except Exception:
            count = 0
    elif title == "制作管理":
        try:
            _pr = PROJECT_ROOT / "project"
            count = sum(
                1 for d in _pr.iterdir()
                if d.is_dir() and (d / "production_state.json").exists()
            ) if _pr.exists() else 0
        except Exception:
            count = 0
    elif title == "AI Director":
        try:
            _pr = PROJECT_ROOT / "project"
            count = sum(
                1 for d in _pr.iterdir()
                if d.is_dir() and (d / "director_plan.json").exists()
            ) if _pr.exists() else 0
        except Exception:
            count = 0
    elif title == "プロジェクト管理":
        try:
            import json as _json
            _ps = PROJECT_ROOT / "config" / "project_settings.json"
            count = len(_json.loads(_ps.read_text(encoding="utf-8")).get("series", [])) if _ps.exists() else 0
        except Exception:
            count = 0
    elif title == "AI Studio":
        try:
            _td = PROJECT_ROOT / "project" / "tasks"
            count = sum(1 for f in _td.glob("task_*.json")) if _td.exists() else 0
        except Exception:
            count = 0
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
**クイックスタート v4.3**
1. 🎯 **Mission Control** で今日のKPI・タスクを確認
2. 📝 **note投稿工場** で記事を作成・スコアリング・収益管理
2. ⚙️ スタジオ設定 でプロジェクト・AI設定を構成
3. 🧑 キャラクター管理 でキャラクターを作成してデフォルト設定
4. 🏞️ 背景管理 でロケーション・カメラ設定を登録
5. 📝 プロンプトビルダー でテンプレートを保存
6. 🤖 **AI Studio** でマルチエージェントパイプラインを開始
   - ProducerAgent → DirectorAgent → ScriptAgent
   - → PromptAgent → EditorAgent → PublisherAgent
7. または ⚡ 一発生成 で単体エピソードを生成
8. 🎭 AI Director で演出計画を設計
9. 🎬 制作管理 で書き出しパッケージを作成
10. 📁 プロジェクト管理 でシリーズ・バックアップ・統計を管理
""")
