"""module_manifest — MODULE_INFO schema and manifest helpers for Creator Factory OS SDK v5.1."""
from __future__ import annotations
import re
import unicodedata
from typing import TypedDict

SDK_VERSION = "5.1"

MODULE_TYPES = ["factory", "executive", "development", "utility"]
MODULE_STATUSES = ["stable", "beta", "alpha", "deprecated", "experimental"]

REQUIRED_FIELDS = [
    "module_name", "module_type", "version", "description",
]

_DEFAULTS: dict = {
    "module_id":              None,       # auto-generated from module_name
    "display_name":           None,       # defaults to module_name
    "sdk_version":            SDK_VERSION,
    "minimum_os_version":     "5.0",
    "author":                 "Creator Factory OS",
    "entrypoint":             None,       # dotted import path e.g. "src.aiceo.executive_engine"
    "package_path":           None,       # e.g. "src/aiceo/"
    "health_check":           None,       # dotted import path for health-check function
    "dashboard_widget":       False,
    "mission_control_widget": False,
    "project_support":        False,
    "dependencies":           [],
    "page_path":              None,       # e.g. "pages/26_AI_CEO.py"
    "config_files":           [],
    "report_dir":             None,
    "tags":                   [],
    "status":                 "stable",
}


class ModuleInfo(TypedDict, total=False):
    module_id:                str
    display_name:             str
    module_name:              str
    module_type:              str          # factory | executive | development | utility
    version:                  str
    sdk_version:              str
    minimum_os_version:       str
    author:                   str
    description:              str
    entrypoint:               str | None
    package_path:             str | None
    health_check:             str | None
    dashboard_widget:         bool
    mission_control_widget:   bool
    project_support:          bool
    dependencies:             list[str]
    page_path:                str | None
    config_files:             list[str]
    report_dir:               str | None
    tags:                     list[str]
    status:                   str          # stable | beta | alpha | deprecated | experimental


def _slugify(name: str) -> str:
    """Convert a module name to a URL-safe slug."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug or f"module-{abs(hash(name)) % 100000}"


def make_manifest(
    module_name: str,
    module_type: str,
    version: str,
    description: str,
    **kwargs,
) -> dict:
    """Create a MODULE_INFO dict with validated fields and defaults.

    Backward compatible: same positional signature as v5.1 Phase 1.
    New optional fields (module_id, display_name, status, …) can be passed as kwargs
    or will be auto-populated from defaults.
    """
    if module_type not in MODULE_TYPES:
        raise ValueError(f"module_type must be one of {MODULE_TYPES}, got '{module_type}'")
    manifest = dict(_DEFAULTS)
    manifest["dependencies"] = list(_DEFAULTS["dependencies"])
    manifest["config_files"] = list(_DEFAULTS["config_files"])
    manifest["tags"] = list(_DEFAULTS["tags"])
    manifest.update(kwargs)
    manifest.update({
        "module_name":  module_name,
        "module_type":  module_type,
        "version":      version,
        "description":  description,
    })
    if not manifest.get("module_id"):
        manifest["module_id"] = kwargs.get("module_id") or _slugify(module_name)
    if not manifest.get("display_name"):
        manifest["display_name"] = module_name
    return manifest


# ── Built-in module manifests ─────────────────────────────────────────────────
BUILTIN_MANIFESTS: list[dict] = [
    make_manifest(
        module_name="AI動画工場",
        module_type="factory",
        version="4.8",
        description="動画制作自動化工場。スクリプト生成からアセンブリまで。",
        module_id="video-factory",
        display_name="AI Video Factory",
        minimum_os_version="1.0",
        entrypoint="src.pipeline.script_pipeline",
        package_path="src/pipeline/",
        page_path="pages/1_Script.py",
        dashboard_widget=True,
        mission_control_widget=True,
        project_support=True,
        dependencies=["src.core.openai_client", "src.core.ffmpeg_utils"],
        tags=["video", "production"],
        status="stable",
    ),
    make_manifest(
        module_name="note投稿工場",
        module_type="factory",
        version="4.3",
        description="note記事管理・スコアリング・収益・転用工場。",
        module_id="note-factory",
        display_name="Note Factory",
        minimum_os_version="4.3",
        entrypoint="src.factories.note.article_manager",
        package_path="src/factories/note/",
        page_path="pages/18_Note_Factory.py",
        dashboard_widget=True,
        mission_control_widget=True,
        project_support=False,
        config_files=["config/note_articles.json"],
        tags=["content", "note"],
        status="stable",
    ),
    make_manifest(
        module_name="SNS投稿工場",
        module_type="factory",
        version="4.4",
        description="7プラットフォーム対応SNS投稿管理・スケジュール工場。",
        module_id="sns-factory",
        display_name="SNS Factory",
        minimum_os_version="4.4",
        entrypoint="src.factories.sns.sns_post_manager",
        package_path="src/factories/sns/",
        page_path="pages/19_SNS_Factory.py",
        dashboard_widget=True,
        mission_control_widget=True,
        config_files=["config/sns_posts.json", "config/sns_platforms.json"],
        tags=["sns", "content"],
        status="stable",
    ),
    make_manifest(
        module_name="営業工場",
        module_type="factory",
        version="4.5",
        description="CRM・リード管理・商談・フォロー・売上予測工場。",
        module_id="sales-factory",
        display_name="Sales Factory",
        minimum_os_version="4.5",
        entrypoint="src.factories.sales.lead_manager",
        package_path="src/factories/sales/",
        page_path="pages/21_Sales_Factory.py",
        dashboard_widget=True,
        mission_control_widget=True,
        config_files=["config/sales_leads.json", "config/sales_deals.json"],
        tags=["sales", "crm"],
        status="stable",
    ),
    make_manifest(
        module_name="会計監査工場",
        module_type="factory",
        version="4.6",
        description="収支管理・ROI・監査・月次レポート工場。",
        module_id="accounting-factory",
        display_name="Accounting Factory",
        minimum_os_version="4.6",
        entrypoint="src.factories.accounting.revenue_manager",
        package_path="src/factories/accounting/",
        page_path="pages/22_Accounting_Factory.py",
        dashboard_widget=True,
        mission_control_widget=True,
        config_files=["config/accounting_revenue.json"],
        tags=["accounting", "finance"],
        status="stable",
    ),
    make_manifest(
        module_name="アナリティクス工場",
        module_type="factory",
        version="4.7",
        description="全工場・KPI・ROI・プロジェクト横断分析工場。",
        module_id="analytics-factory",
        display_name="Analytics Factory",
        minimum_os_version="4.7",
        entrypoint="src.factories.analytics.analytics_collector",
        package_path="src/factories/analytics/",
        page_path="pages/23_Analytics_Factory.py",
        dashboard_widget=True,
        mission_control_widget=True,
        report_dir="reports/analytics",
        tags=["analytics", "kpi"],
        status="stable",
    ),
    make_manifest(
        module_name="自動化工場",
        module_type="factory",
        version="4.8",
        description="ルールベース工場間ワークフロー自動化。ドライランデフォルト。",
        module_id="automation-factory",
        display_name="Automation Factory",
        minimum_os_version="4.8",
        entrypoint="src.factories.automation.workflow_manager",
        package_path="src/factories/automation/",
        page_path="pages/24_Automation_Factory.py",
        dashboard_widget=True,
        mission_control_widget=True,
        config_files=["config/automation_workflows.json", "config/automation_runs.json"],
        report_dir="reports/automation",
        tags=["automation", "workflow"],
        status="stable",
    ),
    make_manifest(
        module_name="承認アシスタント",
        module_type="utility",
        version="4.4.1",
        description="Claude Codeの承認プロンプトをリスク分類するユーティリティ。",
        module_id="approval-assistant",
        display_name="Approval Assistant",
        minimum_os_version="4.4.1",
        entrypoint="src.devtools.approval_analyzer",
        package_path="src/devtools/",
        page_path="pages/20_Approval_Assistant.py",
        mission_control_widget=True,
        config_files=["config/approval_history.json"],
        tags=["devtools", "approval"],
        status="stable",
    ),
    make_manifest(
        module_name="Development Studio",
        module_type="development",
        version="5.0-beta",
        description="OS開発HQ。ロードマップ・リリース・決定ログ・ミーティングノート管理。",
        module_id="development-studio",
        display_name="Development Studio",
        minimum_os_version="5.0",
        entrypoint="src.devstudio.roadmap_manager",
        package_path="src/devstudio/",
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
        status="beta",
    ),
    make_manifest(
        module_name="AI CEO Core",
        module_type="executive",
        version="5.0-beta",
        description="エグゼクティブ決定レイヤー。健全度・優先度・リスク・推奨アクション。",
        module_id="ai-ceo-core",
        display_name="AI CEO Core",
        minimum_os_version="5.0",
        entrypoint="src.aiceo.executive_engine",
        package_path="src/aiceo/",
        page_path="pages/26_AI_CEO.py",
        dashboard_widget=True,
        mission_control_widget=True,
        config_files=["config/aiceo_settings.json", "config/aiceo_history.json"],
        report_dir="reports/aiceo",
        tags=["executive", "ai-ceo"],
        status="beta",
    ),
    make_manifest(
        module_name="Approval Center",
        module_type="utility",
        version="5.1",
        description="人間承認ゲートウェイ。AI CEO・自動化・開発Studio からのアクションをレビュー。",
        module_id="approval-center",
        display_name="Approval Center",
        minimum_os_version="5.1",
        entrypoint="src.approval.approval_queue",
        package_path="src/approval/",
        page_path="pages/27_Approval_Center.py",
        dashboard_widget=True,
        mission_control_widget=True,
        config_files=["config/approval_queue.json"],
        tags=["approval", "governance"],
        status="stable",
    ),
]
