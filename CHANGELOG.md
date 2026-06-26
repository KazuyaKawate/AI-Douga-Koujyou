# Changelog — Creator Factory OS (旧: AI動画工場)

All notable changes to this project are documented in this file.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versions are cumulative; each release builds on the previous stable base.

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
