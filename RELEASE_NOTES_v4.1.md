# Release Notes — AI動画工場 v4.1 Stable

**Release date:** 2026-06-27  
**Status:** Stable Candidate — all health checks pass, zero runtime warnings  
**Git tag:** `v4.1`  
**Base:** v3.1 RC1 (commit `10ec23c`)

---

## New Features

### Project Manager — Central Control Hub (`pages/15_Project_Manager.py`)

Six-tab hub for managing the entire project lifecycle:

- **概要 (Overview)** — 6 live metrics (episode count, done/in-progress, director plans, exports, total GB); asset coverage bars; episode table with per-episode badges; series overview.
- **シリーズ管理 (Series)** — Create, rename, delete series; reorder episodes within a series; move episodes between series.
- **アナリティクス (Analytics)** — 30-second `@st.cache_data` scan; production coverage %; per-stage completion breakdown.
- **バックアップ (Backup)** — GUI front-end to the new backup engine; timestamped ZIP creation; restore with per-section overwrite controls; auto-prune (keeps 20 newest).
- **パッケージ (Package)** — Export a self-contained project ZIP (`export_project_zip`); import a package ZIP uploaded by the user (`import_project_zip`); MANIFEST.json validation including version compatibility check.
- **一括操作 (Batch Ops)** — Multi-episode select grid; bulk export packages; bulk production-stage update; bulk add-to-series.

**New modules:**

| File | Key additions |
|---|---|
| `src/utils/project_manager.py` | `load/save_project_settings`, series CRUD, `duplicate_episode`, `batch_rename_episodes`, `archive_episode`, `delete_episode` |
| `src/utils/backup_manager.py` | `create_backup`, `restore_backup`, `validate_package`, `export_project_zip`, `import_project_zip`, `get_recent_activity`, `hours_since_last_backup`, `_prune_old_backups` |

---

### Multi-Agent Production Studio (`pages/16_AI_Studio.py` + `src/agents/`)

Fully automated end-to-end pipeline driven by a 6-agent registry:

| Agent | Role |
|---|---|
| `ProducerAgent` | Calls `generate_episode_ai()` (OpenAI text); chains to Director |
| `DirectorAgent` | Calls `generate_plan_with_ai()` (OpenAI text); chains to Script |
| `ScriptAgent` | Validates voice script, SRT, image/video prompts; chains to Prompt |
| `PromptAgent` | Injects director scene directions into prompt files (sentinel prevents double-injection); chains to Editor |
| `EditorAgent` | Calls `create_export_package()`; non-fatal export failure; chains to Publisher |
| `PublisherAgent` | Builds `publish_report.json`; 5-item readiness checklist; no external API calls |

**Infrastructure (`src/agents/`):**

- `base_agent.py` — `Task` (fully serializable record with status/progress/depends_on); `TaskQueue` (file-backed JSON store in `project/tasks/*.json`); `BaseAgent` ABC with enable/disable DI and `get_info()` introspection.
- `agent_registry.py` — `AgentRegistry.run_task()` validates, marks RUNNING, delegates; `save_state/load_state` persists enabled flags and routing config to `config/agent_registry.json`.

**AI Studio page (4 tabs):**

- **ダッシュボード** — 6 system health metrics; 2-column agent card grid; pipeline flow diagram; recent task list with inline run buttons.
- **パイプライン実行** — Full episode config form; per-agent enable checkboxes; auto-chain mode (safety limit: 20 iterations); live stage status.
- **タスクキュー** — Filter by status/agent; inline progress bars, error display, retry/delete; input/output JSON viewers.
- **エージェント設定** — Runtime NEXT_AGENTS routing via multiselect; JSON config editor; registry export; architecture notes.

---

### Windows Utility Pack v4.1

Six ready-to-use scripts for Windows 11 users:

| Script | Function |
|---|---|
| `run_ai_factory.bat` | Port check → TCP poll loop (max 60 s) → open browser; dedicated server window with UTF-8 (`chcp 65001`) |
| `stop_streamlit.bat` | Kills port-8501 owner PID via `Get-NetTCPConnection`; confirms termination |
| `update_from_github.bat` | `git pull` → `pip install -r requirements.txt` → health check |
| `backup_project.bat` | Timestamped ZIP (`AI-Douga-Koujyou_Backup_YYYYMMDD_HHmm.zip`); exclusion filter; keep 20 newest |
| `create_desktop_shortcut.ps1` | WScript.Shell `.lnk` with 3-tier icon fallback; Japanese UI (`.ps1` is Unicode-native) |
| `check_environment.bat` | Reports Python / Git / venv / Streamlit / OpenAI / server status at a glance |

Supporting docs: `README_UTILITIES.md` (full reference + troubleshooting); `README.md` Quick Start table added.

---

## Bug Fixes

### Windows CMD cp932/UTF-8 Encoding Errors (critical)

**Symptom:** Double-clicking any `.bat` launcher produced `The syntax of the command is incorrect` before Streamlit started.

**Root cause:** `.bat` files were saved as UTF-8. Windows CMD reads them using the system code page (cp932 on Japanese Windows). Multi-byte UTF-8 sequences for non-ASCII characters produce undefined trailing bytes that corrupt CMD's parser.

**Fix (commit `a76f666`):** Replaced every non-ASCII character (Japanese text, box-drawing characters, em dashes) across all five `.bat` files with ASCII equivalents (0x00–0x7F). ASCII bytes are identical in UTF-8 and cp932, so the encoding mismatch disappears entirely. An enforcement comment was added to the top of each `.bat` file. Japanese UI text is kept only in `.ps1` files, where PowerShell is Unicode-native.

---

## Health Check Improvements

### `scripts/check_project.py` now covers the full v4.1 codebase (commit `c8394a3`)

The script was last updated for v2.x. v3.1 and v4.0 additions were invisible to it.

| Category | Before | After |
|---|---|---|
| Required folders | 13 | 14 (+`src/agents`) |
| Required files | 29 | 53 (+24) |
| Pages checked | 8 of 16 | 16 of 16 |
| src/core files checked | 2 of 5 | 5 of 5 |
| src/utils files checked | 5 of 8 | 8 of 8 |
| src/agents files checked | 0 of 9 | 9 of 9 |

Health check now exits 0 with `STATUS: OK` and zero false negatives on a complete installation.

**Additional checks confirmed clean (not script output, but run as part of v4.1 sign-off):**
- All 57 `.py` files pass `python -m py_compile`
- All 20 `src/` modules import cleanly under `-W all -X dev` with zero `DeprecationWarning` or `SyntaxWarning`
- All `read_text()` / `write_text()` calls carry `encoding="utf-8"`
- `openai-whisper>=20231117` is a valid PEP 440 date-based version; installed version is `20250625`

---

## Known Limitations

| Area | Detail |
|---|---|
| External media generation | Image, video, and audio providers are manual-only. No Runway, ElevenLabs, or Stable Diffusion API calls. Users export prompts and import assets manually. |
| FFmpeg assembly | `ffmpeg_utils.py` wrappers exist but are not yet wired to an automated assembly page. Users assemble clips in their own editor. |
| Agent concurrency | The TaskQueue is file-backed JSON. Concurrent writes from multiple browser tabs can cause race conditions. Single-user / single-tab operation is assumed. |
| Whisper transcription | `whisper_client.py` is present but not exposed in any page UI yet. |
| Agent auto-chain limit | Auto-chain mode caps at 20 iterations to prevent infinite loops. Long pipelines with retries may require manual re-trigger. |
| Config JSON bootstrap | `config/settings.json`, `config/characters.json`, `config/backgrounds.json`, and `config/prompt_templates.json` are created on first use. The health check correctly marks them `[----]` on a fresh install; this is expected behavior, not an error. |
| `.bat` file paths | All `.bat` scripts handle Japanese directory paths correctly at runtime via `%~dp0`. However, the literal ASCII-only content constraint means Japanese text cannot appear as string literals inside `.bat` files. |

---

## Next Milestone — Dashboard Factory

**Target:** v4.2 / v5.0

The Dashboard Factory milestone aims to make production status visible at a glance and reduce manual steps for common workflows:

- **Automated FFmpeg Assembly** — wire `ffmpeg_utils.py` to a new assembly page; one-click merge of approved image/video/audio assets into a finished episode file.
- **Whisper Transcription UI** — expose `whisper_client.py` on a new Transcription page; auto-generate SRT from uploaded audio.
- **Live Production Dashboard** — real-time per-episode status board with auto-refresh; filter by stage, series, or date; quick-action buttons (mark stage, export, open director).
- **Agent Concurrency Safety** — replace file-lock-free JSON store with SQLite or a write-queue to support multi-tab usage.
- **Cloud Backup Integration** — connect the `MANIFEST.json` reserved fields (`cloud_backup_id`, `user_id`) to a storage endpoint; scheduled auto-backup.
- **Runway / ElevenLabs Provider** — implement `image_provider_runway.py` and `audio_provider_elevenlabs.py` behind the existing provider interface; gated by API key presence in `.env`.
