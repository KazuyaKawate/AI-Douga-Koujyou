# AI動画工場 v4.1 — Desktop Shortcut Creator
# Usage: Right-click → Run with PowerShell
#        Or from PowerShell: .\create_desktop_shortcut.ps1

param(
    [string]$ProjectRoot = (Split-Path -Parent $MyInvocation.MyCommand.Path)
)

$batPath = Join-Path $ProjectRoot "run_ai_factory.bat"
$icoPath = Join-Path $ProjectRoot "assets\icon.ico"
$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "AI動画工場.lnk"

Write-Host ""
Write-Host "  AI動画工場 v4.1 — Create Desktop Shortcut"
Write-Host "  ============================================"
Write-Host ""

# ── Verify target exists ──────────────────────────────────────────────────────
if (-not (Test-Path $batPath)) {
    Write-Error "run_ai_factory.bat not found at: $batPath"
    exit 1
}

# ── Resolve icon: assets\icon.ico → venv python.exe → system python.exe ──────
if (Test-Path $icoPath) {
    $iconLocation = $icoPath
    Write-Host "  Icon      : assets\icon.ico"
} else {
    $venvPy = Join-Path $ProjectRoot "venv\Scripts\python.exe"
    if (Test-Path $venvPy) {
        $iconLocation = "$venvPy,0"
        Write-Host "  Icon      : venv python.exe (fallback)"
    } else {
        $sysPy = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($sysPy) {
            $iconLocation = "$sysPy,0"
            Write-Host "  Icon      : system python.exe (fallback)"
        } else {
            $iconLocation = ""
            Write-Host "  Icon      : (default Windows icon)"
        }
    }
}

# ── Create shortcut via WScript.Shell ────────────────────────────────────────
$shell = New-Object -ComObject WScript.Shell
$sc    = $shell.CreateShortcut($lnkPath)
$sc.TargetPath       = $batPath
$sc.WorkingDirectory = $ProjectRoot
$sc.Description      = "AI動画工場 v4.1 - Multi-Agent Production Studio"
$sc.WindowStyle      = 1
if ($iconLocation) { $sc.IconLocation = $iconLocation }
$sc.Save()

Write-Host "  Shortcut  : $lnkPath"
Write-Host "  Target    : $batPath"
Write-Host "  WorkDir   : $ProjectRoot"
Write-Host ""
Write-Host "  Done! Double-click AI動画工場 on your Desktop to launch."
Write-Host ""
