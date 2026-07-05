# Dependency Installation

AIOS keeps the base install small. Install optional integrations only when you need them.

## Base runtime

```powershell
pip install -r requirements.txt
```

## Development tools

Required for test discovery and browser checks:

```powershell
pip install -r requirements_dev.txt
```

Includes:

- pytest
- playwright

## Optional Google integrations

Required only for live Google Sheets sync or Gemini provider usage. These are intentionally not required for the local-first development workflow.

```powershell
pip install gspread google-auth google-genai
```

Use cases:

- `gspread`: Google Sheets worksheet read/write client
- `google-auth`: Google service-account credentials support
- `google-genai`: Gemini provider support via `google.genai`

Security note: keep real credentials in ignored local files such as `config/workspace_local.json` and `credentials/service-account.local.json`. Do not commit API keys or credential JSON files.
