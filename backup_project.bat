@echo off
REM ================================================================
REM  backup_project.bat  --  AI-Douga-Koujyou v4.1 backup utility
REM
REM  IMPORTANT: This file must remain ASCII-only (0x00-0x7F).
REM  See run_ai_factory.bat header for the full explanation.
REM
REM  NOTE: The ZIP archive name uses the ASCII alias
REM  "AI-Douga-Koujyou" because Japanese literals cannot appear
REM  in .bat files.  The project path (%ROOT%) is a runtime
REM  variable expanded by CMD and passed to PowerShell correctly
REM  even when the path itself contains Japanese characters.
REM ================================================================

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

title Backup AI-Douga-Koujyou

echo.
echo  ============================================
echo   AI-Douga-Koujyou v4.1 - Backup Project
echo  ============================================
echo.

if not exist "backups" mkdir backups

powershell -ExecutionPolicy Bypass -NonInteractive -Command "
Set-Location '%ROOT%'
$root = (Get-Location).Path
$date = Get-Date -Format 'yyyyMMdd_HHmm'
$zipName = 'AI-Douga-Koujyou_Backup_' + $date + '.zip'
$zipPath = Join-Path 'backups' $zipName

Write-Host ('  Creating: ' + $zipName)

$includePaths    = @('config','project','assets','docs','README.md','RELEASE_NOTES.md')
$excludeSegments = [System.Collections.Generic.HashSet[string]]::new(
    [string[]]@('.git','.venv','venv','__pycache__','backups'),
    [System.StringComparer]::OrdinalIgnoreCase
)
$excludeExts = @('.pyc','.pyo','.env')

Add-Type -Assembly System.IO.Compression.FileSystem
Add-Type -Assembly System.IO.Compression

$zip = [System.IO.Compression.ZipFile]::Open($zipPath, [System.IO.Compression.ZipArchiveMode]::Create)
$addedCount = 0

foreach ($rel in $includePaths) {
    if (-not (Test-Path $rel)) { continue }
    $item = Get-Item $rel
    if ($item.PSIsContainer) {
        Get-ChildItem -Path $rel -Recurse -File | ForEach-Object {
            $relPath = $_.FullName.Substring($root.Length + 1)
            $parts   = $relPath.Split([System.IO.Path]::DirectorySeparatorChar)
            $skip    = $parts | Where-Object { $excludeSegments.Contains($_) }
            if ($skip) { return }
            if ($excludeExts -contains $_.Extension.ToLower()) { return }
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $relPath) | Out-Null
            $addedCount++
        }
    } else {
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $item.FullName, $rel) | Out-Null
        $addedCount++
    }
}
$zip.Dispose()

$sizeMB = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
Write-Host ('  Files added  : ' + $addedCount)
Write-Host ('  Archive size : ' + $sizeMB + ' MB')
Write-Host ('  Saved to     : backups\' + $zipName)

$all = Get-ChildItem -Path 'backups' -Filter 'AI-Douga-Koujyou_Backup_*.zip' |
       Sort-Object LastWriteTime -Descending
if ($all.Count -gt 20) {
    $toDelete = $all | Select-Object -Skip 20
    foreach ($f in $toDelete) {
        Remove-Item $f.FullName -Force
        Write-Host ('  Pruned       : ' + $f.Name)
    }
}
"

if errorlevel 1 (
    echo.
    echo  [ERROR] Backup failed. See output above.
    pause
    exit /b 1
)

echo.
echo  ============================================
echo   Backup complete.
echo  ============================================
echo.
pause
