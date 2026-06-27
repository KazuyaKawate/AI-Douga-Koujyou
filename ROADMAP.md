# Roadmap — Creator Factory OS

> **Vision:** A solo creator's operating system. Open the app in the morning, see what matters today, execute each factory in order, close with a daily report. Zero wasted navigation.

---

## Completed

### ✅ v1.x — Foundation
Core Streamlit multi-page app. Script / subtitle / assembly / file management pages. OpenAI client, Whisper client, FFmpeg utils.

### ✅ v2.0 — One-Click Generation
One-shot episode generation: topic → script + image prompts + video prompts + voice script + SRT via OpenAI.

### ✅ v2.5 — Production Dashboard
Per-episode status board with filters, sorting, file previews, step-completion badges.

### ✅ v2.6 → v2.9 — Studio Tooling
Studio settings, character manager, background manager, prompt builder with template persistence.

### ✅ v3.0 — End-to-End Production Pipeline
`src/pipeline/` validation layer. 6-stage production checklist. Export package to `project/EPXX/export/`.

### ✅ v3.1 — AI Director
Scene-by-scene direction planner (manual + OpenAI-generated). Director plan injected into export package.

### ✅ v4.1 — Multi-Agent Studio
6-agent pipeline (Producer → Director → Script → Prompt → Editor → Publisher). Project Manager hub. Windows utility pack.

### ✅ v4.2 — Dashboard Factory / Mission Control
Creator Factory OS rebrand. Mission Control daily command center. KPI, task list, factory status, finance snapshot, AI CEO message, daily report export. `src/hq/` data layer.

### ✅ v4.3 — Note Factory
`pages/18_Note_Factory.py` — article lifecycle (draft → review → scheduled → published → archived), 6-criteria rule-based scoring (SEO/Readability/CTA/Story/Originality/Monetization 0-100), per-article revenue tracking, content repurposing (X/Threads/YouTube Shorts/video proposal), Mission Control KPI integration. `src/factories/note/` data layer.

### ✅ v4.4 — SNS Factory
`pages/19_SNS_Factory.py` — 7-platform SNS management. Rule-based platform formatter. Hashtag generator. Content repurposing from notes and episodes. Weekly calendar. Engagement tracking. `src/factories/sns/` data layer.

### ✅ v4.4.1 — Claude Approval Assistant
`pages/20_Approval_Assistant.py` — Claude Code approval prompt classifier. 4 risk levels (🟢/🟡/🟠/🔴). 36 command patterns. Japanese explanations for 30+ command types. History. Mission Control Dev Tools card. No external API. `src/devtools/` module layer.

### ✅ v4.5 — Sales Factory
`pages/21_Sales_Factory.py` — Full CRM: lead management (8 sources, 4 ranks, status lifecycle), deal pipeline (7 stages with weighted forecast), follow-up manager (overdue detection, today/week views, mark-done → `sales_calls` KPI), proposal tracker (5 response statuses), rule-based sales forecast (pipeline/weighted/conversion/monthly projection). Mission Control Section 7.6 sales card + `sync_from_sales()`. `src/factories/sales/` data layer.

### ✅ v5.2 Phase 4-2 — Google Sheets Local Config Override _(2026-06-27)_
`config/workspace_local.json` (git-ignored) introduced as local runtime config. Overrides committed `workspace_settings.json` at runtime: auth_mode, service_account_file, spreadsheet_id, worksheet_name. `load_local_settings()` + `load_merged_settings()` + `get_local_config_status()` added to `sync_validator`. All runtime entry points (`get_auth_config`, `build_client`, `read_sheet`, `test_read_connection`) now use merged settings when `settings=None`. Dev Studio Tab 10 gains Phase 4-2 section: local config status panel (exists/auth_mode/spreadsheet_id/worksheet_name), JSON template expander, setup hints, Read Connection Test uses merged settings. Health check Phase 4-2 section: workspace_local.json git-ignore/tracking check, local config values, merged test_read_connection result, write guard check. Phase 4-3 = write enable via `allow_write=True` + live execute.

### ✅ v5.2 Phase 4-1 — Google Sheets Read-Only Connection _(2026-06-27)_
`build_client()` fully implemented in `google_auth.py`: builds live `gspread.Client` for `service_account` mode using lazy imports; returns structured status dict; never crashes. `read_sheet()` now calls live gspread API for service_account; `read_sheet_detail()` added (rich return: ok/rows/row_count/source/error). `test_read_connection()` added to `sync_executor`: end-to-end read-only test returning client_status, row_count, source, duration. Quad-lock write guard: 4th lock `allow_write=False` added to `write_rows()` — Phase 4-1 stays read-only. Dev Studio Tab 10 gains Phase 4-1 section: dependency metrics, credential file check, spreadsheet_id / worksheet_name status, "Read Connection Test" button with live result (row_count, source, duration). Health check Phase 4-1 section: service-account.local.json git-tracking check, committed auth_mode=disabled check, write-blocked check, test_read_connection result. `credentials/service-account.local.json` explicitly in `.gitignore`. Phase 4-2 = write enable via `allow_write=True`.

### ✅ v5.2 Phase 3 — Google Sheets Credential Safety & gspread Readiness _(2026-06-27)_
`credentials/` folder with `.gitkeep` (real JSON excluded by `.gitignore`). `docs/google_sheets_setup.md` setup guide. Four new `sync_validator` functions: `check_gitignore_protections()`, `check_credentials_gitkeep()`, `check_phase3_dependencies()` (gspread + google-auth via importlib.metadata, no circular import), `get_phase3_readiness()` (composite 6-check readiness: .gitignore, .gitkeep, no-cred-committed, auth_mode=disabled, deps, spreadsheet_id). `google_auth.get_dependency_status()` added. `sheet_reader` + `sheet_writer` + `sync_executor` updated to Phase 3. Dev Studio Tab 10 gains Phase 3 readiness checklist (🔒 safety / 📦 optional distinction). `check_project.py` Phase 3 section: credentials folder, gitignore patterns, gspread/google-auth check. All files py_compile clean. `auth_mode` stays `disabled`. No real credentials committed. Phase 4+ = live gspread API calls.

### ✅ v5.2 Phase 2 — Google Sheets Connector Foundation _(2026-06-27)_
5 new connector modules in `src/workspace/`: `google_auth.py` (credential config loader; `auth_mode` defaults to `disabled`; never reads credential contents), `sheet_reader.py` (read abstraction; returns sample data when disabled; Phase 3+ API hook), `sheet_writer.py` (write abstraction; triple-lock guard: `auth_mode != disabled` AND `dry_run=False` AND `manual_execute=True`; default preview-only), `sheet_diff.py` (pure diff engine: added/updated/removed/conflicts/unchanged; no I/O), `sync_executor.py` (orchestrator: `run_preview()` steps 1-5 no writes, `run_execute()` triple-locked, `get_connector_health()` dashboard-safe). Updated: `workspace_settings.json` gains `connector` section (`auth_mode=disabled`). `sync_validator.py` adds `validate_connector_settings()` and `check_no_credentials_committed()`. `sheets_sync.py` SHEET_MAPPINGS gain `key_field` for diff engine. Dev Studio Tab 10: security warning, auth mode display, credential status, `check_no_credentials_committed()` result, target list, diff preview (calls `sync_executor`), manual execute button disabled. Dashboard, Mission Control, AI CEO: connector health metrics (auth_mode, dry_run, targets, last_preview, conflict_count). `check_project.py`: Phase 2 connector section (module files, cred scan, auth_mode check, import test, py_compile). Credentials NEVER committed.

### ✅ v5.2 Phase 1 — Google Workspace Sync Foundation _(2026-06-27)_
`src/workspace/` package (6 modules): `sync_models.py` (TypedDicts, status/conflict icons), `sync_history.py` (history logging to `config/sync_history.json`), `sync_validator.py` (read-only settings validation, connection status), `sheets_sync.py` (column-mapping for 5 targets: KPI/Revenue/Notes/SNS/Sales), `sync_engine.py` (orchestration: `generate_preview()`, `run_dry_run()`, `run_sync()` Phase 1 = always dry, `get_sync_health()`). `config/workspace_settings.json` (5 sync targets, dry_run_default=true, enabled=false, auto_sync=false). `config/sync_history.json` (empty store). `reports/workspace/`. Dev Studio 10th tab "🔄 Workspace Sync" (connection status, validation errors, per-target preview, dry-run button, sync history). Dashboard strip, Mission Control Section 7.14 card. AI CEO reads `workspace_sync` health from executive_engine snapshot (read-only). Phase 2 will add google-auth + gspread for actual writes.

### ✅ v5.1 Phase 2 — Module SDK Self-Registration Foundation _(2026-06-27)_
Extended `MODULE_INFO` schema with `module_id` (auto-slugified), `display_name`, `sdk_version`, `minimum_os_version`, `entrypoint`, `package_path`, `status`. `module_loader.py` now discovers both `MODULE_INFO` (new canonical) and `MODULE_MANIFEST` (legacy). `registry_builder.py` adds `export_registry()` → `config/module_registry.json` (on-demand), `load_exported_registry()`, `get_by_id()`, `STATUS_ICONS`. Development Studio gains a 9th "📦 Module SDK" tab: summary metrics, per-module expandable cards (all fields), export button, validation errors. Module SDK status card added to Dashboard and Mission Control (Dev Studio section). All 11 BUILTIN_MANIFESTS updated with explicit module_ids, package_paths, entrypoints, statuses. `config/module_registry.json` pre-populated (11 modules, 0 invalid).

### ✅ v5.1 Phase 1 — Module SDK + Approval Center _(2026-06-27)_
`pages/27_Approval_Center.py` — 5-tab human-approval gateway: Pending (stored queue + Live Inbox from AI CEO / Automation / DevStudio), Approved History, Rejected History, New Request (manual submission form), Summary (source/risk breakdown). `src/approval/` package (5 modules). `src/sdk/` Module SDK (5 modules): `ModuleInfo` TypedDict schema, `make_manifest()` helper, `BUILTIN_MANIFESTS` (11 modules), manifest validator, module loader (built-in + dynamic discovery), `ModuleRegistry` class. Approval Center is read-only: Approve/Reject buttons update `config/approval_queue.json` only, never execute commands. Mission Control Section 7.13 Approval Center card. Dashboard Approval Center strip.

### ✅ v5.0-beta Phase 2 — AI CEO Core _(2026-06-27)_
`pages/26_AI_CEO.py` — Executive decision layer. 7-tab interface: CEO Daily Brief (overall health 0-100, OS snapshot), KPI Summary (per-metric achievement bars, revenue summary), Top 10 Priorities (Impact+Urgency+ROI+Dependencies scoring), Opportunities (ROI/unused factory/automation/content), Risks (revenue/factory/roadmap/KPI), Recommendations (up to 10; reason+impact+confidence+factory+action; never executed), Executive Report (Markdown export to reports/aiceo/). `src/aiceo/` package (9 modules). NOT a Factory. NOT a chatbot. Executive Module. No FactoryRegistry registration. Mission Control Section 7.12 AI CEO card. Dashboard AI CEO Executive Summary strip.

### ✅ v5.0-beta — Development Studio _(2026-06-27)_
`pages/25_Development_Studio.py` — OS development headquarters. 8-tab management interface: Overview (version, registry counts, open decisions, recent meetings), Roadmap Manager (CRUD with status lifecycle), Release Manager (health tracking), Decision Log (impact/status tracking), Meeting Notes (agenda/decisions/next actions), Health Check (run-on-demand scripts/check_project.py), Git Status (read-only branch/commit/dirty status), Spreadsheet Export (CSV to reports/devstudio/). `src/devstudio/` package (7 modules). No FactoryRegistry registration — this is an OS Management tool. Mission Control Section 7.11 Dev Studio card. Dashboard Dev Studio summary strip.

### ✅ v4.8 — Automation Factory
`pages/24_Automation_Factory.py` — 6-tab workflow automation layer: Dashboard (6 metrics, enabled workflow list, recent runs, quick dry-run button), Workflows (CRUD with enable/disable toggle), Templates (5 built-in templates with one-click install), Run Log (paginated history, filter by dry/real), Report (generate + export Markdown), Settings (dry_run_default, max_runs, log_retention). `src/factories/automation/` package (7 modules): `automation_rules.py` (6 trigger types, 6 action types, 5 templates), `workflow_manager.py` (CRUD + run counter), `trigger_engine.py` (READ-ONLY trigger evaluation), `action_engine.py` (draft-only actions, dry_run=True gating), `automation_runner.py` (orchestration), `automation_reporter.py` (run log + Markdown export). Safe-first: all actions create drafts; no auto-publishing; dry_run=True default; `_automation_source` flag on all generated items. Mission Control Section 7.10 automation card. Dashboard automation strip.

### ✅ v4.7 — Analytics Factory
`pages/23_Analytics_Factory.py` — 6-tab unified analytics layer: KPI achievement analysis (7 KPIs, avg%, per-KPI bars), factory health analysis (FactoryRegistry health check, activity metrics, per-factory cards), project progress analysis (progress cards, factory usage distribution), cross-factory ROI analysis (revenue-by-source, expense-by-category, sub cost ratio), rule-based insight synthesis (error→warning→ok priority), Markdown report export to `reports/analytics/`, snapshot persistence. `src/factories/analytics/` package (7 modules). Mission Control Section 7.9 analytics card. Dashboard analytics strip. Uses v4.5.1 Core Architecture (FactoryRegistry + ProjectRegistry).

### ✅ v4.5.1 — Core Architecture
`src/core/` architecture layer: `FactoryBase` ABC (7 required methods), `FactoryRegistry` static catalog (6 factories, config/page existence health check), `EventBus` (pub/sub + JSON persistence, 7 event types), `Project` dataclass + CRUD + `ProjectRegistry` (system summary, per-project factory health). Creator Factory OS is now **Project-centric** — Projects are the top-level unit; Factories are project modules. Architecture docs: `FACTORY_SPEC.md`, `PROJECT_SPEC.md`, `ARCHITECTURE_DECISIONS.md` (7 ADRs). Mission Control Section 3.5 (Projects) + Section 7.8 (Core Architecture). Dashboard System Overview strip. Existing factory modules untouched.

### ✅ v4.6 — Accounting Audit Factory
`pages/22_Accounting_Factory.py` — Revenue management (8 sources, factory tracking, Sales Factory import), expense management (8 categories, billing cycle), subscription management (8 presets, active toggle, renewal tracking), rule-based ROI/profit/break-even calculator, 6-rule audit checker (expense>revenue, negative profit, no revenue, high sub ratio, large expense no memo, below break-even), monthly Markdown report export to `reports/monthly/`. Mission Control Section 7.7 accounting card + `sync_from_accounting()`. `src/factories/accounting/` data layer.
`pages/19_SNS_Factory.py` — 7-platform SNS management (X, Threads, Instagram, TikTok, YouTube Shorts, LinkedIn, Facebook). Rule-based platform formatter. Hashtag generator. Repurpose from note articles and video episodes. Weekly schedule calendar. Overdue detection. Manual engagement tracking. Analytics stubs. Mission Control KPI integration. `src/factories/sns/` data layer.

---

## Next

### 🔲 v4.3 — Note Factory _(Target: 2026-07)_

**Goal:** Make `note投稿工場` a fully operational factory inside Creator Factory OS. Clicking "📝 note投稿工場を開く" in Mission Control navigates to a live page.

**Deliverables:**

| Item | Description |
|------|-------------|
| `pages/18_Note_Factory.py` | Main note factory page |
| `src/factories/note/__init__.py` | Package marker |
| `src/factories/note/article_manager.py` | Article CRUD: draft → review → published lifecycle |
| `src/factories/note/seo_checklist.py` | Rule-based SEO score (title length, tag count, body length, CTA) |
| `src/factories/note/publishing_tracker.py` | Track published URLs, view counts (manual entry) |
| `config/note_articles.json` | Article queue |

**Page sections:**
1. **Article Queue** — list with status badges (下書き / レビュー中 / 公開済)
2. **New Article** — title, tags, body outline, target keyword, estimated reading time
3. **SEO Checklist** — rule-based score, no API
4. **Publishing Log** — published date, note URL, manual view count entry
5. **KPI Integration** — completing "公開済" auto-increments `note_posts` actual in `config/kpi_targets.json`

**Mission Control changes:**
- `pages/18_Note_Factory.py` wired to "📝 note投稿工場を開く" button
- note投稿工場 factory card shows live article counts

---

### 🔲 v4.9 — Factory Automation _(Target: 2026-Q4)_

Connect the factories to each other. Completing a video in AI動画工場 auto-populates an SNS post draft. Publishing a note article auto-logs the revenue if sold.

**Key features:**
- Cross-factory event triggers (rule-based)
- `config/factory_events.json` — event log
- Mission Control: daily activity timeline

---

### 🔄 v5.0 — Creator Factory OS — Full Platform _(In Beta from 2026-06-27)_

**v5.0-beta started** with Development Studio as Milestone 1. Subsequent milestones TBD.

**Goal:** Every section of the creator's business runs inside one app.

| Factory | Status at v5.0 |
|---------|---------------|
| 🎬 AI動画工場 | Full pipeline: script → image → video → audio → assembly → upload |
| 📝 note投稿工場 | Full: draft → SEO → publish → track |
| 📱 SNS投稿工場 | Full: compose → schedule → track engagement |
| 💼 営業工場 | Full: CRM → pipeline → forecast |
| 💰 会計監査工場 | Full: transaction → P&L → tax estimate |
| 🎯 Mission Control | Full: all factories live; daily auto-report emailed at end of day |

**Additional v5.0 capabilities:**
- SQLite backend option for high-volume users (JSON stays as default)
- Cloud backup integration (S3 / Google Drive) via MANIFEST.json reserved fields
- Weekly performance report: compare current week vs. previous 4-week average
- Multi-platform publish API integrations (YouTube, note, Twitter/X — gated by API key)

---

## Deferred (not in active roadmap)

| Item | Reason |
|------|--------|
| Multi-user support | Single-creator product; adds auth/session complexity with no current need |
| Cloud deployment | Local-first by design; `reports/` and `config/` are personal data |
| Runway / ElevenLabs API | Infrastructure exists (`src/providers/`); deprioritised until manual workflow is stable |
| FFmpeg auto-assembly | `ffmpeg_utils.py` exists; deferred until asset pipeline is complete |
| Whisper transcription UI | `whisper_client.py` exists; deferred until audio workflow is prioritised |

---

## Version Naming Convention

| Range | Codename | Theme |
|-------|----------|-------|
| v1.x – v2.x | Foundation / Studio | Core video production tools |
| v3.x | Pipeline | Production validation and AI direction |
| v4.x | Factory OS | Business operating system layer |
| v5.x | Creator Platform | Full integrated creator business platform |
