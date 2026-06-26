@echo off
chcp 65001 >nul

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

title Check Environment - AI動画工場

echo.
echo  ============================================
echo   AI動画工場 v4.1 — Environment Check
echo  ============================================
echo.

REM ── Python ───────────────────────────────────────────────────────────────────
echo  [Python]
python --version 2>&1 || echo    Not found in PATH
echo.

REM ── Git ───────────────────────────────────────────────────────────────────────
echo  [Git]
git --version 2>&1 || echo    Not found in PATH
echo.

REM ── Virtual environment ───────────────────────────────────────────────────────
echo  [Virtual Environment]
if exist "venv\Scripts\activate.bat" (
    echo    Path   : %ROOT%\venv
    call venv\Scripts\activate.bat
    echo    Status : Active
    echo.

    REM ── Streamlit (requires venv) ──────────────────────────────────────────────
    echo  [Streamlit]
    streamlit --version 2>&1 || echo    Not installed  ^(pip install streamlit^)
    echo.

    REM ── OpenAI (requires venv) ────────────────────────────────────────────────
    echo  [OpenAI]
    pip show openai 2>nul | find "Version:" || echo    Not installed  ^(pip install openai^)
    echo.

) else (
    echo    Not found
    echo    Run: python -m venv venv
    echo.
    echo  [Streamlit]
    echo    Cannot check — venv not active
    echo.
    echo  [OpenAI]
    echo    Cannot check — venv not active
    echo.
)

REM ── Project version ───────────────────────────────────────────────────────────
echo  [Project Version]
for /f "tokens=* delims=" %%l in ('findstr /i "caption" app.py 2^>nul') do (
    echo    %%l
    goto DONE_VER
)
echo    Not found in app.py
:DONE_VER
echo.

REM ── Server status ─────────────────────────────────────────────────────────────
echo  [Server Status]
netstat -an 2>nul | find ":8501" | find "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo    Streamlit is RUNNING on port 8501
    echo    URL: http://localhost:8501
) else (
    echo    Streamlit is NOT running
)
echo.

echo  ============================================
echo   Check complete.
echo  ============================================
echo.
pause
