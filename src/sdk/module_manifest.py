"""module_manifest — MODULE_INFO schema and manifest helpers for Creator Factory OS SDK."""
from __future__ import annotations
from typing import TypedDict

MODULE_TYPES = ["factory", "executive", "development", "utility"]

REQUIRED_FIELDS = [
    "module_name", "module_type", "version", "description",
]

_DEFAULTS: dict = {
    "author":                 "Creator Factory OS",
    "health_check":           None,
    "dashboard_widget":       False,
    "mission_control_widget": False,
    "project_support":        False,
    "dependencies":           [],
    "page_path":              None,
    "config_files":           [],
    "report_dir":             None,
    "tags":                   [],
}


class ModuleInfo(TypedDict, total=False):
    module_name:              str
    module_type:              str   # factory | executive | development | utility
    version:                  str
    author:                   str
    description:              str
    health_check:             str | None   # dotted import path e.g. "src.aiceo.check"
    dashboard_widget:         bool
    mission_control_widget:   bool
    project_support:          bool
    dependencies:             list[str]
    page_path:                str | None   # e.g. "pages/26_AI_CEO.py"
    config_files:             list[str]
    report_dir:               str | None
    tags:                     list[str]


def make_manifest(
    module_name: str,
    module_type: str,
    version: str,
    description: str,
    **kwargs,
) -> dict:
    """Create a MODULE_INFO dict with validated fields and defaults."""
    if module_type not in MODULE_TYPES:
        raise ValueError(f"module_type must be one of {MODULE_TYPES}, got '{module_type}'")
    manifest = dict(_DEFAULTS)
    manifest.update(kwargs)
    manifest.update({
        "module_name":  module_name,
        "module_type":  module_type,
        "version":      version,
        "description":  description,
    })
    return manifest


# ── Built-in module manifests ─────────────────────────────────────────────────
BUILTIN_MANIFESTS: list[dict] = [
    make_manifest(
        module_name="AI動画工場",
        module_type="factory",
        version="4.8",
        description="動画制作自動化工場。スクリプト生成からアセンブリまで。",
        page_path="pages/1_Script.py",
        dashboard_widget=True,
        mission_control_widget=True,
        project_support=True,
        dependencies=["src.core.openai_client", "src.core.ffmpeg_utils"],
        tags=["video", "production"],
    ),
    make_manifest(
        module_name="note投稿工場",
        module_type="factory",
        version="4.3",
        description="note記事管理・スコアリング・収益・転用工場。",
        page_path="pages/18_Note_Factory.py",
        dashboard_widget=True,
        mission_control_widget=True,
        project_support=False,
        config_files=["config/note_articles.json"],
        tags=["content", "note"],
    ),
    make_manifest(
        module_name="SNS投稿工場",
        module_type="factory",
        version="4.4",
        description="7プラットフォーム対応SNS投稿管理・スケジュール工場。",
        page_path="pages/19_SNS_Factory.py",
        dashboard_widget=True,
        mission_control_widget=True,
        config_files=["config/sns_posts.json", "config/sns_platforms.json"],
        tags=["sns", "content"],
    ),
    make_manifest(
        module_name="営業工場",
        module_type="factory",
        version="4.5",
        description="CRM・リード管理・商談・フォロー・売上予測工場。",
        page_path="pages/21_Sales_Factory.py",
        dashboard_widget=True,
        mission_control_widget=True,
        config_files=["config/sales_leads.json", "config/sales_deals.json"],
        tags=["sales", "crm"],
    ),
    make_manifest(
        module_name="会計監査工場",
        module_type="factory",
        version="4.6",
        description="収支管理・ROI・監査・月次レポート工場。",
        page_path="pages/22_Accounting_Factory.py",
        dashboard_widget=True,
        mission_control_widget=True,
        config_files=["config/accounting_revenue.json"],
        tags=["accounting", "finance"],
    ),
    make_manifest(
        module_name="アナリティクス工場",
        module_type="factory",
        version="4.7",
        description="全工場・KPI・ROI・プロジェクト横断分析工場。",
        page_path="pages/23_Analytics_Factory.py",
        dashboard_widget=True,
        mission_control_widget=True,
        report_dir="reports/analytics",
        tags=["analytics", "kpi"],
    ),
    make_manifest(
        module_name="自動化工場",
        module_type="factory",
        version="4.8",
        description="ルールベース工場間ワークフロー自動化。ドライランデフォルト。",
        page_path="pages/24_Automation_Factory.py",
        dashboard_widget=True,
        mission_control_widget=True,
        config_files=["config/automation_workflows.json", "config/automation_runs.json"],
        report_dir="reports/automation",
        tags=["automation", "workflow"],
    ),
    make_manifest(
        module_name="承認アシスタント",
        module_type="utility",
        version="4.4.1",
        description="Claude Codeの承認プロンプトをリスク分類するユーティリティ。",
        page_path="pages/20_Approval_Assistant.py",
        mission_control_widget=True,
        config_files=["config/approval_history.json"],
        tags=["devtools", "approval"],
    ),
    make_manifest(
        module_name="Development Studio",
        module_type="development",
        version="5.0-beta",
        description="OS開発HQ。ロードマップ・リリース・決定ログ・ミーティングノート管理。",
        page_path="pages/25_Development_Studio.py",
        dashboard_widget=True,
        mission_control_widget=True,
        config_files=[
            "config/devstudio_roadmap.json",
            "config/devstudio_releases.json",
            "config/devstudio_decisions.json",
            "config/devstudio_meetings.json",
        ],
        report_dir="reports/devstudio",
        tags=["devstudio", "roadmap", "os-management"],
    ),
    make_manifest(
        module_name="AI CEO Core",
        module_type="executive",
        version="5.0-beta",
        description="エグゼクティブ決定レイヤー。健全度・優先度・リスク・推奨アクション。",
        page_path="pages/26_AI_CEO.py",
        dashboard_widget=True,
        mission_control_widget=True,
        config_files=["config/aiceo_settings.json", "config/aiceo_history.json"],
        report_dir="reports/aiceo",
        tags=["executive", "ai-ceo"],
    ),
    make_manifest(
        module_name="Approval Center",
        module_type="utility",
        version="5.1",
        description="人間承認ゲートウェイ。AI CEO・自動化・開発Studio からのアクションをレビュー。",
        page_path="pages/27_Approval_Center.py",
        dashboard_widget=True,
        mission_control_widget=True,
        config_files=["config/approval_queue.json"],
        tags=["approval", "governance"],
    ),
]
