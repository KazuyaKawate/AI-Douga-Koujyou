# AI動画工場 v4.1 — Windows Utility Scripts

This document describes every utility script included with AI動画工場 v4.1.

---

## Quick Reference

| Script | Purpose | How to run |
|--------|---------|-----------|
| `run_ai_factory.bat` | Launch the app | Double-click |
| `stop_streamlit.bat` | Stop the server | Double-click |
| `update_from_github.bat` | Pull latest version | Double-click |
| `backup_project.bat` | Create a ZIP backup | Double-click |
| `create_desktop_shortcut.ps1` | Create desktop shortcut | Right-click → Run with PowerShell |
| `check_environment.bat` | Verify installation | Double-click |

---

## 1. `run_ai_factory.bat` — Launch App

Starts AI動画工場 and opens it in your default browser.

**Behavior:**
1. Detects if Streamlit is already running on port 8501 — if so, opens the browser directly without starting a second instance.
2. Activates the Python virtual environment (`venv\Scripts\activate`).
3. Starts Streamlit in a dedicated **"AI動画工場 Server"** console window.
4. Polls TCP port 8501 every second (up to 60 s) until the server is accepting connections.
5. Opens `http://localhost:8501` in the default browser.
6. Pauses with an error message if the server fails to start within 60 seconds.

**To stop the server:** close the "AI動画工場 Server" window, or run `stop_streamlit.bat`.

---

## 2. `stop_streamlit.bat` — Stop Server

Safely stops the Streamlit server.

**Behavior:**
- Finds the process listening on TCP port 8501 using `Get-NetTCPConnection`.
- Sends a `Stop-Process -Force` signal to that PID.
- Prints the process name and ID before terminating.
- Reports if no server is running.

**Note:** This targets only the process bound to port 8501, not all Python processes.

---

## 3. `update_from_github.bat` — Pull Latest Release

Updates the project from GitHub and refreshes Python packages.

**Steps:**
1. `git pull` — fetches and merges the latest commits from `origin`.
2. `pip install -r requirements.txt` — installs any new or updated packages (skipped if `requirements.txt` does not exist or `venv` is not found).
3. `python scripts/check_project.py` — runs the project health check (skipped if the script does not exist).

**Requirements:** Git must be installed and in `PATH`. Run `check_environment.bat` to verify.

---

## 4. `backup_project.bat` — Create ZIP Backup

Creates a timestamped ZIP archive of all project data.

**Archive name:** `AI動画工場_Backup_YYYYMMDD_HHMM.zip`

**Included:**

| Path | Contents |
|------|---------|
| `config/` | Settings, characters, backgrounds, templates, agent registry |
| `project/` | All episode data, director plans, production state, exports |
| `assets/` | Icons, images, and other project assets |
| `docs/` | Project documentation |
| `README.md` | Project readme |
| `RELEASE_NOTES.md` | Release notes |

**Excluded:** `.git`, `.venv`, `venv`, `__pycache__`, `backups`, `.pyc` / `.pyo` files, `.env` files.

**Retention:** Automatically deletes older backups when more than 20 exist (keeps the 20 newest).

**Location:** `backups/` directory in the project root (created automatically).

---

## 5. `create_desktop_shortcut.ps1` — Desktop Shortcut

Creates a Windows desktop shortcut (`AI動画工場.lnk`) pointing to `run_ai_factory.bat`.

**Usage:**
```powershell
# Right-click the file → "Run with PowerShell"
# Or from a PowerShell terminal:
.\create_desktop_shortcut.ps1
```

**Icon resolution order:**
1. `assets\icon.ico` — project icon (preferred)
2. `venv\Scripts\python.exe` — Python icon from venv (fallback)
3. System `python.exe` — system Python icon (fallback)

**Note:** Place a custom `.ico` file at `assets\icon.ico` to use your own icon.

---

## 6. `check_environment.bat` — Environment Check

Displays the current installation status of all required components.

**Checks:**
- Python version
- Git version
- Virtual environment (`venv`) — path and active status
- Streamlit version (requires venv)
- OpenAI package version (requires venv)
- Project version (read from `app.py`)
- Server status — whether Streamlit is currently running on port 8501

Run this first if something is not working.

---

## Troubleshooting

### App won't start
1. Run `check_environment.bat` and fix any missing components.
2. Ensure `venv` exists: `python -m venv venv`
3. Install packages: `venv\Scripts\activate && pip install -r requirements.txt`

### Port 8501 already in use
Run `stop_streamlit.bat` to release the port, then try again.

### git pull fails
Ensure Git is installed (`git --version`) and you have internet access.

### Backup is very large
The `project/` directory may contain large media files. Consider excluding it from regular backups by editing `backup_project.bat`.

---

*AI動画工場 v4.1 — Windows Utility Pack*
