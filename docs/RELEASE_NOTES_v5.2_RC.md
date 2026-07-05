# AIOS v5.2 Release Candidate Notes

Release date: 2026-07-05

## Summary

AIOS v5.2 RC is a stabilization release for the Creator Factory OS / AI動画工場 codebase. It prepares the project for release by tightening runtime compatibility, local safety, workflow registration, release metadata, and the main Streamlit dashboard.

## Completed

- Runtime API mismatches fixed for AI router access, task model usage, and task type defaults.
- Workflow executors required by `config/workflow_definitions/note_daily.json` are registered and discoverable.
- Development dependencies and pytest discovery are documented.
- Smoke tests added for syntax, JSON, kernel startup, workflow registry, virtual AI router, Streamlit import, and safe workflow execution.
- Filesystem safety layer added for workspace-confined file operations.
- Atomic JSON persistence added for JSON managers and state files.
- Version source of truth centralized in `src/core/version.py`.
- Dashboard workflow layout reorganized into grouped sections.
- Google Workspace sync remains disabled by default, with graceful optional dependency and credential handling.

## Verification

- `pytest`: passed.
- Python syntax check: passed.
- JSON validation: passed.
- Streamlit startup: passed.
- Dashboard browser verification: passed.
- Workflow, memory, AI router, business engine, Creator Factory, and Video Factory probes: passed.

## Known Limitations

- Live Google Sheets production sync requires local credentials and optional packages; it is intentionally disabled in committed config.
- External paid generation APIs for image, video, and voice remain out of scope for this release candidate.
- Browser verification covers dashboard availability and workflow links, not every page interaction.

## Release Decision

AIOS v5.2 is ready as a Release Candidate for local-first validation and user acceptance testing.
