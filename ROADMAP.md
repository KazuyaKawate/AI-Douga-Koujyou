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

### 🔲 v5.0 — Creator Factory OS — Full Platform _(Target: 2027-Q1)_

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
