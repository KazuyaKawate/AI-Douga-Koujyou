@echo off
chcp 65001 >nul

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

title Update AI動画工場

echo.
echo  ============================================
echo   AI動画工場 v4.1 — Update from GitHub
echo  ============================================
echo.

REM ── [1/3] git pull ────────────────────────────────────────────────────────────
echo  [1/3] Pulling latest changes from GitHub...
git pull
if errorlevel 1 (
    echo.
    echo  [ERROR] git pull failed.
    echo  Verify your network connection and that git is configured correctly.
    pause
    exit /b 1
)
echo.

REM ── [2/3] pip install ─────────────────────────────────────────────────────────
if exist "requirements.txt" (
    echo  [2/3] Installing / updating Python packages...
    if exist "venv\Scripts\activate.bat" (
        call venv\Scripts\activate.bat
        pip install -r requirements.txt --quiet
        if errorlevel 1 (
            echo  [WARN] pip install reported errors. Review the output above.
        ) else (
            echo  Packages up to date.
        )
    ) else (
        echo  [WARN] Virtual environment not found — skipping pip install.
        echo  To create one: python -m venv venv ^&^& pip install -r requirements.txt
    )
) else (
    echo  [2/3] requirements.txt not found — skipping pip install.
)
echo.

REM ── [3/3] Project health check ───────────────────────────────────────────────
echo  [3/3] Running project health check...
if exist "scripts\check_project.py" (
    python scripts\check_project.py
    if errorlevel 1 (
        echo  [WARN] Health check reported issues.
    )
) else (
    echo  [INFO] scripts\check_project.py not found — skipping health check.
)
echo.

echo  ============================================
echo   Update Complete
echo  ============================================
echo.
pause
