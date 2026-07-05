# Version Summary: AIOS v5.2 RC

## Source Of Truth

- Version file: `src/core/version.py`
- `OS_VERSION`: `5.2`
- `OS_CODENAME`: `Google Workspace Sync Foundation`
- App title helper: `get_app_title()`
- Version label helper: `get_version_label()`

## Release Scope

This release candidate is a stabilization and release-preparation pass. It does not add new business features.

## Major Areas

- Creator Factory: local episode, production, asset, prompt, subtitle, and video workflow surfaces remain available.
- Business Factories: note, SNS, sales, accounting, analytics, and automation pages remain available.
- AIOS Control: Mission Control, AI Studio, Development Studio, AI CEO, Approval Center, and Approval Assistant remain available.
- Workspace Sync: committed defaults remain safe and local-first with `auth_mode=disabled`.

## Release Candidate Status

- Syntax: passing.
- JSON: passing.
- Smoke tests: passing.
- Streamlit startup: passing.
- Dashboard workflow access: passing.
- Live external sync: disabled by default.
