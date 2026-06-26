@echo off
REM ================================================================
REM  update_from_github.bat  --  AI-Douga-Koujyou v4.1 updater
REM
REM  IMPORTANT: This file must remain ASCII-only (0x00-0x7F).
REM  See run_ai_factory.bat header for the full explanation.
REM ================================================================

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

title Update AI-Douga-Koujyou

echo.
echo  ============================================
echo   AI-Douga-Koujyou v4.1 - Update from GitHub
echo  ============================================
echo.

REM -- [1/3] git pull
echo  [1/3] Pulling latest changes from GitHub...
git pull
if errorlevel 1 (
    echo.
    echo  [ERROR] git pull failed.
    echo  Verify your network connection and git configuration.
    pause
    exit /b 1
)
echo.

REM -- [2/3] pip install
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
        echo  [WARN] Virtual environment not found. Skipping pip install.
        echo  To create one: python -m venv venv ^&^& pip install -r requirements.txt
    )
) else (
    echo  [2/3] requirements.txt not found. Skipping pip install.
)
echo.

REM -- [3/3] Project health check
echo  [3/3] Running project health check...
if exist "scripts\check_project.py" (
    python scripts\check_project.py
    if errorlevel 1 (
        echo  [WARN] Health check reported issues.
    )
) else (
    echo  [INFO] scripts\check_project.py not found. Skipping health check.
)
echo.

echo  ============================================
echo   Update Complete
echo  ============================================
echo.
pause
