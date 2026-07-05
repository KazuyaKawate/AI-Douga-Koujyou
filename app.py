import json as _json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src.utils.config import FOLDERS, PROJECT_ROOT
from src.utils.file_manager import count_files
from src.utils.settings_manager import CONFIG_PATH, load_settings
from src.core.version import OS_VERSION, get_version_label

st.set_page_config(
    page_title="Creator Factory OS",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎯 Creator Factory OS")
st.caption(f"AIツールを組み合わせた動画制作自動化プラットフォーム | {get_version_label()}")

st.divider()

WORKFLOW = [
    ("🎯", "Mission Control",    "毎日のKPI・タスク・工場状態を一覧管理",    None),
    ("📝", "note投稿工場",       "記事管理・スコア・収益・コンテンツ転用",    None),
    ("📱", "SNS投稿工場",       "プラットフォーム別SNS投稿管理・スケジュール", None),
    ("💼", "営業工場",          "CRM・リード管理・商談・フォロー・売上予測",   None),
    ("💰", "会計監査工場",       "収支管理・ROI・サブスク・監査・月次レポート", None),
    ("📊", "アナリティクス工場", "全工場・KPI・ROI・プロジェクト分析・インサイト", None),
    ("⚙️", "自動化工場",        "ルールベース工場間ワークフロー自動化",          None),
    ("🔍", "承認アシスタント",  "Claude Codeの承認プロンプトをリスク分類",    None),
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
    ("🛠️", "Development Studio", "OS開発HQ — ロードマップ・決定ログ・リリース管理", None),
    ("🧠", "AI CEO",           "エグゼクティブ分析・優先度・リスク・推奨アクション", None),
    ("✅", "Approval Center",  "人間承認ゲートウェイ — AI CEO・自動化・DevStudio", None),
]

WORKFLOW_PAGES = {
    "Mission Control": "pages/17_Mission_Control.py",
    "note投稿工場": "pages/18_Note_Factory.py",
    "SNS投稿工場": "pages/19_SNS_Factory.py",
    "営業工場": "pages/21_Sales_Factory.py",
    "会計監査工場": "pages/22_Accounting_Factory.py",
    "アナリティクス工場": "pages/23_Analytics_Factory.py",
    "自動化工場": "pages/24_Automation_Factory.py",
    "承認アシスタント": "pages/20_Approval_Assistant.py",
    "一発生成": "pages/6_Produce.py",
    "エピソード管理": "pages/5_Episode.py",
    "素材ライブラリ": "pages/7_Assets.py",
    "画像・動画生成": "pages/13_Production.py",
    "ナレーション": "pages/13_Production.py",
    "字幕生成": "pages/2_Subtitles.py",
    "動画組立": "pages/3_Assembly.py",
    "制作ダッシュボード": "pages/8_Dashboard.py",
    "スタジオ設定": "pages/9_Settings.py",
    "キャラクター管理": "pages/10_Characters.py",
    "背景管理": "pages/11_Backgrounds.py",
    "プロンプトビルダー": "pages/12_Prompt_Builder.py",
    "制作管理": "pages/13_Production.py",
    "AI Director": "pages/14_Director.py",
    "プロジェクト管理": "pages/15_Project_Manager.py",
    "AI Studio": "pages/16_AI_Studio.py",
    "Development Studio": "pages/25_Development_Studio.py",
    "AI CEO": "pages/26_AI_CEO.py",
    "Approval Center": "pages/27_Approval_Center.py",
}

WORKFLOW_GROUPS = [
    (
        "🎬 Creator Factory",
        "動画制作・素材・エピソード制作に使うページ",
        [
            "一発生成",
            "エピソード管理",
            "素材ライブラリ",
            "画像・動画生成",
            "ナレーション",
            "字幕生成",
            "動画組立",
            "制作ダッシュボード",
            "キャラクター管理",
            "背景管理",
            "プロンプトビルダー",
            "制作管理",
            "AI Director",
            "プロジェクト管理",
        ],
    ),
    (
        "🏭 Business Factories",
        "日次運用・投稿・営業・会計・分析・自動化の業務ページ",
        [
            "note投稿工場",
            "SNS投稿工場",
            "営業工場",
            "会計監査工場",
            "アナリティクス工場",
            "自動化工場",
        ],
    ),
    (
        "🧠 AIOS Control",
        "OS管理・AIエージェント・承認・設定のページ",
        [
            "Mission Control",
            "スタジオ設定",
            "AI Studio",
            "Development Studio",
            "AI CEO",
            "Approval Center",
            "承認アシスタント",
        ],
    ),
]

WORKFLOW_BY_TITLE = {title: (icon, desc, folder) for icon, title, desc, folder in WORKFLOW}


def get_workflow_count(title: str, folder: str | None) -> int:
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
            _np = PROJECT_ROOT / "config" / "note_articles.json"
            _nd = _json.loads(_np.read_text(encoding="utf-8")) if _np.exists() else {}
            count = len([a for a in _nd.get("articles", []) if a.get("status") == "published"])
        except Exception:
            count = 0
    elif title == "SNS投稿工場":
        try:
            _sp = PROJECT_ROOT / "config" / "sns_posts.json"
            _sd = _json.loads(_sp.read_text(encoding="utf-8")) if _sp.exists() else {}
            count = len([p for p in _sd.get("posts", []) if p.get("status") == "published"])
        except Exception:
            count = 0
    elif title == "営業工場":
        try:
            _slp = PROJECT_ROOT / "config" / "sales_leads.json"
            _sld = _json.loads(_slp.read_text(encoding="utf-8")) if _slp.exists() else {}
            count = len([l for l in _sld.get("leads", []) if l.get("status") not in ("archived",)])
        except Exception:
            count = 0
    elif title == "会計監査工場":
        try:
            _arp = PROJECT_ROOT / "config" / "accounting_revenue.json"
            _ard = _json.loads(_arp.read_text(encoding="utf-8")) if _arp.exists() else {}
            count = sum(1 for r in _ard.get("revenue", []) if r.get("status") == "confirmed")
        except Exception:
            count = 0
    elif title == "アナリティクス工場":
        try:
            _anp = PROJECT_ROOT / "config" / "analytics_snapshots.json"
            _and = _json.loads(_anp.read_text(encoding="utf-8")) if _anp.exists() else {}
            count = len(_and.get("snapshots", []))
        except Exception:
            count = 0
    elif title == "自動化工場":
        try:
            _awp = PROJECT_ROOT / "config" / "automation_workflows.json"
            _awd = _json.loads(_awp.read_text(encoding="utf-8")) if _awp.exists() else {}
            count = sum(1 for w in _awd.get("workflows", []) if w.get("enabled"))
        except Exception:
            count = 0
    elif title == "承認アシスタント":
        try:
            _ap = PROJECT_ROOT / "config" / "approval_history.json"
            _ad = _json.loads(_ap.read_text(encoding="utf-8")) if _ap.exists() else {}
            count = len(_ad.get("history", []))
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
            _cp = PROJECT_ROOT / "config" / "characters.json"
            count = len(_json.loads(_cp.read_text(encoding="utf-8")).get("characters", [])) if _cp.exists() else 0
        except Exception:
            count = 0
    elif title == "背景管理":
        try:
            _bp = PROJECT_ROOT / "config" / "backgrounds.json"
            count = len(_json.loads(_bp.read_text(encoding="utf-8")).get("backgrounds", [])) if _bp.exists() else 0
        except Exception:
            count = 0
    elif title == "プロンプトビルダー":
        try:
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
    elif title == "Development Studio":
        try:
            from src.devstudio.roadmap_manager import get_summary as _ds_sum
            count = _ds_sum()["in_progress"]
        except Exception:
            count = 0
    elif title == "AI CEO":
        try:
            from src.aiceo.executive_engine import collect_snapshot as _ceo_snap
            from src.aiceo.risk_engine import identify_risks as _ceo_risks
            from src.aiceo.executive_dashboard import compute_overall_health as _ceo_health
            _ccs = _ceo_snap()
            _ccr = _ceo_risks(_ccs)
            _cch = _ceo_health(_ccs, _ccr)
            count = _cch["score"]
        except Exception:
            count = 0
    elif title == "Approval Center":
        try:
            from src.approval.approval_queue import get_summary as _ac_s
            count = _ac_s()["pending_count"]
        except Exception:
            count = 0
    else:
        count = count_files(PROJECT_ROOT / folder)
    return count


def render_workflow_card(title: str) -> None:
    icon, desc, folder = WORKFLOW_BY_TITLE[title]
    page_path = WORKFLOW_PAGES[title]
    count = get_workflow_count(title, folder)
    with st.container(border=True):
        st.metric(label=f"{icon} {title}", value=count, help=desc)
        st.caption(desc)
        st.page_link(page_path, label="開く", icon="↗️", use_container_width=True)


st.subheader("制作フロー")
st.caption("Creator Factory と AIOS 管理ページを分けて表示しています。すべての既存ページは引き続きサイドバーからも開けます。")
workflow_tabs = st.tabs([group_name for group_name, _, _ in WORKFLOW_GROUPS])
for tab, (_, group_desc, titles) in zip(workflow_tabs, WORKFLOW_GROUPS):
    with tab:
        st.caption(group_desc)
        for start in range(0, len(titles), 3):
            cols = st.columns(3)
            for col, title in zip(cols, titles[start:start + 3]):
                with col:
                    render_workflow_card(title)

st.divider()

st.subheader("フォルダ統計")
cols = st.columns(len(FOLDERS))
for col, (label, folder) in zip(cols, FOLDERS.items()):
    count = count_files(PROJECT_ROOT / folder)
    col.metric(label=label, value=f"{count} ファイル")

st.divider()

# ── System Overview — Project Registry (v4.5.1) ────────────────────────────────
try:
    from src.core.project_registry import ProjectRegistry as _AppPR
    from src.core.factory_registry import FactoryRegistry as _AppFR
    _app_sys = _AppPR.get_system_summary()
    _app_projs = _AppPR.get_all_project_summaries()
    _app_hdot  = {"ok": "✅", "degraded": "🟡", "failed": "🔴"}.get(_app_sys["system_health"], "⚪")
    st.subheader("🗂️ Projects")
    _acols = st.columns(len(_app_projs)) if _app_projs else [st.container()]
    for _ci, _ap in enumerate(_app_projs):
        with _acols[_ci]:
            with st.container(border=True):
                st.metric(
                    label=f"{_ap['status_icon']} {_ap['name']}",
                    value=f"{_ap['factory_count']} 工場",
                    help=_ap.get("description", ""),
                )
                st.caption(f"👤 {_ap['owner']}  |  優先度: {_ap['priority']}")
    st.caption(
        f"{_app_hdot} System Health: {_app_sys['health_pct']}%  |  "
        f"工場 {_app_sys['healthy_factories']}/{_app_sys['total_factories']} 正常"
    )
    st.divider()
except Exception:
    pass

col1, col2 = st.columns([2, 1])
with col1:
    st.info("👈 左のサイドバーから各ページを選択して作業を開始してください。")
with col2:
    st.markdown(f"""
**クイックスタート v{OS_VERSION}**
1. 🛠️ **Development Studio** でロードマップ・決定・リリースを管理
2. 🗂️ **Projects** でプロジェクトとシステム健全性を確認
2. 🎯 **Mission Control** で今日のKPI・タスク・工場状態を確認
3. 📝 **note投稿工場** で記事を作成・スコアリング・収益管理
4. 📱 **SNS投稿工場** でプラットフォーム別投稿を生成・スケジュール
5. 💼 **営業工場** でリード管理・商談・フォロー・売上予測
6. 💰 **会計監査工場** で収支・ROI・サブスク・監査・月次レポート
7. 📊 **アナリティクス工場** で全工場・KPI・ROI・インサイト分析
8. ⚙️ **自動化工場** でルールベースワークフローを設定・実行
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
