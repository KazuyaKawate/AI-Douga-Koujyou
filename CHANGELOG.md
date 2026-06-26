# Changelog — Creator Factory OS (旧: AI動画工場)

All notable changes to this project are documented in this file.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versions are cumulative; each release builds on the previous stable base.

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
