@echo off
chcp 65001 >nul

REM ── Resolve project root from this script's location ─────────────────────────
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

title AI動画工場 v4.1

echo.
echo  ============================================
echo   AI動画工場 v4.1
echo   Multi-Agent Production Studio
echo  ============================================
echo.

REM ── Check if already running on port 8501 ────────────────────────────────────
netstat -an 2>nul | find ":8501" | find "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo  [INFO] AI動画工場 is already running at http://localhost:8501
    echo  Opening browser...
    start "" "http://localhost:8501"
    echo.
    exit /b 0
)

REM ── Virtual environment check ─────────────────────────────────────────────────
if not exist "venv\Scripts\activate.bat" (
    echo  [ERROR] Virtual environment not found.
    echo.
    echo  First-time setup:
    echo    1. python -m venv venv
    echo    2. venv\Scripts\activate
    echo    3. pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM ── Activate venv ─────────────────────────────────────────────────────────────
echo  Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo  [ERROR] Failed to activate virtual environment.
    pause
    exit /b 1
)

REM ── Start Streamlit server in a dedicated window ──────────────────────────────
echo  Starting AI動画工場 server...
start "" /d "%ROOT%" cmd /k "chcp 65001 >nul && title AI動画工場 Server && call venv\Scripts\activate.bat && streamlit run app.py --server.port 8501 --server.headless true"

REM ── Wait until port 8501 is accepting TCP connections (max 60 s) ──────────────
echo  Waiting for server to become ready
set /a N=0
:WAIT
set /a N+=1
if %N% gtr 60 (
    echo.
    echo  [ERROR] Server did not respond after 60 seconds.
    echo  Check the "AI動画工場 Server" window for error details.
    pause
    exit /b 1
)
<nul set /p "=."
timeout /t 1 /nobreak >nul
powershell -NonInteractive -Command "try { $c=New-Object Net.Sockets.TcpClient; $c.Connect('localhost',8501); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 goto WAIT

REM ── Open browser ──────────────────────────────────────────────────────────────
echo.
echo  Server is ready!
start "" "http://localhost:8501"
echo.
echo  AI動画工場 is running at http://localhost:8501
echo  Run stop_streamlit.bat to stop the server.
echo  This window will close in 5 seconds...
echo.
timeout /t 5 /nobreak >nul
