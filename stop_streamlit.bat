@echo off
REM ================================================================
REM  stop_streamlit.bat  --  AI-Douga-Koujyou v4.1 server stopper
REM
REM  IMPORTANT: This file must remain ASCII-only (0x00-0x7F).
REM  See run_ai_factory.bat header for the full explanation.
REM ================================================================
title Stop AI-Douga-Koujyou

echo.
echo  ============================================
echo   AI-Douga-Koujyou v4.1 - Stop Server
echo  ============================================
echo.

powershell -ExecutionPolicy Bypass -NonInteractive -Command "
$port = 8501
$conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $conns) {
    Write-Host '  No process is listening on port 8501.'
    Write-Host '  AI-Douga-Koujyou is not running.'
} else {
    foreach ($conn in $conns) {
        try {
            $proc = Get-Process -Id $conn.OwningProcess -ErrorAction Stop
            Write-Host ('  Stopping ' + $proc.Name + ' (PID ' + $proc.Id + ')...')
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 500
            $stillRunning = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
            if ($stillRunning) {
                Write-Host '  [WARN] Process may still be running.'
            } else {
                Write-Host '  Stopped successfully.'
            }
        } catch {
            Write-Host ('  Could not find process for PID ' + $conn.OwningProcess + ' - may have already exited.')
        }
    }
}
"

echo.
echo  Done.
timeout /t 2 /nobreak >nul
