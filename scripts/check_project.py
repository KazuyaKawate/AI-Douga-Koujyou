"""Project health check script for Creator Factory OS (AI動画工場 v5.1)."""
import io
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent.parent

REQUIRED_FOLDERS = [
    "assets",
    "assets/images",
    "assets/videos",
    "assets/voices",
    "config",
    "pages",
    "project",
    "reports",
    "reports/daily",
    "reports/monthly",
    "reports/analytics",
    "reports/automation",
    "reports/aiceo",
    "reports/devstudio",
    "src",
    "src/agents",
    "src/core",
    "src/factories",
    "src/factories/note",
    "src/factories/sns",
    "src/factories/sales",
    "src/factories/accounting",
    "src/factories/analytics",
    "src/factories/automation",
    "src/aiceo",
    "src/approval",
    "src/devstudio",
    "src/devtools",
    "src/sdk",
    "src/workspace",
    "reports/workspace",
    "src/hq",
    "src/utils",
    "src/pipeline",
    "src/providers",
    "src/director",
]

REQUIRED_FILES = [
    "app.py",
    "requirements.txt",
    # Pages
    "pages/1_Script.py",
    "pages/2_Subtitles.py",
    "pages/3_Assembly.py",
    "pages/4_Files.py",
    "pages/5_Episode.py",
    "pages/6_Produce.py",
    "pages/7_Assets.py",
    "pages/8_Dashboard.py",
    "pages/9_Settings.py",
    "pages/10_Characters.py",
    "pages/11_Backgrounds.py",
    "pages/12_Prompt_Builder.py",
    "pages/13_Production.py",
    "pages/14_Director.py",
    "pages/15_Project_Manager.py",
    "pages/16_AI_Studio.py",
    "pages/17_Mission_Control.py",
    "pages/18_Note_Factory.py",
    "pages/19_SNS_Factory.py",
    "pages/20_Approval_Assistant.py",
    "pages/21_Sales_Factory.py",
    "pages/22_Accounting_Factory.py",
    "pages/23_Analytics_Factory.py",
    "pages/24_Automation_Factory.py",
    "pages/25_Development_Studio.py",
    "pages/26_AI_CEO.py",
    "pages/27_Approval_Center.py",
    # Google Sheets Phase 3 credential safety
    "credentials/.gitkeep",
    # Workspace Sync (v5.2 Phase 1)
    "src/workspace/__init__.py",
    "src/workspace/sync_models.py",
    "src/workspace/sync_history.py",
    "src/workspace/sync_validator.py",
    "src/workspace/sheets_sync.py",
    "src/workspace/sync_engine.py",
    # Google Sheets Connector (v5.2 Phase 2)
    "src/workspace/google_auth.py",
    "src/workspace/sheet_reader.py",
    "src/workspace/sheet_writer.py",
    "src/workspace/sheet_diff.py",
    "src/workspace/sync_executor.py",
    # Module SDK (v5.1)
    "src/sdk/__init__.py",
    "src/sdk/module_manifest.py",
    "src/sdk/module_loader.py",
    "src/sdk/module_validator.py",
    "src/sdk/registry_builder.py",
    # Approval Center (v5.1)
    "src/approval/__init__.py",
    "src/approval/approval_models.py",
    "src/approval/approval_queue.py",
    "src/approval/risk_analyzer.py",
    "src/approval/command_preview.py",
    # AI CEO Core — Executive Module (v5.0-beta)
    "src/aiceo/__init__.py",
    "src/aiceo/executive_engine.py",
    "src/aiceo/executive_dashboard.py",
    "src/aiceo/priority_engine.py",
    "src/aiceo/kpi_engine.py",
    "src/aiceo/opportunity_engine.py",
    "src/aiceo/risk_engine.py",
    "src/aiceo/recommendation_engine.py",
    "src/aiceo/executive_report.py",
    # Dev Studio — OS Management
    "src/devstudio/__init__.py",
    "src/devstudio/roadmap_manager.py",
    "src/devstudio/release_manager.py",
    "src/devstudio/git_status_reader.py",
    "src/devstudio/healthcheck_reader.py",
    "src/devstudio/decision_log_manager.py",
    "src/devstudio/meeting_log_manager.py",
    "src/devstudio/spreadsheet_exporter.py",
    # Factories — 自動化工場
    "src/factories/automation/__init__.py",
    "src/factories/automation/automation_rules.py",
    "src/factories/automation/workflow_manager.py",
    "src/factories/automation/trigger_engine.py",
    "src/factories/automation/action_engine.py",
    "src/factories/automation/automation_runner.py",
    "src/factories/automation/automation_reporter.py",
    # Factories — アナリティクス工場
    "src/factories/analytics/__init__.py",
    "src/factories/analytics/analytics_collector.py",
    "src/factories/analytics/kpi_analyzer.py",
    "src/factories/analytics/factory_analyzer.py",
    "src/factories/analytics/project_analyzer.py",
    "src/factories/analytics/roi_analyzer.py",
    "src/factories/analytics/trend_reporter.py",
    # Factories — 会計監査工場
    "src/factories/accounting/__init__.py",
    "src/factories/accounting/revenue_manager.py",
    "src/factories/accounting/expense_manager.py",
    "src/factories/accounting/subscription_manager.py",
    "src/factories/accounting/roi_calculator.py",
    "src/factories/accounting/audit_checker.py",
    "src/factories/accounting/monthly_report.py",
    # Factories — 営業工場
    "src/factories/sales/__init__.py",
    "src/factories/sales/lead_manager.py",
    "src/factories/sales/deal_manager.py",
    "src/factories/sales/followup_manager.py",
    "src/factories/sales/proposal_tracker.py",
    "src/factories/sales/sales_forecast.py",
    # Dev Tools — 承認アシスタント
    "src/devtools/__init__.py",
    "src/devtools/risk_rules.py",
    "src/devtools/command_classifier.py",
    "src/devtools/approval_templates.py",
    "src/devtools/approval_analyzer.py",
    # Factories — SNS投稿工場
    "src/factories/sns/__init__.py",
    "src/factories/sns/sns_post_manager.py",
    "src/factories/sns/platform_formatter.py",
    "src/factories/sns/hashtag_generator.py",
    "src/factories/sns/sns_calendar.py",
    "src/factories/sns/sns_analytics_placeholder.py",
    # Factories — note投稿工場
    "src/factories/__init__.py",
    "src/factories/note/__init__.py",
    "src/factories/note/article_manager.py",
    "src/factories/note/article_scorer.py",
    "src/factories/note/revenue_tracker.py",
    "src/factories/note/repurpose_engine.py",
    "src/factories/note/integration_bridge.py",
    # Core — version (v5.1)
    "src/core/version.py",
    # Core — architecture layer (v4.5.1)
    "src/core/factory_base.py",
    "src/core/factory_interfaces.py",
    "src/core/factory_registry.py",
    "src/core/factory_events.py",
    "src/core/project_manager.py",
    "src/core/project_registry.py",
    # Core — AI pipeline (pre-v4.3)
    "src/core/openai_client.py",
    "src/core/whisper_client.py",
    "src/core/ffmpeg_utils.py",
    "src/core/ai_pipeline.py",
    "src/core/episode_manager.py",
    # Architecture docs
    "docs/google_sheets_setup.md",
    "docs/FACTORY_SPEC.md",
    "docs/PROJECT_SPEC.md",
    "docs/ARCHITECTURE_DECISIONS.md",
    # Utils
    "src/utils/config.py",
    "src/utils/settings_manager.py",
    "src/utils/file_manager.py",
    "src/utils/backup_manager.py",
    "src/utils/project_manager.py",
    "src/utils/character_manager.py",
    "src/utils/background_manager.py",
    "src/utils/prompt_builder.py",
    # Agents
    "src/agents/__init__.py",
    "src/agents/base_agent.py",
    "src/agents/agent_registry.py",
    "src/agents/producer_agent.py",
    "src/agents/director_agent.py",
    "src/agents/script_agent.py",
    "src/agents/prompt_agent.py",
    "src/agents/editor_agent.py",
    "src/agents/publisher_agent.py",
    # Pipeline
    "src/pipeline/__init__.py",
    "src/pipeline/script_pipeline.py",
    "src/pipeline/image_pipeline.py",
    "src/pipeline/video_pipeline.py",
    "src/pipeline/audio_pipeline.py",
    "src/pipeline/export_pipeline.py",
    # Providers
    "src/providers/__init__.py",
    "src/providers/openai_provider.py",
    "src/providers/image_provider_manual.py",
    "src/providers/video_provider_manual.py",
    "src/providers/audio_provider_manual.py",
    # Director
    "src/director/__init__.py",
    "src/director/director_schema.py",
    "src/director/director_planner.py",
    # HQ — Mission Control
    "src/hq/__init__.py",
    "src/hq/kpi_manager.py",
    "src/hq/task_manager.py",
    "src/hq/factory_status.py",
    "src/hq/daily_report.py",
]

OPTIONAL_FILES = [
    ".env",
    "config/settings.json",
    "config/characters.json",
    "config/backgrounds.json",
    "config/prompt_templates.json",
    "config/kpi_targets.json",
    "config/daily_tasks.json",
    "config/factory_status.json",
    "config/revenue_expense.json",
    "config/note_articles.json",
    "config/sns_posts.json",
    "config/sns_platforms.json",
    "config/sns_schedule.json",
    "config/approval_rules.json",
    "config/approval_history.json",
    "config/sales_leads.json",
    "config/sales_deals.json",
    "config/sales_followups.json",
    "config/sales_settings.json",
    "config/accounting_revenue.json",
    "config/accounting_expenses.json",
    "config/accounting_subscriptions.json",
    "config/accounting_settings.json",
    "config/projects.json",
    "config/factory_events.json",
    "config/analytics_settings.json",
    "config/analytics_snapshots.json",
    "config/automation_workflows.json",
    "config/automation_runs.json",
    "config/automation_settings.json",
    # AI CEO Core config (v5.0-beta)
    "config/aiceo_settings.json",
    "config/aiceo_history.json",
    # Dev Studio config (v5.0-beta)
    "config/devstudio_roadmap.json",
    "config/devstudio_releases.json",
    "config/devstudio_decisions.json",
    "config/devstudio_meetings.json",
    "config/devstudio_settings.json",
    # Workspace Sync config (v5.2)
    "config/workspace_settings.json",
    "config/sync_history.json",
    # Approval Center config (v5.1)
    "config/approval_queue.json",
    # Module SDK registry export (v5.1 Phase 2)
    "config/module_registry.json",
]


def check() -> bool:
    ok = True
    width = 60

    try:
        import sys as _sv; _sv.path.insert(0, str(ROOT))
        from src.core.version import OS_VERSION as _V, OS_CODENAME as _C
        _title = f"Creator Factory OS v{_V} — {_C}"
    except Exception:
        _title = "Creator Factory OS v5.1 — Project Health Check"
    print("=" * width)
    print(f"  {_title}")
    print("=" * width)
    print(f"  Root: {ROOT}\n")

    # Folders
    print("[ フォルダ ]")
    for rel in REQUIRED_FOLDERS:
        p = ROOT / rel
        status = "OK  " if p.is_dir() else "MISS"
        if not p.is_dir():
            ok = False
        print(f"  [{status}] {rel}")

    print()

    # Required files
    print("[ 必須ファイル ]")
    for rel in REQUIRED_FILES:
        p = ROOT / rel
        if p.exists():
            kb = p.stat().st_size / 1024
            print(f"  [OK  ] {rel}  ({kb:.1f} KB)")
        else:
            print(f"  [MISS] {rel}")
            ok = False

    print()

    # Optional
    print("[ オプション ]")
    for rel in OPTIONAL_FILES:
        p = ROOT / rel
        if p.exists():
            print(f"  [OK  ] {rel}")
        else:
            print(f"  [----] {rel}  (未作成)")

    print()

    # Config JSON check
    print("[ 設定ファイル ]")
    import json
    for cfg_name, key in [
        ("config/settings.json",         None),
        ("config/characters.json",        "characters"),
        ("config/backgrounds.json",       "backgrounds"),
        ("config/prompt_templates.json",  "templates"),
    ]:
        p = ROOT / cfg_name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if key:
                    count = len(data.get(key, []))
                    print(f"  [OK  ] {cfg_name}  ({count} {key})")
                else:
                    print(f"  [OK  ] {cfg_name}")
            except Exception as exc:
                print(f"  [ERR ] {cfg_name}  → JSONパースエラー: {exc}")
                ok = False
        else:
            print(f"  [----] {cfg_name}  (未作成)")

    print()

    # Mission Control daily config
    print("[ Mission Control 設定ファイル ]")
    mc_configs = [
        ("config/kpi_targets.json",    "date"),
        ("config/daily_tasks.json",    "tasks"),
        ("config/factory_status.json", None),
        ("config/revenue_expense.json", None),
    ]
    for cfg_name, key in mc_configs:
        p = ROOT / cfg_name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if key:
                    count = len(data.get(key, [])) if isinstance(data.get(key), list) else data.get(key, "—")
                    print(f"  [OK  ] {cfg_name}  ({key}: {count})")
                else:
                    print(f"  [OK  ] {cfg_name}")
            except Exception as exc:
                print(f"  [ERR ] {cfg_name}  → JSONパースエラー: {exc}")
                ok = False
        else:
            print(f"  [----] {cfg_name}  (未作成)")

    print()

    # Analytics Factory (v4.7)
    print("[ Analytics Factory データ ]")
    _anl_cfgs = [
        ("config/analytics_settings.json",  "meta"),
        ("config/analytics_snapshots.json", "snapshots"),
    ]
    for cfg_name, key in _anl_cfgs:
        p = ROOT / cfg_name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if key == "snapshots":
                    print(f"  [OK  ] {cfg_name}  ({len(data.get(key, []))} スナップショット)")
                else:
                    print(f"  [OK  ] {cfg_name}  (v{data.get('meta', {}).get('version', '?')})")
            except Exception as exc:
                print(f"  [ERR ] {cfg_name}  → JSONパースエラー: {exc}")
                ok = False
        else:
            print(f"  [----] {cfg_name}  (未作成)")
    anl_reports_dir = ROOT / "reports" / "analytics"
    if anl_reports_dir.exists():
        anl_rpts = list(anl_reports_dir.glob("*_analytics_report.md"))
        print(f"  [OK  ] reports/analytics/  ({len(anl_rpts)} レポート)")
    else:
        print("  [----] reports/analytics/  (未作成)")

    print()

    # Automation Factory (v4.8)
    print("[ Automation Factory データ ]")
    _auto_cfgs = [
        ("config/automation_workflows.json", "workflows"),
        ("config/automation_runs.json",      "runs"),
        ("config/automation_settings.json",  "meta"),
    ]
    for cfg_name, key in _auto_cfgs:
        p = ROOT / cfg_name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if key in ("workflows", "runs"):
                    print(f"  [OK  ] {cfg_name}  ({len(data.get(key, []))} 件)")
                else:
                    print(f"  [OK  ] {cfg_name}  (dry_run_default={data.get('dry_run_default', True)})")
            except Exception as exc:
                print(f"  [ERR ] {cfg_name}  → JSONパースエラー: {exc}")
                ok = False
        else:
            print(f"  [----] {cfg_name}  (未作成)")
    auto_reports_dir = ROOT / "reports" / "automation"
    if auto_reports_dir.exists():
        auto_rpts = list(auto_reports_dir.glob("*_automation_report.md"))
        print(f"  [OK  ] reports/automation/  ({len(auto_rpts)} レポート)")
    else:
        print("  [----] reports/automation/  (未作成)")

    print()

    # AI CEO Core (v5.0-beta)
    print("[ AI CEO Core データ ]")
    _ceo_cfgs = [
        ("config/aiceo_settings.json", None),
        ("config/aiceo_history.json",  "history"),
    ]
    for cfg_name, key in _ceo_cfgs:
        p = ROOT / cfg_name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if key and key in data:
                    print(f"  [OK  ] {cfg_name}  ({len(data[key])} {key})")
                else:
                    print(f"  [OK  ] {cfg_name}")
            except Exception as exc:
                print(f"  [ERR ] {cfg_name}  → JSONパースエラー: {exc}")
                ok = False
        else:
            print(f"  [----] {cfg_name}  (未作成)")
    ceo_reports_dir = ROOT / "reports" / "aiceo"
    if ceo_reports_dir.exists():
        ceo_rpts = list(ceo_reports_dir.glob("*_executive_report.md"))
        print(f"  [OK  ] reports/aiceo/  ({len(ceo_rpts)} レポート)")
    else:
        print("  [----] reports/aiceo/  (未作成)")

    print()

    # Development Studio (v5.0-beta)
    print("[ Development Studio データ ]")
    _ds_cfgs = [
        ("config/devstudio_roadmap.json",   "roadmap"),
        ("config/devstudio_releases.json",  "releases"),
        ("config/devstudio_decisions.json", "decisions"),
        ("config/devstudio_meetings.json",  "meetings"),
        ("config/devstudio_settings.json",  None),
    ]
    for cfg_name, key in _ds_cfgs:
        p = ROOT / cfg_name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if key and key in data:
                    print(f"  [OK  ] {cfg_name}  ({len(data[key])} {key})")
                else:
                    print(f"  [OK  ] {cfg_name}")
            except Exception as exc:
                print(f"  [ERR ] {cfg_name}  → JSONパースエラー: {exc}")
                ok = False
        else:
            print(f"  [----] {cfg_name}  (未作成)")
    ds_reports_dir = ROOT / "reports" / "devstudio"
    if ds_reports_dir.exists():
        ds_csvs = list(ds_reports_dir.glob("*.csv"))
        print(f"  [OK  ] reports/devstudio/  ({len(ds_csvs)} CSVファイル)")
    else:
        print("  [----] reports/devstudio/  (未作成)")

    print()

    # Module SDK + Approval Center (v5.1 Phase 2)
    print("[ Module SDK データ ]")
    reg_path = ROOT / "config" / "module_registry.json"
    if reg_path.exists():
        try:
            reg_data = json.loads(reg_path.read_text(encoding="utf-8"))
            _meta = reg_data.get("meta", {})
            _mods = reg_data.get("modules", [])
            print(
                f"  [OK  ] config/module_registry.json  "
                f"({len(_mods)} モジュール, SDK v{_meta.get('sdk_version', '?')}, "
                f"生成: {_meta.get('generated_at', '?')[:10]})"
            )
        except Exception as exc:
            print(f"  [ERR ] config/module_registry.json  → JSONパースエラー: {exc}")
            ok = False
    else:
        print("  [----] config/module_registry.json  (未生成 — Development Studio SDK タブで生成)")
    try:
        import sys as _sys2
        _sys2.path.insert(0, str(ROOT))
        from src.sdk.registry_builder import ModuleRegistry as _MR
        from src.sdk.module_manifest import SDK_VERSION as _SDK_VER
        _mr_sum = _MR.get_summary()
        _vr = _MR.get_validation_report()
        print(
            f"  [OK  ] ModuleRegistry  "
            f"(SDK v{_SDK_VER}: {_mr_sum['total']} モジュール, "
            f"{_mr_sum['valid']} valid, {_mr_sum['invalid']} invalid, "
            f"{_mr_sum['factories']} 工場)"
        )
        if _mr_sum["invalid"] > 0:
            for r in _vr["results"]:
                if not r["valid"]:
                    for e in r["errors"]:
                        print(f"  [WARN] {r['module_name']}: {e}")
    except Exception as exc:
        print(f"  [----] ModuleRegistry  → {exc}")

    print()

    print("[ Approval Center データ ]")
    approval_queue_path = ROOT / "config" / "approval_queue.json"
    if approval_queue_path.exists():
        try:
            data = json.loads(approval_queue_path.read_text(encoding="utf-8"))
            pending_count = len(data.get("pending", []))
            history_count = len(data.get("history", []))
            print(f"  [OK  ] config/approval_queue.json  (pending: {pending_count}, history: {history_count})")
        except Exception as exc:
            print(f"  [ERR ] config/approval_queue.json  → JSONパースエラー: {exc}")
            ok = False
    else:
        print("  [----] config/approval_queue.json  (未作成)")

    print()

    # Core Architecture (v4.5.1)
    print("[ Core Architecture ]")
    _core_cfgs = [
        ("config/projects.json",       "projects"),
        ("config/factory_events.json", "events"),
    ]
    for cfg_name, key in _core_cfgs:
        p = ROOT / cfg_name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                count = len(data.get(key, []))
                print(f"  [OK  ] {cfg_name}  ({count} {key})")
            except Exception as exc:
                print(f"  [ERR ] {cfg_name}  → JSONパースエラー: {exc}")
                ok = False
        else:
            print(f"  [----] {cfg_name}  (未作成)")
    try:
        import sys as _sys
        _sys.path.insert(0, str(ROOT))
        from src.core.factory_registry import FactoryRegistry
        _summary = FactoryRegistry.get_summary()
        print(f"  [OK  ] FactoryRegistry  ({_summary['total']} 工場, {_summary['healthy']} 正常)")
        from src.core.project_manager import get_all_projects
        _projs = get_all_projects()
        print(f"  [OK  ] ProjectRegistry  ({len(_projs)} プロジェクト)")
    except Exception as exc:
        print(f"  [ERR ] Core Architecture  → {exc}")
        ok = False

    print()

    # Accounting Factory
    print("[ Accounting Factory データ ]")
    acc_files = [
        ("config/accounting_revenue.json",       "revenue"),
        ("config/accounting_expenses.json",       "expenses"),
        ("config/accounting_subscriptions.json",  "subscriptions"),
        ("config/accounting_settings.json",       None),
    ]
    for cfg_name, key in acc_files:
        p = ROOT / cfg_name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if key and key in data:
                    print(f"  [OK  ] {cfg_name}  ({len(data[key])} {key})")
                elif "break_even_monthly" in data:
                    print(f"  [OK  ] {cfg_name}  (損益分岐点: ¥{data['break_even_monthly']:,})")
                else:
                    print(f"  [OK  ] {cfg_name}")
            except Exception as exc:
                print(f"  [ERR ] {cfg_name}  → JSONパースエラー: {exc}")
                ok = False
        else:
            print(f"  [----] {cfg_name}  (未作成)")
    acc_reports_dir = ROOT / "reports" / "monthly"
    if acc_reports_dir.exists():
        acc_rpts = list(acc_reports_dir.glob("*_accounting_report.md"))
        print(f"  [OK  ] reports/monthly/  ({len(acc_rpts)} レポート)")
    else:
        print("  [----] reports/monthly/  (未作成)")

    print()

    # Sales Factory
    print("[ Sales Factory データ ]")
    sales_files = [
        ("config/sales_leads.json",    "leads"),
        ("config/sales_deals.json",    "deals"),
        ("config/sales_followups.json", "followups"),
        ("config/sales_settings.json",  None),
    ]
    for cfg_name, key in sales_files:
        p = ROOT / cfg_name
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if key and key in data:
                    print(f"  [OK  ] {cfg_name}  ({len(data[key])} {key})")
                elif "monthly_target" in data:
                    print(f"  [OK  ] {cfg_name}  (目標: ¥{data['monthly_target']:,})")
                else:
                    print(f"  [OK  ] {cfg_name}")
            except Exception as exc:
                print(f"  [ERR ] {cfg_name}  → JSONパースエラー: {exc}")
                ok = False
        else:
            print(f"  [----] {cfg_name}  (未作成)")

    print()

    # Approval Assistant
    print("[ Approval Assistant データ ]")
    approval_rules_path = ROOT / "config" / "approval_rules.json"
    approval_history_path = ROOT / "config" / "approval_history.json"
    for cfg_ap in [approval_rules_path, approval_history_path]:
        rel_ap = str(cfg_ap.relative_to(ROOT)).replace("\\", "/")
        if cfg_ap.exists():
            try:
                data = json.loads(cfg_ap.read_text(encoding="utf-8"))
                if "history" in data:
                    print(f"  [OK  ] {rel_ap}  ({len(data['history'])} 件の履歴)")
                elif "stop_keywords" in data:
                    print(f"  [OK  ] {rel_ap}  (v{data.get('version','?')})")
                else:
                    print(f"  [OK  ] {rel_ap}")
            except Exception as exc:
                print(f"  [ERR ] {rel_ap}  → JSONパースエラー: {exc}")
                ok = False
        else:
            print(f"  [----] {rel_ap}  (未作成)")

    print()

    # SNS Factory posts
    print("[ SNS Factory 投稿データ ]")
    sns_posts_path = ROOT / "config" / "sns_posts.json"
    sns_plat_path  = ROOT / "config" / "sns_platforms.json"
    sns_sched_path = ROOT / "config" / "sns_schedule.json"
    for cfg_sns in [sns_posts_path, sns_plat_path, sns_sched_path]:
        rel_sns = str(cfg_sns.relative_to(ROOT)).replace("\\", "/")
        if cfg_sns.exists():
            try:
                data = json.loads(cfg_sns.read_text(encoding="utf-8"))
                if "posts" in data:
                    pub = sum(1 for p in data["posts"] if p.get("status") == "published")
                    print(f"  [OK  ] {rel_sns}  ({len(data['posts'])} 投稿, {pub} 公開済)")
                elif "platforms" in data:
                    print(f"  [OK  ] {rel_sns}  ({len(data['platforms'])} プラットフォーム)")
                else:
                    print(f"  [OK  ] {rel_sns}")
            except Exception as exc:
                print(f"  [ERR ] {rel_sns}  → JSONパースエラー: {exc}")
                ok = False
        else:
            print(f"  [----] {rel_sns}  (未作成)")

    print()

    # Note Factory articles
    print("[ Note Factory 記事データ ]")
    note_articles_path = ROOT / "config" / "note_articles.json"
    if note_articles_path.exists():
        try:
            data = json.loads(note_articles_path.read_text(encoding="utf-8"))
            arts = data.get("articles", [])
            published = sum(1 for a in arts if a.get("status") == "published")
            print(f"  [OK  ] config/note_articles.json  ({len(arts)} 記事, {published} 公開済)")
        except Exception as exc:
            print(f"  [ERR ] config/note_articles.json  → JSONパースエラー: {exc}")
            ok = False
    else:
        print(f"  [----] config/note_articles.json  (未作成)")

    print()

    # Workspace Sync (v5.2)
    print("[ Workspace Sync データ ]")
    _ws_settings_path = ROOT / "config" / "workspace_settings.json"
    _ws_history_path  = ROOT / "config" / "sync_history.json"
    if _ws_settings_path.exists():
        try:
            _ws_cfg = json.loads(_ws_settings_path.read_text(encoding="utf-8"))
            _ws_targets = _ws_cfg.get("sync_targets", [])
            _ws_enabled = sum(1 for t in _ws_targets if t.get("enabled", True))
            _ws_dry = _ws_cfg.get("dry_run_default", True)
            _ws_auth_mode = _ws_cfg.get("connector", {}).get("auth_mode", "disabled")
            print(
                f"  [OK  ] config/workspace_settings.json  "
                f"({len(_ws_targets)} ターゲット, {_ws_enabled} 有効, "
                f"dry_run={_ws_dry}, enabled={_ws_cfg.get('enabled', False)}, "
                f"auth_mode={_ws_auth_mode})"
            )
            if _ws_auth_mode != "disabled":
                print(f"  [WARN] auth_mode={_ws_auth_mode}  認証ファイルをコミットしないでください。")
            else:
                print("  [OK  ] auth_mode=disabled (デフォルト: 安全)")
        except Exception as exc:
            print(f"  [ERR ] config/workspace_settings.json  → {exc}")
            ok = False
    else:
        print("  [----] config/workspace_settings.json  (未作成)")
    if _ws_history_path.exists():
        try:
            _ws_hist = json.loads(_ws_history_path.read_text(encoding="utf-8"))
            _ws_hist_count = len(_ws_hist.get("history", []))
            print(f"  [OK  ] config/sync_history.json  ({_ws_hist_count} 同期履歴)")
        except Exception as exc:
            print(f"  [ERR ] config/sync_history.json  → {exc}")
            ok = False
    else:
        print("  [----] config/sync_history.json  (未作成)")
    try:
        import sys as _sys3
        _sys3.path.insert(0, str(ROOT))
        from src.workspace.sync_validator import get_connection_status as _ws_status
        from src.workspace.sync_engine import get_sync_health as _ws_hlth
        _wst = _ws_status()
        _wsh = _ws_hlth()
        print(
            f"  [OK  ] WorkspaceSync  "
            f"({_wst['icon']} {_wst['label']}, "
            f"sync_total={_wsh['total_syncs']}, "
            f"conflicts={_wsh['total_conflicts']})"
        )
    except Exception as exc:
        print(f"  [----] WorkspaceSync  → {exc}")
    _ws_reports_dir = ROOT / "reports" / "workspace"
    if _ws_reports_dir.exists():
        _ws_rpts = list(_ws_reports_dir.glob("*.md")) + list(_ws_reports_dir.glob("*.json"))
        print(f"  [OK  ] reports/workspace/  ({len(_ws_rpts)} ファイル)")
    else:
        print("  [----] reports/workspace/  (未作成)")

    print()

    # Google Sheets Connector (v5.2 Phase 2)
    print("[ Google Sheets Connector (v5.2 Phase 2) ]")
    _connector_modules = [
        "src/workspace/google_auth.py",
        "src/workspace/sheet_reader.py",
        "src/workspace/sheet_writer.py",
        "src/workspace/sheet_diff.py",
        "src/workspace/sync_executor.py",
    ]
    for _cm in _connector_modules:
        _cp = ROOT / _cm
        if _cp.exists():
            print(f"  [OK  ] {_cm}  ({_cp.stat().st_size / 1024:.1f} KB)")
        else:
            print(f"  [MISS] {_cm}")
            ok = False

    # Validate no credential files are committed
    _cred_names = (
        "google_credentials.json", "service_account.json",
        "credentials.json", "client_secret.json",
        "oauth_client.json", "token.json",
    )
    _cred_found = False
    for _cn in _cred_names:
        for _cp2 in (ROOT / _cn, ROOT / "config" / _cn):
            if _cp2.exists():
                print(f"  [WARN] 認証ファイルが検出されました: {_cp2.relative_to(ROOT)}"
                      "  → .gitignore に追加してください。")
                _cred_found = True
    if not _cred_found:
        print("  [OK  ] 認証ファイルなし（安全）")

    # Validate auth_mode defaults to disabled
    try:
        import sys as _sys4
        _sys4.path.insert(0, str(ROOT))
        from src.workspace.google_auth import get_auth_config as _ga_cfg
        _ac = _ga_cfg()
        if _ac["auth_mode"] == "disabled":
            print(f"  [OK  ] auth_mode=disabled (デフォルト設定確認)")
        else:
            print(f"  [WARN] auth_mode={_ac['auth_mode']}  デフォルトは 'disabled' 推奨")
    except Exception as exc:
        print(f"  [----] google_auth.get_auth_config  → {exc}")

    # Validate sync_executor imports correctly
    try:
        import sys as _sys5
        _sys5.path.insert(0, str(ROOT))
        from src.workspace.sync_executor import run_preview as _se_prev, get_connector_health as _se_hlth
        _seh = _se_hlth()
        print(
            f"  [OK  ] sync_executor  "
            f"(auth_mode={_seh['auth_mode']}, "
            f"targets={_seh['target_count']}, "
            f"phase={_seh['phase']})"
        )
    except Exception as exc:
        print(f"  [ERR ] sync_executor  → {exc}")
        ok = False

    # py_compile all connector modules
    import py_compile as _pyc
    for _cm2 in _connector_modules:
        _cp3 = ROOT / _cm2
        if _cp3.exists():
            try:
                _pyc.compile(str(_cp3), doraise=True)
                print(f"  [OK  ] py_compile: {_cm2}")
            except _pyc.PyCompileError as exc:
                print(f"  [ERR ] py_compile: {_cm2}  → {exc}")
                ok = False

    print()

    # Google Sheets Phase 3 Safety & gspread Readiness
    print("[ Google Sheets Phase 3 安全性 & gspread 準備状況 ]")

    # credentials/.gitkeep
    _creds_dir  = ROOT / "credentials"
    _gitkeep    = _creds_dir / ".gitkeep"
    if not _creds_dir.exists():
        print("  [MISS] credentials/  → フォルダが存在しません")
        ok = False
    elif not _gitkeep.exists():
        print("  [MISS] credentials/.gitkeep  → .gitkeep が存在しません")
        ok = False
    else:
        _real_jsons = list(_creds_dir.glob("*.json"))
        if _real_jsons:
            for _rj in _real_jsons:
                print(f"  [WARN] credentials/{_rj.name}  → 認証JSONが検出されました。コミットしないでください。")
        else:
            print("  [OK  ] credentials/.gitkeep（実JSONなし — 安全）")

    # docs/google_sheets_setup.md
    _gss_doc = ROOT / "docs" / "google_sheets_setup.md"
    if _gss_doc.exists():
        print(f"  [OK  ] docs/google_sheets_setup.md  ({_gss_doc.stat().st_size / 1024:.1f} KB)")
    else:
        print("  [----] docs/google_sheets_setup.md  (未作成)")

    # .gitignore credential protections
    _gi_path = ROOT / ".gitignore"
    _gi_required = ("credentials/", ".gitkeep", "service_account", "token.json")
    if not _gi_path.exists():
        print("  [MISS] .gitignore  → 存在しません")
        ok = False
    else:
        _gi_content = _gi_path.read_text(encoding="utf-8", errors="replace")
        _gi_missing = [p for p in _gi_required if p not in _gi_content]
        if _gi_missing:
            print(f"  [WARN] .gitignore  → 次のパターンが見つかりません: {', '.join(_gi_missing)}")
        else:
            print("  [OK  ] .gitignore 認証保護パターン（credentials/, service_account, token.json）")

    # gspread / google-auth
    import importlib.metadata as _imd
    def _pkg_ver(pkg: str) -> tuple[bool, str]:
        try:
            return True, _imd.version(pkg)
        except Exception:
            return False, ""
    _gs_ok, _gs_ver = _pkg_ver("gspread")
    _ga_ok, _ga_ver = _pkg_ver("google-auth")
    if _gs_ok and _ga_ok:
        print(f"  [OK  ] gspread {_gs_ver} / google-auth {_ga_ver}  (Phase 4+ で使用)")
    else:
        _missing_pkgs = [p for p, ok2 in [("gspread", _gs_ok), ("google-auth", _ga_ok)] if not ok2]
        print(f"  [----] gspread/google-auth 未インストール: {', '.join(_missing_pkgs)}"
              "  → pip install gspread google-auth  (Phase 4+ まで不要)")

    # Phase 3 composite readiness via sync_validator
    try:
        import sys as _sys6
        _sys6.path.insert(0, str(ROOT))
        from src.workspace.sync_validator import get_phase3_readiness as _p3r
        _p3 = _p3r()
        _p3_ok = _p3["ready"]
        _p3_total = len(_p3["checks"])
        _p3_pass  = sum(1 for c in _p3["checks"] if c["ok"])
        _p3_label = "安全" if _p3_ok else "要確認"
        print(
            f"  [{'OK  ' if _p3_ok else 'WARN'}] Phase 3 Readiness  "
            f"({_p3_pass}/{_p3_total} チェック通過, {_p3_label})"
        )
        if not _p3_ok:
            for _blk in _p3.get("blockers", []):
                print(f"  [WARN]   → {_blk[:80]}")
    except Exception as exc:
        print(f"  [----] Phase 3 Readiness  → {exc}")

    print()

    # Reports folder
    print("[ レポートフォルダ ]")
    reports_dir = ROOT / "reports" / "daily"
    if reports_dir.exists():
        report_count = len(list(reports_dir.glob("*.md")))
        print(f"  [OK  ] reports/daily/  ({report_count} レポート)")
    else:
        print(f"  [----] reports/daily/  (未作成)")

    print()

    # Episode count
    print("[ エピソード ]")
    project_dir = ROOT / "project"
    if project_dir.exists():
        eps = [d for d in project_dir.iterdir() if d.is_dir() and (d / "episode.json").exists()]
        with_director = [e for e in eps if (e / "director_plan.json").exists()]
        with_export   = [e for e in eps if (e / "export" / "production_report.json").exists()]
        print(f"  エピソード総数: {len(eps)}")
        print(f"  演出計画あり:   {len(with_director)}")
        print(f"  書き出し済み:   {len(with_export)}")
    else:
        print("  project/ フォルダが存在しません")

    print()
    print("=" * width)
    if ok:
        print("  STATUS: OK — すべての必須ファイルが揃っています ✅")
    else:
        print("  STATUS: NG — 不足ファイルがあります ❌")
    print("=" * width)
    return ok


if __name__ == "__main__":
    success = check()
    sys.exit(0 if success else 1)
