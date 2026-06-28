# Changelog — Creator Factory OS (旧: AI動画工場)

All notable changes to this project are documented in this file.  
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).  
Versions are cumulative; each release builds on the previous stable base.

---

## [v5.2 Phase 4-5] — 2026-06-28 — Google Sheets 本番シート同期（Production Sync）

**Codename:** Production Sync  
**Upgrade path:** v5.2 Phase 4-4 → v5.2 Phase 4-5 (additive, no breaking changes)

### What changed

- **`src/workspace/sheets_sync.py`**: `SHEET_MAPPINGS` を実データに合わせて全面修正（`kpi_targets`: フィールド名を `targets.{}` ネストに対応、`revenue_expense`: key_field を `"date"` に変更・ドット記法廃止・3列構成に簡略化、`note_articles`: key_field を `"id"` に修正・`published_at` / `actual_revenue` / `score_total` / `score_grade` に対応）。`extract_flat_row(target_id, raw_row)` 追加（ターゲット別ネスト構造フラット化）。`read_flat_rows(target_id, local_file)` 追加（Phase 4-5専用ローダー）。`read_local_data()` の `history` 空リストバグ修正（空リストはスキップ）。
- **`src/workspace/sheet_writer.py`**: `write_sheet_upsert()` 追加。処理: ヘッダー行確認・初期化 → key_fieldで既存行インデックス → 追加/更新のみ（行削除なし）。`_col_letter()` 追加（列番号→アルファベット変換）。`get_writer_status()` フェーズラベルを Phase 4-5 に更新。
- **`src/workspace/sync_executor.py`**: `run_production_sync()` 追加（Phase 4-5専用: KPI / Revenue / Notes の3シートにupsert同期）。`_PHASE45_TARGETS` frozenset 追加。`_preview_row()` 追加。`get_connector_health()` フェーズラベルを Phase 4-5 に更新。モジュールdocstringを Phase 4-5 に更新。
- **`pages/25_Development_Studio.py`**: Phase 4-5 パネル追加（差分プレビューボタン → 確認チェックボックス → 本番同期ボタン → ロールバック手順）。`run_production_sync` インポート追加。
- **`scripts/check_project.py`**: Phase 4-5 ヘルスチェックセクション追加（3ターゲットのflat_rows確認・run_production_sync dry-run・allow_write guard）。
- **`config/workspace_settings.json` meta**: `version` → `"5.2 Phase 4-5"`、`phase` → `"4-5: production sync (KPI / Revenue / Notes)"`。

### What did not change

- `allow_write` パラメータは全関数でデフォルト `False`。UIボタン経由でのみ `True` を渡す。コミット済みコードに `allow_write=True` は含まれない。
- `config/workspace_settings.json` の `auth_mode` は `"disabled"` のまま（コミット済み安全デフォルト）。
- `dry_run_default: true`、`auto_sync: false` 変更なし。
- `config/workspace_local.json` および `credentials/service-account.local.json` はローカル専用・コミットなし。
- `run_test_write()` および `_PRODUCTION_WORKSHEETS` blocklist は Phase 4-4 のまま維持。

---

## [v5.2 Phase 4-4] — 2026-06-28 — Google Sheets Test Worksheet Append

**Codename:** Test Worksheet Append  
**Upgrade path:** v5.2 Phase 4-3 → v5.2 Phase 4-4 (additive, no breaking changes)

### What changed

- **`src/workspace/sheet_writer.py`**: Implemented actual `gspread.append_row()` in `write_rows()`. Added `"allow_write": False` to `get_writer_status()` — fixes the Phase 4-2 health-check `[ERR]` bug (was checking `write_enabled` instead of `allow_write`). Added `build_client` import.
- **`src/workspace/sync_executor.py`**: Added `run_test_write()` — dedicated Phase 4-4 function. Appends exactly one tagged test row to `test_worksheet_name`. Never touches production worksheets. Guards: `_PRODUCTION_WORKSHEETS` blocklist, `manual_execute=True`, `allow_write=True` (passed only from UI button, never committed). Added `load_local_settings` import.
- **`src/workspace/sync_validator.py`**: Added `test_worksheet_name` and `has_test_worksheet` to `get_local_config_status()` return dict.
- **`pages/25_Development_Studio.py`**: Added Phase 4-4 test write panel (test_worksheet_name check → dry-run preview → checkbox confirmation → write button → rollback instructions). Replaced the permanently-disabled "Manual Execute" button. Added `run_test_write` import.
- **`scripts/check_project.py`**: Fixed write guard check (now checks `allow_write` not `write_enabled`). Added Phase 4-4 section: `test_worksheet_name` check, production worksheet blocklist, `run_test_write` dry-run, `allow_write` guard.
- **`config/workspace_settings.json` meta**: `version` → `"5.2 Phase 4-4"`.

### What did not change

- `allow_write` parameter in `write_rows()` still defaults to `False` — never committed as `True`.
- `config/workspace_settings.json` `auth_mode` remains `"disabled"` (safe committed default).
- `dry_run_default: true`, `auto_sync: false` unchanged.
- Production worksheets (KPI / Revenue / Notes / SNS / Sales) are blocked by `_PRODUCTION_WORKSHEETS` frozenset in `run_test_write()`.
- `config/workspace_local.json` and `credentials/service-account.local.json` remain local-only, never committed.

---

## [v5.2 Phase 4-3] — 2026-06-28 — Google Sheets Live Read-Only Connection Verified

**Codename:** Live Read-Only Connection  
**Upgrade path:** v5.2 Phase 4-2 → v5.2 Phase 4-3 (no breaking changes, no new dependencies)

### What changed

- **Live Google Sheets connection confirmed:** First end-to-end live read (`test_read_connection`) completed against a real spreadsheet using `gspread` + service account via `load_merged_settings()`. Connection succeeded; KPI sheet accessible. Writes remain blocked (`allow_write=False`).
- **`config/workspace_settings.json` meta:** `version` → `"5.2 Phase 4-3"`, `phase` → `"4-3: live read-only connection verified"`.
- **Phase label strings updated** in `sheet_reader.py`, `sheet_writer.py`, `sync_executor.py` — no logic changes.
- **Docs updated:** CHANGELOG, ROADMAP, README, ARCHITECTURE.md, google_sheets_setup.md reflect Phase 4-3 completion.

### What did not change

- `allow_write` remains `False` — no writes possible.
- `config/workspace_settings.json` `auth_mode` remains `"disabled"` (safe committed default).
- `config/workspace_local.json` and `credentials/service-account.local.json` remain local-only, git-ignored, not committed.
- `dry_run_default: true`, `auto_sync: false` unchanged.
- No production logic changes.

---

## [v5.2 Phase 4-2] — 2026-06-27 — Google Sheets Local Config Override

**Codename:** Google Sheets Local Config Override  
**Upgrade path:** v5.2 Phase 4-1 → v5.2 Phase 4-2 (additive, no breaking changes)

### Added
- `config/workspace_local.json` — local-only runtime config (git-ignored); overrides committed `workspace_settings.json` at runtime; allows setting `auth_mode`, `service_account_file`, `spreadsheet_id`, `worksheet_name`, `range` without modifying committed config
- `src/workspace/sync_validator.load_local_settings()` — loads `config/workspace_local.json`; returns `{}` if missing (normal); never raises
- `src/workspace/sync_validator.load_merged_settings()` — committed settings deep-merged with local overrides; local keys win; used by all runtime paths
- `src/workspace/sync_validator.get_local_config_status()` — summary dict of local config: exists, auth_mode, has_spreadsheet_id, has_service_account_file, is_active
- `.gitignore`: `config/workspace_local.json` added (explicit ignore)

### Changed
- `src/workspace/google_auth.get_auth_config()` — when `settings=None`, now calls `load_merged_settings()` instead of `load_settings()`; committed auth_mode always "disabled" but local override activates service_account at runtime
- `src/workspace/google_auth.build_client()` — same: uses `load_merged_settings()` for default
- `src/workspace/sheet_reader.read_sheet()` — inline settings reload now uses `load_merged_settings()` so local spreadsheet_id is honoured
- `src/workspace/sheet_reader` — phase label updated to "Phase 4-2"
- `src/workspace/sync_executor.test_read_connection()` — uses `load_merged_settings()` when settings=None
- `src/workspace/sync_executor` — imports `load_merged_settings`; phase label updated to "Phase 4-2"
- `pages/25_Development_Studio.py` — Phase 4-2 section: local config status panel (exists, auth_mode, spreadsheet_id, worksheet_name), dependency metrics, credential file check, setup hint expander with JSON template, Read Connection Test now passes merged settings; manual execute warning updated
- `scripts/check_project.py` — Phase 4-2 section: workspace_local.json git-ignore check, git-tracking check, local config values (no cred contents), test_read_connection with merged settings, write guard check

### Design decisions
- Committed `workspace_settings.json` always has `auth_mode=disabled` — safe for all contributors
- Local override: only `config/workspace_local.json` activates service_account; never committed
- `load_merged_settings()` is the single merge point; all runtime entry points call it when settings=None
- Missing `workspace_local.json` → `load_local_settings()` returns `{}` → `load_merged_settings()` returns committed settings unmodified; backward-compatible
- Health check: missing local config / cred file = WARN not STATUS fail; app is fully functional without them (auth_mode=disabled mode)

---

## [v5.2 Phase 4-1] — 2026-06-27 — Google Sheets Read-Only Connection

**Codename:** Google Sheets Read-Only Connection  
**Upgrade path:** v5.2 Phase 3 → v5.2 Phase 4-1 (additive, no breaking changes)

### Added
- `src/workspace/google_auth.build_client()` — fully implemented; builds live gspread client for `service_account` mode (lazy imports gspread + google.oauth2); returns structured `{status, client, auth_mode, error, icon, label}` dict; never crashes; OAuth returns `"oauth_pending"` placeholder for Phase 4-2+
- `src/workspace/sheet_reader.read_sheet_detail()` — rich return dict `{ok, rows, row_count, source, error, sheet_name, auth_mode}`; calls live gspread for service_account mode
- `src/workspace/sync_executor.test_read_connection()` — read-only connection test; builds client, calls `read_sheet_detail()`, returns safe summary `{ok, auth_mode, client_status, deps_ready, sheet_tested, row_count, source, error, duration_ms}`

### Changed
- `src/workspace/google_auth.py` — `build_client()` now constructs real gspread.Client for service_account; adds OAuth pending stub; dep + file checks before any import attempt; all paths return safe dict
- `src/workspace/sheet_reader.py` — `read_sheet()` now calls `build_client()` and real `gspread` API for service_account mode; resolves `spreadsheet_id` from `google_sheets` or legacy field; `get_reader_status()` phase label updated to Phase 4-1
- `src/workspace/sheet_writer.py` — quad-lock write guard added: 4th lock `allow_write=False` (always False in Phase 4-1, enabling Phase 4-2+ opt-in); `get_writer_status()` phase label updated
- `src/workspace/sync_executor.py` — imports `build_client`, `get_dependency_status`, `read_sheet_detail`; `get_connector_health()` phase label updated; `deps_ready` added to health dict
- `.gitignore` — added explicit `credentials/service-account.local.json` line
- `config/workspace_settings.json` — `meta.version` → "5.2 Phase 4-1"; `credential_paths.service_account_file` → `"credentials/service-account.local.json"`
- `pages/25_Development_Studio.py` — Tab 10: Phase 4-1 section added with dependency metrics (gspread, google-auth), credential file status, auth_mode, spreadsheet_id, worksheet_name, "Read Connection Test" button (calls `test_read_connection()`), success/error detail display, pip install hint on deps_missing
- `scripts/check_project.py` — Phase 4-1 section: service-account.local.json tracking check, committed auth_mode=disabled check, `sheet_writer` write-blocked check, `test_read_connection()` import + execution result; missing packages are WARN not STATUS fail

### Design decisions
- `allow_write=False` is the 4th lock in `write_rows()`; existing call sites (`run_execute`) continue to pass `manual_execute=True` but will still be blocked by `allow_write` — no risk of accidental writes in Phase 4-1
- `build_client()` uses lazy imports (`import gspread` inside function body) — module loads cleanly even when gspread is not installed
- `test_read_connection()` picks test worksheet from `google_sheets.worksheet_name` or falls back to first enabled target's `sheet_name`
- `credentials/service-account.local.json` is explicitly named in `.gitignore`; health check verifies it is NOT tracked by git
- gspread/google-auth missing → WARN in health check, never STATUS fail; auth_mode=disabled is always the safe fallback

---

## [v5.2 Phase 3] — 2026-06-27 — Google Sheets Credential Safety & gspread Readiness

**Codename:** Google Sheets Credential Safety & gspread Readiness  
**Upgrade path:** v5.2 Phase 2 → v5.2 Phase 3 (additive, no breaking changes)

### Added
- `credentials/` — credential storage folder (tracked via `.gitkeep` only; real JSON files excluded by `.gitignore`)
- `credentials/.gitkeep` — placeholder so the folder is tracked without real credential files
- `docs/google_sheets_setup.md` — step-by-step guide for optional Google Sheets connection; covers security principles, gspread install, service account creation, `workspace_settings.json` fields; auth_mode stays `disabled` by default
- `src/workspace/sync_validator.check_gitignore_protections()` — verifies `.gitignore` contains all required credential protection patterns
- `src/workspace/sync_validator.check_credentials_gitkeep()` — verifies `credentials/.gitkeep` exists and no real JSON files are present in `credentials/`
- `src/workspace/sync_validator.check_phase3_dependencies()` — checks gspread + google-auth via `importlib.metadata`; never raises; no circular import
- `src/workspace/sync_validator.get_phase3_readiness()` — composite Phase 3 safety check: .gitignore, .gitkeep, no-cred-committed, auth_mode=disabled, gspread/google-auth status, spreadsheet_id status

### Changed
- `src/workspace/google_auth.py` — docstring updated to Phase 3; `get_dependency_status()` added (gspread + google-auth check via importlib.metadata); `build_client()` placeholder updated for Phase 3 context
- `src/workspace/sheet_reader.py` — docstring updated to Phase 3; dependency guard added before credential check
- `src/workspace/sheet_writer.py` — docstring updated to Phase 3; dependency guard (gspread + google-auth) added to `write_rows()`; `get_writer_status()` phase label updated to "Phase 3"
- `src/workspace/sync_executor.py` — docstring updated to Phase 3; `get_connector_health()` phase label updated to "Phase 3 (gspread readiness)"
- `config/workspace_settings.json` — `meta.version` updated to "5.2 Phase 3"; `connector` section updated to Phase 3
- `.gitignore` — added `credentials/` exclusion with `!credentials/.gitkeep` exception; added `*.service-account.json`, `*service_account*.json`, `*oauth*.json`, `token.json`
- `pages/25_Development_Studio.py` — Tab 10: caption updated to Phase 3; Phase 3 readiness checklist section added (calls `get_phase3_readiness()`; per-check status with 🔒 safety / 📦 optional distinction); Manual Execute button help text updated to Phase 4+
- `scripts/check_project.py` — added `credentials/.gitkeep` and `docs/google_sheets_setup.md` to REQUIRED_FILES; new "Google Sheets Phase 3 安全性 & gspread 準備状況" section: credentials folder + .gitkeep check, google_sheets_setup.md check, .gitignore pattern check, gspread/google-auth package check, composite `get_phase3_readiness()` result

### Design decisions
- `auth_mode` remains `"disabled"` — Phase 3 is safety + readiness only; no live API calls
- `credentials/` folder is tracked via `.gitkeep`; all real JSON files excluded in `.gitignore`
- `check_phase3_dependencies()` in `sync_validator` uses `importlib.metadata` directly to avoid circular import with `google_auth.py`
- gspread/google-auth absence is NOT a blocker — it is flagged as optional (Phase 4+ requirement)
- `get_phase3_readiness()` returns structured `checks` list for both UI display and CLI health check

---

## [v5.2 Phase 2] — 2026-06-27 — Google Sheets Connector Foundation

**Codename:** Google Sheets Connector Foundation  
**Upgrade path:** v5.2 Phase 1 → v5.2 Phase 2 (additive, no breaking changes)

### Added
- `src/workspace/google_auth.py` — credential configuration loader; `get_auth_config()`, `get_credential_status()`, `build_client()` placeholder; `auth_mode` defaults to `"disabled"`; never reads credential file contents; never committed credentials
- `src/workspace/sheet_reader.py` — read abstraction; `read_sheet()` returns SAMPLE_SHEET_DATA when `auth_mode="disabled"` (no API call); `get_reader_status()`; Phase 3+ API hook ready
- `src/workspace/sheet_writer.py` — write abstraction with triple-lock guard (`auth_mode != disabled` AND `dry_run=False` AND `manual_execute=True`); default preview-only; `write_rows()`, `get_writer_status()`; Phase 3+ gspread hook ready
- `src/workspace/sheet_diff.py` — pure diff engine; `diff_records()` returns `added / updated / removed / conflicts / unchanged`; `summarize_diff()` one-liner; no I/O
- `src/workspace/sync_executor.py` — orchestrator; `run_preview()` (steps 1-5, no writes), `run_execute()` (step 6, triple-locked), `get_connector_health()` (dashboard-safe read-only)

### Changed
- `src/workspace/sync_engine.py` — updated docstring to Phase 2; `get_sync_health()` now includes `connector` sub-dict from `sync_executor.get_connector_health()`
- `src/workspace/sheets_sync.py` — added `key_field` to all 5 `SHEET_MAPPINGS` entries (used by `sheet_diff.diff_records()`)
- `src/workspace/sync_validator.py` — added `validate_connector_settings()` (validates auth_mode, file paths), `check_no_credentials_committed()` (scans root + config/ for known credential file patterns)
- `config/workspace_settings.json` — added `connector` section: `auth_mode="disabled"`, `service_account_file=""`, `oauth_client_file=""`, `last_preview=null`
- `pages/25_Development_Studio.py` — Tab 10 (Workspace Sync) upgraded to Phase 2: security warning banner, auth mode + credential status display, `check_no_credentials_committed()` result, connection status, full summary metrics, sheet target list, diff preview button (calls `sync_executor.run_preview()`), connector validation, manual dry-run button, manual execute button (disabled when `auth_mode=disabled`), sync history
- `pages/8_Dashboard.py` — Workspace Sync summary expanded: added `auth_mode`, `dry_run`, `target_count`, `conflict_count` (connector health row)
- `pages/17_Mission_Control.py` — Section 7.14 expanded: renamed to "Workspace Sync / Google Sheets Connector", added 8 metrics (connection, auth_mode, targets, conflicts, dry-run, sync total, last_preview, conflict_count)
- `pages/26_AI_CEO.py` — CEO Brief Workspace Sync section expanded: added 4 connector metrics (auth_mode, targets, last_preview, conflict_count) when `connector` dict present in snapshot
- `scripts/check_project.py` — added 5 new connector files to `REQUIRED_FILES`; `Workspace Sync データ` section now shows `auth_mode`; new `Google Sheets Connector (v5.2 Phase 2)` section: module file existence + size, credential-file scan, auth_mode default check, `sync_executor` import test, `py_compile` of all 5 connector modules

### Design decisions
- Triple-lock write guard (`auth_mode`, `dry_run`, `manual_execute`) is enforced in code, not just configuration
- `auth_mode="disabled"` is the only safe default — all operations are dry-run until explicitly reconfigured locally
- Credential files are NEVER stored in the repository; `check_no_credentials_committed()` enforces this at health-check time
- `sheet_diff.py` is pure logic (no I/O) — testable in isolation without any Google API or file system access
- Phase 3+ gspread integration requires only filling in two marked stubs: `build_client()` in `google_auth.py` and the API call section in `sheet_reader.read_sheet()` / `sheet_writer.write_rows()`

---

## [v5.2 Phase 1] — 2026-06-27 — Google Workspace Sync Foundation

**Codename:** Google Workspace Sync Foundation  
**Upgrade path:** v5.1 Phase 2 → v5.2 Phase 1 (additive, no breaking changes)

### Added
- `src/workspace/__init__.py` — workspace sync package (v5.2)
- `src/workspace/sync_models.py` — TypedDicts: SyncTarget, SyncRecord, SyncPreview, SyncConflict; `make_sync_record()`; STATUS_ICONS, CONNECTION_ICONS
- `src/workspace/sync_history.py` — sync history logging; load/save `config/sync_history.json`; `log_sync()`, `get_summary()`, `get_recent()`
- `src/workspace/sync_validator.py` — read-only config validation; `validate_settings()`, `get_connection_status()`, `get_enabled_targets()`; never makes API calls
- `src/workspace/sheets_sync.py` — Google Sheets column mapping definitions for 5 targets (KPI, Revenue, Notes, SNS, Sales); `read_local_data()`, `prepare_mapping()`; no API calls
- `src/workspace/sync_engine.py` — sync orchestration; `generate_preview()`, `run_dry_run()`, `run_sync()` (Phase 1: always dry-run), `get_sync_health()`; manual execution only; no external API calls in Phase 1
- `config/workspace_settings.json` — connection settings, 5 sync targets, `dry_run_default=true`, `enabled=false`, `auto_sync=false`
- `config/sync_history.json` — empty sync history store
- `reports/workspace/` — directory for sync reports

### Changed
- `src/core/version.py` — OS_VERSION → "5.2", OS_CODENAME → "Google Workspace Sync Foundation"
- `src/aiceo/executive_engine.py` — added Workspace Sync section: reads `get_sync_health()` into `snap["workspace_sync"]`
- `pages/25_Development_Studio.py` — added "🔄 Workspace Sync" tab (tab 10): connection status banner, summary metrics, validation errors, sync preview per target, dry-run button, sync history table
- `pages/8_Dashboard.py` — Workspace Sync summary strip (connection status, last sync, sync total, conflict count)
- `pages/17_Mission_Control.py` — Workspace Sync card (Section 7.14): connection, dry-run mode, sync total, conflicts
- `pages/26_AI_CEO.py` — Workspace Sync health display in CEO Brief tab (read-only; 4 metrics; "never executes" caption)
- `scripts/check_project.py` — added `src/workspace/` and `reports/workspace` to REQUIRED_FOLDERS; all 6 src/workspace files to REQUIRED_FILES; config files to OPTIONAL_FILES; Workspace Sync data section
- `docs/ARCHITECTURE.md` — updated to v5.2

### Design decisions
- Phase 1 is intentionally read-only; `run_sync()` always delegates to `run_dry_run()` — actual Sheets writes are Phase 2 (google-auth + gspread)
- `auto_sync: false` hardcoded in settings and validated to be always false
- `get_sync_health()` is safe for AI CEO integration (read-only, no side effects)
- Dry-run records sync history so future sessions can see execution timeline

---

## [v5.1 Phase 2] — 2026-06-27 — Module SDK Self-Registration Foundation

**Codename:** Module SDK Self-Registration Foundation  
**Upgrade path:** v5.1 Phase 1 (Approval Center) → Phase 2 (additive, no breaking changes)

### Added
- `config/module_registry.json` — exported registry snapshot (SDK v5.1, 11 modules, 0 invalid)

### Changed
- `src/sdk/module_manifest.py` — extended MODULE_INFO schema: `module_id` (auto-slugified), `display_name`, `sdk_version`, `minimum_os_version`, `entrypoint`, `package_path`, `status` (stable/beta/alpha/deprecated/experimental); added `SDK_VERSION = "5.1"`, `MODULE_STATUSES`, `_slugify()`; all 11 BUILTIN_MANIFESTS updated with explicit ids, package paths, entrypoints, and statuses
- `src/sdk/module_loader.py` — discovery now checks both `MODULE_INFO` (new canonical) and `MODULE_MANIFEST` (legacy); added `load_all_with_errors()` for diagnostics; added `get_manifest_by_id()`
- `src/sdk/module_validator.py` — validates new fields: `status` enum, `module_id` format, `sdk_version` / `minimum_os_version` types; per-module results now include `module_id`, `module_type`, `version`, `status`
- `src/sdk/registry_builder.py` — added `export_registry() → Path` (writes config/module_registry.json on demand), `load_exported_registry()`, `get_by_id()`, `get_status_icon()`, `STATUS_ICONS`; `get_summary()` now includes `sdk_version`, `by_status`, `registry_exported`, `registry_age`
- `pages/25_Development_Studio.py` — new "📦 Module SDK" tab (tab 9): summary metrics (SDK version, total/valid/invalid, type breakdown), per-module expandable cards (all fields visible), registry export button, validation error display
- `pages/8_Dashboard.py` — Module SDK summary strip (SDK version, total, valid, invalid)
- `pages/17_Mission_Control.py` — Module SDK metrics (SDK version, total, valid, invalid) appended to Development Studio section
- `scripts/check_project.py` — updated Module SDK section to show `config/module_registry.json` details and full ModuleRegistry validation summary with per-invalid-module error reporting; added `config/module_registry.json` to OPTIONAL_FILES

### Design decisions
- `MODULE_INFO` is the new canonical attribute name; `MODULE_MANIFEST` still accepted for backward compat
- `module_id` auto-generated from module_name via ASCII slugification; explicit ids set in BUILTIN_MANIFESTS for Japanese-named modules (e.g. `video-factory`, `note-factory`)
- `make_manifest()` signature unchanged — all new fields are kwargs with defaults
- `export_registry()` is write-on-demand only; never called automatically

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
