"""Project health check script for Creator Factory OS (AI動画工場 v4.8)."""
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
    "src/devtools",
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
]


def check() -> bool:
    ok = True
    width = 60

    print("=" * width)
    print("  Creator Factory OS v4.8 — Project Health Check")
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
