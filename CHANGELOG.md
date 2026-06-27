# Changelog — Creator Factory OS (旧: AI動画工場)

All notable changes to this project are documented in this file.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versions are cumulative; each release builds on the previous stable base.

---

## [v5.1 Phase 1] — 2026-06-27 — Module SDK + Approval Center

**Codename:** Module SDK + Approval Center Foundation  
**Upgrade path:** v5.0-beta Phase 2 (AI CEO Core) → v5.1 Phase 1 (additive, no breaking changes)

### Added
- `pages/27_Approval_Center.py` — 5-tab human-approval gateway (Pending / Approved / Rejected / New Request / Summary)
- `src/approval/__init__.py` — package marker; module_type = "utility"
- `src/approval/approval_models.py` — ApprovalItem data model, status/risk/source constants, `make_item()`
- `src/approval/approval_queue.py` — queue CRUD over `config/approval_queue.json`; approve/reject/expire/delete; never executes
- `src/approval/risk_analyzer.py` — rule-based risk analysis for pending items (high/medium/low/none)
- `src/approval/command_preview.py` — human-readable action previews; `preview_action()`, `get_short_summary()`
- `src/sdk/__init__.py` — Module SDK package marker; version = "5.1"
- `src/sdk/module_manifest.py` — `ModuleInfo` TypedDict + `make_manifest()` helper + `BUILTIN_MANIFESTS` for all 11 modules
- `src/sdk/module_loader.py` — manifest discovery (built-ins + dynamic import scan); backward compatible
- `src/sdk/module_validator.py` — `validate_manifest()`, `validate_all()` with error reporting
- `src/sdk/registry_builder.py` — `ModuleRegistry` class: `get_all()`, `get_by_type()`, `get_summary()`
- `config/approval_queue.json` — approval queue store (pending + history)

### Changed
- `pages/17_Mission_Control.py` — Section 7.13 Approval Center card (pending, high-risk, approved, rejected counts)
- `pages/8_Dashboard.py` — Approval Center summary strip (4 metrics + page link)
- `app.py` — Approval Center added to WORKFLOW list with pending count metric
- `scripts/check_project.py` — v5.1 title; added `src/sdk/`, `src/approval/`, `pages/27` to required lists; Module SDK + Approval Center data sections

### Design decisions
- Approval Center is display-only: "Approve" button updates queue JSON only, never executes commands
- Live Inbox aggregates AI CEO recommendations + disabled Automation workflows + open DevStudio decisions
- Module SDK built-ins cover all 11 current modules; future modules can export MODULE_MANIFEST from __init__.py
- `src/approval/` excluded from FactoryRegistry (module_type = "utility")
- `src/sdk/` excluded from FactoryRegistry (no factory behavior)

---

## [v5.0-beta Phase 2] — 2026-06-27 — AI CEO Core

**Codename:** AI CEO Core  
**Upgrade path:** v5.0-beta (Development Studio) → Phase 2 (additive, no breaking changes)

### Added
- `pages/26_AI_CEO.py` — 7-tab executive layer (CEO Daily Brief / KPI Summary / Priorities / Opportunities / Risks / Recommendations / Executive Report)
- `src/aiceo/__init__.py` — package marker; module_type = "executive"
- `src/aiceo/executive_engine.py` — read-only OS snapshot collector across all factories
- `src/aiceo/executive_dashboard.py` — overall health score (0-100), CEO brief generator
- `src/aiceo/priority_engine.py` — Top 10 priorities scored by Impact(40%)+Urgency(30%)+ROI(20%)+Dependencies(10%)
- `src/aiceo/kpi_engine.py` — KPI achievement analysis with per-metric status and alerts
- `src/aiceo/opportunity_engine.py` — identifies ROI, unused factory, automation, content opportunities
- `src/aiceo/risk_engine.py` — identifies revenue, factory, roadmap, KPI, project delay risks
- `src/aiceo/recommendation_engine.py` — generates up to 10 recommendations (reason/impact/confidence/factory/action); never executes
- `src/aiceo/executive_report.py` — full Markdown executive report; export to `reports/aiceo/`
- `config/aiceo_settings.json` — AI CEO module settings
- `config/aiceo_history.json` — analysis history store
- `reports/aiceo/` — executive report export directory

### Changed
- `pages/17_Mission_Control.py` — Section 7.12 AI CEO card (health score, high risks, KPI avg)
- `pages/8_Dashboard.py` — AI CEO Executive Summary strip at top (6 metrics)
- `app.py` — AI CEO in WORKFLOW with OS health score as count
- `scripts/check_project.py` — `src/aiceo/` folder, 9 aiceo files, 2 aiceo config files, `reports/aiceo/`

### Architecture
- AI CEO is an **Executive Module**, NOT a Factory. Not registered in FactoryRegistry.
- Strictly read-only — executive_engine.py never writes to any data store
- No external API calls — all analysis is rule-based
- No automatic execution — recommendations are text only
- All engines degrade gracefully when factory data is unavailable
- `@st.cache_data(ttl=60)` applied to snapshot collection for performance

---

## [v5.0-beta] — 2026-06-27 — Development Studio

**Codename:** Development Studio  
**Upgrade path:** v4.8 → v5.0-beta (additive, no breaking changes)

### Added
- `pages/25_Development_Studio.py` — 8-tab OS development HQ page (Overview / Roadmap / Releases / Decision Log / Meeting Notes / Health Check / Git Status / Spreadsheet Export)
- `src/devstudio/__init__.py` — package marker
- `src/devstudio/roadmap_manager.py` — roadmap CRUD (planned/in_progress/completed/blocked/archived)
- `src/devstudio/release_manager.py` — release record CRUD with health status tracking
- `src/devstudio/decision_log_manager.py` — decision log CRUD (open/accepted/rejected/superseded)
- `src/devstudio/meeting_log_manager.py` — meeting notes CRUD
- `src/devstudio/git_status_reader.py` — read-only git status (branch, latest commit, dirty/clean)
- `src/devstudio/healthcheck_reader.py` — run-on-demand health check via scripts/check_project.py
- `src/devstudio/spreadsheet_exporter.py` — CSV export to `reports/devstudio/`
- `config/devstudio_roadmap.json` — roadmap data store
- `config/devstudio_releases.json` — release record store
- `config/devstudio_decisions.json` — decision log store
- `config/devstudio_meetings.json` — meeting notes store
- `config/devstudio_settings.json` — Dev Studio settings
- `reports/devstudio/` — CSV export directory

### Changed
- `pages/17_Mission_Control.py` — Section 7.11 Development Studio card (roadmap count, in-progress, open decisions, meetings)
- `pages/8_Dashboard.py` — Development Studio summary strip (roadmap / in-progress / completed / open decisions)
- `app.py` — v5.0-beta; Development Studio in WORKFLOW with in-progress count
- `scripts/check_project.py` — v5.0-beta; `src/devstudio/` folder, 8 devstudio files, 5 devstudio config files, `reports/devstudio/` folder

### Architecture
- Development Studio is an **OS Management** module, NOT a Factory. Not registered in FactoryRegistry.
- All data stored as local JSON files under `config/devstudio_*.json`
- Git status reader is strictly read-only — no write operations
- Health check runs only on explicit user button click — never automatic
- CSV export writes to `reports/devstudio/` — compatible with spreadsheet management ledger

---

## [v4.8] — 2026-06-27 — Automation Factory

**Codename:** Automation Factory
**Upgrade path:** v4.7 → v4.8 (additive, no breaking changes)

### Added
- `src/factories/automation/__init__.py` — package marker
- `src/factories/automation/automation_rules.py` — 6 trigger types, 6 action types, 5 built-in workflow templates
- `src/factories/automation/workflow_manager.py` — workflow CRUD, enable/disable, run counter
- `src/factories/automation/trigger_engine.py` — read-only trigger evaluation (status_changed, kpi_below_target, new_item_created, revenue_recorded, warning_detected, manual_run)
- `src/factories/automation/action_engine.py` — draft-only action execution; 6 action types; dry_run=True gating
- `src/factories/automation/automation_runner.py` — orchestrates trigger→action→log per workflow
- `src/factories/automation/automation_reporter.py` — run log (max 200), report generation, Markdown export
- `pages/24_Automation_Factory.py` — 6-tab UI: Dashboard / Workflows / Templates / Run Log / Report / Settings
- `config/automation_workflows.json` — workflow store (seeded from templates on first load)
- `config/automation_runs.json` — run history (max 200 entries)
- `config/automation_settings.json` — dry_run_default: true, max_runs: 200
- `reports/automation/` — automation report export folder

### Changed
- `src/core/factory_registry.py` — added 自動化工場 to FACTORY_CATALOG (v4.8, 2 config files, 5 dependencies)
- `src/core/factory_interfaces.py` — added 自動化工場 → ⚙️ to FACTORY_ICONS
- `config/projects.json` — added 自動化工場 to default project factories list
- `pages/17_Mission_Control.py` — v4.8; Section 7.10 Automation Factory card (workflow count, enabled, run count, success count)
- `pages/8_Dashboard.py` — v4.8; Automation Factory summary strip at top (6 metrics)
- `app.py` — v4.8; 自動化工場 in WORKFLOW with enabled workflow count
- `scripts/check_project.py` — v4.8; `reports/automation/` folder, 7 automation files, 3 automation config files, Automation data section

### Architecture
- All automation actions are draft-only — no auto-publishing, no auto-confirmation
- Dry-run mode (`dry_run=True`) is default at every level: settings, runner, action engine
- All items created by automation are marked `_automation_source: true` for auditability
- Trigger evaluation is READ-ONLY — no writes in trigger_engine.py
- Lazy imports inside all cross-factory function calls to prevent circular imports
- Run history capped at 200 entries in automation_runs.json

---

## [v4.7] — 2026-06-27 — Analytics Factory

**Codename:** Analytics Factory
**Upgrade path:** v4.5.1 → v4.7 (additive, no breaking changes)

### Added
- `pages/23_Analytics_Factory.py` — 6-tab analytics page (ダッシュボード/KPI分析/工場分析/プロジェクト分析/ROI分析/レポート)
  - Tab 1: 8 summary metrics, all insights, content counts, snapshot save
  - Tab 2: KPI achievement table, per-KPI progress bars, KPI insights
  - Tab 3: factory health cards (from FactoryRegistry), activity metrics
  - Tab 4: project progress cards, factory usage distribution
  - Tab 5: ROI metrics, revenue-by-source bars, expense-by-category bars
  - Tab 6: report date selector, generate/preview/export/download, report history
- `src/factories/analytics/` package — 7 modules
  - `analytics_collector.py` — read-only JSON collection from all factory config files + core registries
  - `kpi_analyzer.py` — KPI achievement analysis, 7 KPI labels, rule-based insights
  - `factory_analyzer.py` — factory health + activity analysis via FactoryRegistry, rule-based insights
  - `project_analyzer.py` — project progress + factory usage distribution, rule-based insights
  - `roi_analyzer.py` — cross-factory revenue/expense/profit/ROI analysis from Accounting + Sales config
  - `trend_reporter.py` — insight synthesis (error→warning→ok priority), Markdown report generation, export to `reports/analytics/`, snapshot persistence
- `config/analytics_settings.json` — settings: snapshot limit, KPI alert threshold, ROI target
- `config/analytics_snapshots.json` — snapshot store (max 30, FIFO eviction)
- `reports/analytics/` — output directory for analytics reports

### Changed
- `src/core/factory_registry.py` — added アナリティクス工場 to FACTORY_CATALOG (v4.7, 2 config files, 4 dependencies)
- `src/core/factory_interfaces.py` — added アナリティクス工場 → 📊 to FACTORY_ICONS
- `config/projects.json` — added アナリティクス工場 to default project factories list
- `pages/17_Mission_Control.py` — v4.7; Section 7.9 Analytics Factory card (health%, KPI%, PJ count, insight count)
- `pages/8_Dashboard.py` — v4.7; Analytics Factory summary strip at top (6 metrics)
- `app.py` — v4.7; アナリティクス工場 in WORKFLOW with snapshot count
- `scripts/check_project.py` — v4.7; `reports/analytics/` folder, 7 analytics files, 2 analytics config files, Analytics data section

### Architecture
- Analytics Factory reads all factory data **read-only** from existing JSON config files — no factory module imports in `analytics_collector.py`
- Rule-based insight synthesis: error → warning → ok priority ordering
- Snapshot history in `config/analytics_snapshots.json` (max 30, for future trend analysis)
- Uses `src.core.factory_registry.FactoryRegistry` and `src.core.project_manager` via lazy imports in factory_analyzer / project_analyzer

---

## [v4.5.1] — 2026-06-27 — Core Architecture

**Codename:** Core Architecture
**Upgrade path:** v4.6 → v4.5.1 (architecture-only; no new business features, no breaking changes)

### Added
- `src/core/factory_base.py` — `FactoryBase` ABC with 7 required methods: `initialize`, `health_check`, `sync_kpi`, `sync_dashboard`, `sync_mission_control`, `generate_report`, `export_status`. Plus `FactoryStatus` and `HealthReport` dataclasses.
- `src/core/factory_interfaces.py` — Shared TypedDicts, `FactoryProtocol` / `ProjectProtocol` Protocols, `FACTORY_ICONS` constant map.
- `src/core/factory_registry.py` — `FACTORY_CATALOG` static dict (6 factories), `FactoryRegistry` with health check + summary. No module imports — config/page existence checks only.
- `src/core/factory_events.py` — `EventBus` (pub/sub + JSON persistence). 7 event constants: `factory_initialized`, `factory_completed`, `factory_failed`, `factory_updated`, `project_updated`, `kpi_changed`, `report_generated`.
- `src/core/project_manager.py` — `Project` dataclass, CRUD, auto-creates default "Creator Factory" project with all 6 factories.
- `src/core/project_registry.py` — `ProjectRegistry` with system summary, per-project factory health, project queries.
- `config/projects.json` — Default "Creator Factory" project.
- `config/factory_events.json` — Event log store (empty, max 200 events).
- `docs/FACTORY_SPEC.md` — Folder structure, required files/methods, config format, integration requirements, design constraints, page structure, health check registration.
- `docs/PROJECT_SPEC.md` — Project model, lifecycle, workflow, registry API, Mission Control roadmap, default project.
- `docs/ARCHITECTURE_DECISIONS.md` — 7 ADRs: Project-Centric Architecture, FactoryBase Interface, Static Factory Catalog, Event Bus, JSON-First Storage, Lazy Imports, Additive-Only Rule.

### Changed
- `pages/17_Mission_Control.py` — v4.5.1; Section 3.5 Projects (project cards + system summary); Section 7.8 Core Architecture (health metrics + doc status).
- `pages/8_Dashboard.py` — v4.5.1; System Overview at top (project + factory health from registries).
- `app.py` — v4.5.1; Projects section (cards from ProjectRegistry).
- `scripts/check_project.py` — v4.5.1; 6 new core files + 3 arch docs in REQUIRED_FILES; Core Architecture data section.

### Architecture
Creator Factory OS is now **Project-centric**: Projects are the top-level unit; Factories are project modules. Existing factory modules are untouched.

---

## [v4.6] — 2026-06-27 — Accounting Audit Factory

**Codename:** Accounting Audit Factory
**Upgrade path:** v4.5 → v4.6 (additive, no breaking changes)

### Added
- `pages/22_Accounting_Factory.py` — 6-tab accounting page (ダッシュボード/収入/経費/サブスク/ROI/月次レポート)
  - Tab 1: break-even progress, audit alerts, quick revenue entry, recent entries
  - Tab 2: revenue CRUD with source filter, Sales Factory deal import
  - Tab 3: expense CRUD with category filter, large-expense warning
  - Tab 4: subscription management (8 presets, active/inactive toggle, renewal tracking)
  - Tab 5: ROI metrics, revenue by factory, expense by category, break-even settings
  - Tab 6: monthly report generate + preview + Markdown export to `reports/monthly/`
- `src/factories/accounting/` package — 6 modules
  - `revenue_manager.py` — revenue CRUD, 8 sources, source_factory tracking, today/monthly aggregation
  - `expense_manager.py` — expense CRUD, 8 categories, billing_cycle, category aggregation
  - `subscription_manager.py` — subscription CRUD, 8 presets, active toggle, renewal tracking, monthly total
  - `roi_calculator.py` — rule-based ROI/profit/break-even/conversion calculations
  - `audit_checker.py` — 6 rule-based warnings (expense>revenue, negative profit, no revenue, high sub ratio, large expense no memo, below break-even)
  - `monthly_report.py` — Markdown report generator, `export_monthly_report()` → `reports/monthly/`
- `config/accounting_revenue.json`, `accounting_expenses.json`, `accounting_subscriptions.json`, `accounting_settings.json`
- `reports/monthly/` folder — output directory for monthly accounting reports

### Changed
- `pages/17_Mission_Control.py` — v4.6; 会計監査工場 wired to `pages/22_Accounting_Factory.py`; Section 7.7 Accounting card with today's revenue/profit/expense/audit count; `sync_from_accounting()` added to data load
- `src/hq/factory_status.py` — added `sync_from_accounting()`: reads revenue/audits, sets warning on audit errors
- `pages/8_Dashboard.py` — added Accounting Factory summary strip (6 metrics: revenue/expense/profit/ROI/subscriptions/audits)
- `app.py` — v4.6; 会計監査工場 added to WORKFLOW with confirmed revenue count
- `scripts/check_project.py` — v4.6; `reports/monthly/` folder, `src/factories/accounting/` folder, 7 accounting files, 4 accounting config files, Accounting data section

### Architecture
- `src/factories/accounting/` sits parallel to `src/factories/note/`, `sns/`, `sales/` — same layering pattern
- Sales Factory integration: contracted deals in `sales_deals.json` can be imported as actual revenue (one-click in revenue tab)
- Audit checker is purely rule-based — no LLM, no external API
- Monthly report exports to `reports/monthly/YYYY-MM_accounting_report.md`

---

## [v4.5] — 2026-06-27 — Sales Factory

**Codename:** Sales Factory
**Upgrade path:** v4.4.1 → v4.5 (additive, no breaking changes)

### Added
- `pages/21_Sales_Factory.py` — 6-tab CRM page (ダッシュボード/見込み客/商談/フォロー/提案/売上予測)
  - Tab 1: today's followups, overdue alerts, pipeline overview, recent deals
  - Tab 2: lead CRUD with status/rank/source filtering and inline edit
  - Tab 3: deal management with stage kanban, transition, amount/probability editing
  - Tab 4: followup management (today/week/overdue/all views), mark done, skip
  - Tab 5: proposal tracking with response status lifecycle
  - Tab 6: sales forecast (pipeline, weighted, contracted, conversion rate, monthly projection, goal setting)
- `src/factories/sales/` package — full CRM module layer
  - `lead_manager.py` — lead CRUD, status lifecycle (new→contracted/lost), rank (S/A/B/C), 8 sources
  - `deal_manager.py` — deal CRUD, 7-stage pipeline, `transition_stage()`, `_on_contract()` KPI+factory side-effect
  - `followup_manager.py` — followup CRUD, overdue/today/week detection, `mark_done_followup()` → increments `sales_calls` KPI
  - `proposal_tracker.py` — proposal CRUD, 5 response statuses (draft/sent/replied/accepted/declined)
  - `sales_forecast.py` — rule-based pipeline/weighted/conversion calculations, monthly projection, settings load
- `config/sales_leads.json` — lead records store
- `config/sales_deals.json` — deal records store
- `config/sales_followups.json` — followup records store
- `config/sales_settings.json` — monthly_target + default probabilities per stage

### Changed
- `pages/17_Mission_Control.py` — v4.5; 営業工場 wired to `pages/21_Sales_Factory.py`; Section 7.6 Sales summary card; `sync_from_sales()` added to data load
- `src/hq/factory_status.py` — added `sync_from_sales()`: reads leads/followups, sets warning on overdue followups
- `pages/8_Dashboard.py` — added Sales Factory summary strip (leads/deals/contracted/forecast/followups)
- `app.py` — v4.5; 営業工場 added to WORKFLOW with active lead count
- `scripts/check_project.py` — v4.5; added `src/factories/sales/` folder, 5 sales modules + page 21, 4 sales config files, Sales Factory data section

### Architecture
- `src/factories/sales/` sits parallel to `src/factories/note/` and `src/factories/sns/` — same layering pattern
- `_on_contract()` in `deal_manager.py` updates factory card using lazy import of `factory_status`
- `mark_done_followup()` in `followup_manager.py` increments `sales_calls` actual using lazy import of `kpi_manager`
- All data local JSON; no external API calls; no database

---

## [v4.4.1] — 2026-06-27 — Claude Approval Assistant

**Codename:** Approval Assistant  
**Upgrade path:** v4.4 → v4.4.1 (additive, no breaking changes)

### Added
- `pages/20_Approval_Assistant.py` — 3-tab Claude Code approval analysis page
  - Tab 1: 分析 — paste prompt, analyze, see risk + Japanese explanation + next instruction
  - Tab 2: 履歴 — filterable history of past analyses (last 100)
  - Tab 3: ガイド — risk level reference guide + project rules
- `src/devtools/` package — Dev Tools module layer
  - `risk_rules.py` — 4-level risk definitions (🟢/🟡/🟠/🔴) + 36 command patterns
  - `command_classifier.py` — regex-based pattern detection, tool type inference, file path extraction
  - `approval_templates.py` — Japanese templates for 30+ command keys (what/why/after/warnings/next_instruction)
  - `approval_analyzer.py` — analysis pipeline, history save/load, `get_latest_risk()`
- `config/approval_rules.json` — configurable keyword lists per risk level
- `config/approval_history.json` — persisted analysis history (last 100 entries)

### Changed
- `pages/17_Mission_Control.py` — v4.4.1; added Section 7.5 Dev Tools with latest risk display and launch button;承認アシスタント added to NAV_ITEMS
- `pages/8_Dashboard.py` — added Approval Assistant latest analysis summary strip
- `app.py` — v4.4.1; 承認アシスタント added to WORKFLOW with analysis count
- `scripts/check_project.py` — v4.4.1; added src/devtools/ folder, 4 devtools files, 2 approval config files, Approval Assistant section

### Architecture
- `src/devtools/` sits parallel to `src/factories/` and `src/hq/` — no cross-dependencies with factory modules
- Zero external API calls — all classification is regex + rule-based
- History auto-caps at 100 entries; JSON-first storage consistent with rest of project

---

## [v4.4] — 2026-06-27 — SNS Factory

**Codename:** SNS Factory  
**Upgrade path:** v4.3 → v4.4 (additive, no breaking changes)

### Added
- `pages/19_SNS_Factory.py` — 6-tab SNS management page (dashboard, create, manage, calendar, repurpose, analytics)
- `src/factories/sns/` package — full SNS factory module layer
  - `sns_post_manager.py` — post CRUD, 4-status lifecycle, `_on_publish()` KPI/factory side-effects
  - `platform_formatter.py` — rule-based text generation for X, Threads, Instagram, TikTok, YouTube Shorts, LinkedIn, Facebook
  - `hashtag_generator.py` — category+platform hashtag generation with Japanese tag sets
  - `sns_calendar.py` — week/day schedule view, overdue detection, monthly summary
  - `sns_analytics_placeholder.py` — stub classes for X/Instagram/YouTube analytics + manual engagement updater
- `config/sns_posts.json` — SNS post queue (platform, source, text, hashtags, status, schedule)
- `config/sns_platforms.json` — platform config (char limits, icons, tones, max hashtags)
- `config/sns_schedule.json` — schedule metadata store

### Changed
- `pages/17_Mission_Control.py` — v4.4; SNS投稿工場 wired to `pages/19_SNS_Factory.py`; version caption updated
- `src/hq/factory_status.py` — added `sync_from_sns()` for live factory card sync
- `pages/8_Dashboard.py` — added SNS Factory summary strip (draft/scheduled/published/today)
- `app.py` — v4.4 caption; SNS投稿工場 added to WORKFLOW with published post count
- `scripts/check_project.py` — v4.4; added src/factories/sns/ folder, 6 SNS files, 3 SNS config files, SNS data section

### Architecture
- `src/factories/sns/` sits parallel to `src/factories/note/` — same pattern, different domain
- Platform formatter is purely rule-based (no LLM calls); each platform has dedicated formatter function
- SNS → Mission Control integration: `_on_publish()` increments `sns_posts` KPI + updates factory card
- Repurpose bridge reads `config/note_articles.json` and `project/*/episode.json` — no circular imports

---

## [v4.3] — 2026-06-27 — Note Factory

**Codename:** Note Factory  
**Upgrade path:** v4.2 → v4.3 (additive, no breaking changes)

### Added
- `pages/18_Note_Factory.py` — 6-tab note article management page
- `src/factories/note/` package — article manager, scorer, revenue tracker, repurpose engine, integration bridge
- `config/note_articles.json` — article data schema with status lifecycle and scoring

### Changed
- `pages/17_Mission_Control.py` — v4.3; note投稿工場 wired to page 18
- `src/hq/factory_status.py` — added `sync_from_notes()`
- `app.py` — v4.3; note投稿工場 added to WORKFLOW
- `scripts/check_project.py` — v4.3; added factories/ folder and all note files

---

## [v4.2] — 2026-06-27 — Dashboard Factory

**Codename:** Dashboard Factory  
**Upgrade path:** v4.1 → v4.2 (additive, no breaking changes)

### Added
- `pages/17_Mission_Control.py` — daily command center (KPI, tasks, factory status, finance, AI CEO message, navigation, daily report)
- `src/hq/` package — Mission Control data layer
  - `kpi_manager.py` — KPI CRUD, daily auto-reset, display row builder
  - `task_manager.py` — task CRUD, status lifecycle, stats, category grouping
  - `factory_status.py` — factory card data, task-driven count sync
  - `daily_report.py` — Markdown report generator and file exporter
- `config/kpi_targets.json` — daily KPI targets and actuals (auto-resets each morning)
- `config/daily_tasks.json` — daily task queue with 7-category system
- `config/factory_status.json` — status cards for 6 factories
- `config/revenue_expense.json` — today and month-to-date financial data
- `reports/daily/` folder — output directory for daily Markdown reports

### Changed
- `app.py` — renamed to Creator Factory OS; version v4.0 → v4.2; Mission Control added first in WORKFLOW
- `pages/8_Dashboard.py` — added Mission Control summary strip (completion %, open tasks, today revenue, video count)
- `scripts/check_project.py` — extended for src/hq, reports/daily, Mission Control page, 4 new config files

### Architecture
- New `src/hq/` layer sits between Streamlit pages and the existing `src/utils/` layer
- Rule-based AI CEO message generation: zero external API calls
- All task state persists to JSON; no database dependency added

---

## [v4.1] — 2026-06-27 — Multi-Agent Production Studio

**Codename:** Multi-Agent Production Studio  
**See:** `RELEASE_NOTES_v4.1.md` for full details

### Added
- `pages/15_Project_Manager.py` — 6-tab project hub (overview, series, analytics, backup, package, batch ops)
- `pages/16_AI_Studio.py` — multi-agent production command center (4 tabs)
- `src/agents/` package — 6-agent pipeline (Producer → Director → Script → Prompt → Editor → Publisher)
  - `base_agent.py` — `Task`, `TaskQueue`, `BaseAgent` ABC
  - `agent_registry.py` — `AgentRegistry` with DI routing and JSON persistence
  - 6 agent implementations
- `src/utils/project_manager.py` — series CRUD, episode operations, bulk actions
- `src/utils/backup_manager.py` — timestamped ZIP backup, restore, project import/export
- Windows utility pack: `run_ai_factory.bat`, `stop_streamlit.bat`, `update_from_github.bat`, `backup_project.bat`, `create_desktop_shortcut.ps1`, `check_environment.bat`
- `README_UTILITIES.md`

### Fixed
- All `.bat` files converted to ASCII-only content to resolve cp932/UTF-8 parse errors on Japanese Windows

### Changed
- `scripts/check_project.py` — extended from 29 to 53 required file checks (full v4.1 coverage)

---

## [v3.1-RC1] — 2026-06-26 — AI Director Layer

### Added
- `src/director/` package
  - `director_schema.py` —演出計画スキーマ定義
  - `director_planner.py` — `load/save_director_plan()`, `generate_plan_with_ai()`
- `pages/14_Director.py` — 手動モード + AI生成モード演出計画エディタ
- Prompt Builder: 🎬 演出ディレクションセクション（Director計画をプロンプトに注入）
- Production page: `director_plan.json` バリデーション・プレビュー・エクスポート対応
- Dashboard: 🎬 Director バッジ

### Changed
- `export_pipeline.py` — エクスポートパッケージに `director_plan.json` を追加; `production_report.json` に演出サマリー追加
- One-click generation: post-generation AI Director誘導メッセージ追加

---

## [v3.0] — 2026-06-26 — End-to-End Production Pipeline

### Added
- `src/pipeline/` package
  - `script_pipeline.py`, `image_pipeline.py`, `video_pipeline.py`, `audio_pipeline.py` — ファイルバリデーション
  - `export_pipeline.py` — `production_state.json` CRUD + 書き出しパッケージ作成
- `src/providers/` package (Manual baseline)
  - `openai_provider.py`, `image_provider_manual.py`, `video_provider_manual.py`, `audio_provider_manual.py`
- `pages/13_Production.py` — 6ステージ制作チェックリスト + 書き出しパッケージ

### Changed
- Dashboard: 📦 書き出し済 / 🎬 制作可能 バッジ追加

---

## [v2.9] — 2026-06-25 — Prompt Builder

### Added
- `src/utils/prompt_builder.py` — キャラ×背景×ムード×スタイル×カメラを合成
- `pages/12_Prompt_Builder.py` — 4種類の出力（画像/動画/ボイスディレクション/サムネイル）
- `config/prompt_templates.json` — テンプレートCRUD

---

## [v2.8] — 2026-06-25 — Background Manager

### Added
- `src/utils/background_manager.py` — 背景CRUD・デフォルト設定・プロンプトスニペット生成
- `pages/11_Backgrounds.py` — 5タブエディタ（基本/ビジュアル/カメラ/プロンプト/アセット）
- `config/backgrounds.json`

---

## [v2.7] — 2026-06-24 — Character Manager

### Added
- `src/utils/character_manager.py` — キャラクターCRUD・デフォルト設定・プロンプトスニペット生成
- `pages/10_Characters.py` — 5タブエディタ（基本情報/外見/性格/プロンプト/アセット）
- `config/characters.json`
- AI pipeline への キャラクター自動注入

---

## [v2.6] — Studio Settings

### Added
- `pages/9_Settings.py` — スタジオ設定ページ（AI・生成プロバイダー・プロジェクト設定）
- `config/settings.json` での永続化
- `src/utils/settings_manager.py` — `load_settings()`, `save_settings()`, deep-merge with DEFAULTS

---

## [v2.5] — Production Dashboard

### Added
- `pages/8_Dashboard.py` — 全エピソードの制作進捗一覧
- ステータス判定（完成/制作中/素材待ち/未着手）・フィルター・ソート・ファイルプレビュー

---

## [v2.2] — Asset Library

### Added
- `pages/7_Assets.py` — 素材ライブラリ管理
- `assets/` フォルダ構造

---

## [v2.1] — Low-Cost Manual Production

### Added
- コスト節約モード（短縮プロンプト）
- 手動制作ガイド（Runway / Nano Banana 向け）

---

## [v2.0] — One-Click Generation

### Added
- `pages/6_Produce.py` — 一発生成ページ
- `src/core/ai_pipeline.py` — OpenAI による台本・プロンプト・字幕・音声台本一括生成

---

## [v1.x] — Foundation

### Added
- `pages/1_Script.py`, `2_Subtitles.py`, `3_Assembly.py`, `4_Files.py`, `5_Episode.py` — 基本制作ページ
- `src/core/openai_client.py`, `whisper_client.py`, `ffmpeg_utils.py` — コアクライアント
- `src/utils/config.py`, `file_manager.py` — プロジェクト設定・ファイルカウント
- `app.py` — Streamlit マルチページアプリ エントリポイント
- `.env` / `.env.example` — API キー管理
- `scripts/check_project.py` — プロジェクト整合性チェック
