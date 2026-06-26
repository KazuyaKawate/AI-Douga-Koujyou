# Release Notes — Creator Factory OS v4.2 Dashboard Factory

**Release date:** 2026-06-27  
**Status:** Stable — all health checks pass, zero compilation warnings  
**Git commit:** `c91c61f`  
**Base:** v4.1 Stable (commit `a76f666`)

---

## Overview

v4.2 marks the transition from **AI動画工場** (a single-purpose video production tool) to **Creator Factory OS** — a unified daily operating system for solo content creators.

The centrepiece of this release is **Mission Control** (`pages/17_Mission_Control.py`): a full-screen daily command center that opens on startup, shows today's KPIs at a glance, lets you check off tasks with one click, and navigates directly to any active factory.

> **Design principle:** open the app → see everything that matters today → start working in under 10 seconds.

---

## Screenshots

> _Screenshots will be added after the first live session._

| Section | Description |
|---------|-------------|
| ![Mission Control Header](docs/screenshots/mc_header.png) | Header with date, build, status |
| ![KPI Panel](docs/screenshots/mc_kpi.png) | Today KPI with progress deltas |
| ![Task List](docs/screenshots/mc_tasks.png) | Checkbox task list with start buttons |
| ![Factory Cards](docs/screenshots/mc_factories.png) | Six factory status cards |
| ![Finance Snapshot](docs/screenshots/mc_finance.png) | Revenue / expense / ROI / breakeven |

---

## New Features

### Mission Control — Daily Command Center (`pages/17_Mission_Control.py`)

The first page in the sidebar. Opens directly to today's operational view.

#### 1. Header

```
🎯 Creator Factory OS
📅 2026年06月27日 (Saturday)   🔨 Build: v4.2 Dashboard Factory   ✅ Status: v4.2 Dashboard Factory
```

#### 2. Today KPI

Seven metrics displayed as `st.metric` cards with delta indicators:

| Metric | Key | Unit | Editable |
|--------|-----|------|----------|
| 今日の売上目標 | `sales_target` | 円 | No (target) |
| 今日の売上実績 | `sales_actual` | 円 | Yes |
| note投稿数 | `note_posts` | 件 | Yes |
| 動画制作数 | `video_count` | 本 | Yes |
| SNS投稿数 | `sns_posts` | 件 | Yes |
| 営業件数 | `sales_calls` | 件 | Yes |
| 開発タスク数 | `dev_tasks` | 件 | Yes |

Actuals are edited via an expandable number-input panel. Values save immediately on change and reset to zero at the start of each new day.

#### 3. Today Tasks

Interactive task list with:

- **Checkbox** — toggle done/pending, auto-saves to `config/daily_tasks.json` via `on_change` callback
- **Task title** — ~~strikethrough~~ when complete
- **Category badge** — one of 7 factory categories
- **Priority indicator** — 🔴 高 / 🟡 中 / 🟢 低
- **▶️ 開始 button** — sets status to `in_progress` and reveals a `st.page_link` to the related factory page, or inline guidance text for factories without a page yet

Tasks sorted by: in_progress first → pending → done, then by priority within each group.

**Task categories:**

| Category | Icon | Page Link |
|----------|------|-----------|
| AI動画工場 | 🎬 | `pages/1_Script.py` |
| note投稿工場 | 📝 | Coming Soon |
| SNS投稿工場 | 📱 | Coming Soon |
| 営業工場 | 💼 | Coming Soon |
| 会計監査工場 | 💰 | Coming Soon |
| 開発 | ⚙️ | `pages/17_Mission_Control.py` |
| 経営 | 🏢 | `pages/8_Dashboard.py` |

#### 4. Factory Status Cards

Six cards in a 3-column grid. Each card shows:

- Factory name + status dot (🟢 active / 🟡 idle / 🔴 warning / ⚫ stopped)
- Active items count
- Completed today count
- Warning count (shown as `st.warning` if > 0)
- Next action text

Factory counts auto-sync from the daily task list on every page load.

#### 5. Finance Snapshot

Six `st.metric` widgets:

| Metric | Formula |
|--------|---------|
| 今日の売上 | `today.revenue` |
| 今月売上 | `month.revenue` |
| 今月費用 | `month.expense` |
| 今月利益 | `month.revenue - month.expense` |
| ROI | `profit / expense × 100` |
| 損益分岐点まで | `max(0, breakeven - month.revenue)` |

An expandable editor allows updating today/month figures. If `month.expense > month.revenue`, a red alert appears automatically.

#### 6. AI CEO Daily Message (rule-based, no API)

Generates a prioritised guidance message from the current state. Rules evaluated in order:

| Condition | Message |
|-----------|---------|
| Month expense > revenue | 費用が売上を上回っています。無料運用を優先してください。 |
| All tasks done | 本日の主要タスクはすべて完了しています。素晴らしい成果です！ |
| AI動画工場 tasks pending | 今日は動画制作を優先してください。 |
| note投稿工場 tasks pending | note記事の投稿がまだです。コンテンツ発信を忘れずに。 |
| SNS投稿工場 tasks pending | SNS投稿でオーディエンスとのエンゲージメントを高めましょう。 |
| 営業工場 tasks pending | 営業活動を積み重ねることで収益につながります。 |
| Sales KPI met | 本日の売上目標を達成しました！ |
| Progress ≥ 80% | あと少しで全タスク完了です。 |
| Progress 0% | 最優先タスクから着手してください。 |
| Progress < 50% | 集中して作業を進めましょう。 |

Multiple rules can fire; messages are concatenated with a space.

#### 7. One-click Navigation

Six navigation slots. Existing pages use `st.page_link()`; pages not yet implemented show a disabled button labelled "Coming Soon 🚧".

| Button | Target |
|--------|--------|
| 🎬 AI動画工場を開く | `pages/1_Script.py` |
| 📝 note投稿工場を開く | Coming Soon |
| 📱 SNS投稿工場を開く | Coming Soon |
| 💼 営業工場を開く | Coming Soon |
| 💰 会計監査工場を開く | Coming Soon |
| 📊 ダッシュボードを開く | `pages/8_Dashboard.py` |

#### 8. Daily Report

Auto-generated Markdown report containing:

- KPI progress table
- Completed tasks (with checkboxes)
- In-progress tasks
- Remaining tasks (with priority marks)
- Finance summary table
- AI CEO message

Two export options:
- **📄 エクスポート** — saves to `reports/daily/YYYY-MM-DD_daily_report.md`
- **⬇️ ダウンロード** — browser download of the Markdown file

---

## New Modules — `src/hq/`

The HQ package is the data layer for Mission Control. All modules are pure Python with no external dependencies beyond the standard library.

| Module | Responsibilities |
|--------|-----------------|
| `src/hq/__init__.py` | Package marker |
| `src/hq/kpi_manager.py` | Load/save `config/kpi_targets.json`; auto-reset actuals on new day; `get_kpi_rows()` for display |
| `src/hq/task_manager.py` | Load/save `config/daily_tasks.json`; `update_task_status()`; `get_task_stats()`; `get_tasks_by_category()` |
| `src/hq/factory_status.py` | Load/save `config/factory_status.json`; `sync_from_tasks()` to auto-update counts from task data |
| `src/hq/daily_report.py` | `generate_report()` — builds full Markdown string; `export_report()` — writes to `reports/daily/` |

---

## New Config Files

| File | Structure | Auto-reset |
|------|-----------|------------|
| `config/kpi_targets.json` | `{date, targets{}, actuals{}}` | Actuals reset to 0 on new day |
| `config/daily_tasks.json` | `{date, tasks[]}` | Non-done tasks reset to `pending` on new day |
| `config/factory_status.json` | `{factory_name: {status, active_items, completed_today, warning_count, next_action}}` | Synced from tasks on each page load |
| `config/revenue_expense.json` | `{today: {date, revenue, expense}, month: {year_month, revenue, expense, breakeven}}` | Manual update via UI |

---

## New Folders

| Folder | Purpose |
|--------|---------|
| `reports/daily/` | Daily report exports (`YYYY-MM-DD_daily_report.md`) |

---

## Updated Files

### `app.py`
- App title: `AI動画工場` → `Creator Factory OS`
- Page icon: 🎬 → 🎯
- Caption: `v4.0 Multi-Agent Production Studio` → `v4.2 Dashboard Factory`
- Mission Control added as the first item in the WORKFLOW table
- Mission Control metric: shows today's completed task count
- Quick Start guide updated to v4.2 (Mission Control as step 1)

### `pages/8_Dashboard.py`
- Caption updated: `v3.0` → `v4.2`
- Added Mission Control Summary strip at the top (four metrics + page link):
  - Today completion %
  - Open tasks count
  - Today revenue
  - Video count
- Uses a try/except guard so the strip is silently skipped if `src/hq` is unavailable

### `scripts/check_project.py`
- Title updated: `AI動画工場` → `Creator Factory OS v4.2`
- Required folders: added `reports/`, `reports/daily/`, `src/hq/`
- Required files: added `pages/17_Mission_Control.py` + all five `src/hq/*.py`
- Optional files: added all four `config/*.json` Mission Control data files
- New `[ Mission Control 設定ファイル ]` section: validates and counts entries in each JSON
- New `[ レポートフォルダ ]` section: counts exported reports

---

## Health Check Results

```
============================================================
  Creator Factory OS v4.2 — Project Health Check
============================================================
[ フォルダ ]      18/18 OK
[ 必須ファイル ]  61/61 OK  (↑ from 53 in v4.1)
[ Mission Control 設定ファイル ]  4/4 OK
[ レポートフォルダ ]  OK  (0 レポート — fresh install)
[ エピソード ]    2 total
============================================================
  STATUS: OK — すべての必須ファイルが揃っています ✅
```

All 61 required files pass `python -m py_compile` with zero errors.

---

## Known Limitations

| Area | Detail |
|------|--------|
| note / SNS / 営業 / 会計 factories | Pages not yet implemented. Navigation buttons show "Coming Soon". Tasks still trackable in Mission Control. |
| KPI daily reset | Reset is triggered on page load the next day, not at midnight. If the page is not loaded on a new day, the previous day's actuals remain until next load. |
| Finance data | Revenue and expense figures are entered manually. No automatic integration with accounting tools. |
| Multi-tab concurrency | JSON writes are not atomic. Opening Mission Control in multiple browser tabs simultaneously can cause race conditions on task status updates. Single-tab operation is recommended. |
| Task list bootstrap | `config/daily_tasks.json` ships with 9 example tasks. Users should edit this file directly to customise their daily routine. A UI editor for the task list is planned for v4.3. |

---

## Next Milestone — v4.3 Note Factory

See `ROADMAP.md` for the full v4.3 specification.

**Target:** 2026-07 (TBD)

Key deliverables:
- `pages/18_Note_Factory.py` — note article planning, drafting, and publication tracker
- `src/factories/note/` — article manager, category tracker, SEO checklist
- `config/note_articles.json` — article queue with status lifecycle
- Mission Control integration: note投稿工場 "Coming Soon" → live page link
- KPI auto-update: note_posts actual increments when article is marked published
