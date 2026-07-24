<#
package-win.ps1 - Windows equivalent of package-mac.sh.
Node 22 + install + build/pack the Keel desktop app on Windows.

Run from the desktop\ directory:

    powershell -ExecutionPolicy Bypass -File .\scripts\package-win.ps1

Output installer: desktop\release\Keel-<version>.exe (NSIS, x64).
Log:              desktop\release\package-win.log

NOTE ON ENCODING
This file is pure ASCII and saved with a UTF-8 BOM. Windows PowerShell 5.1
reads .ps1 files as CP-1252 when there is no BOM, which corrupts anything
non-ASCII in string literals; keep this file ASCII-only for maximum safety.
#>

Set-StrictMode -Version Latest
# NOTE: Continue, not Stop. Windows PowerShell 5.1 turns any stderr write
# from a native command (python / npm / pip / nvm) into a NativeCommandError
# under Stop mode - even a benign warning kills the script before its
# `2>$null` redirect can suppress it. We use explicit `$LASTEXITCODE` +
# `throw` for real failures, so Stop's implicit termination is not needed.
$ErrorActionPreference = 'Continue'

# Move to desktop\ regardless of where the script was invoked from.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $ScriptDir '..')

# ---- Repo venv (must exist; PyInstaller runs from here) --------------------
$RepoRoot = Resolve-Path (Join-Path $ScriptDir '..\..')
$VenvActivate = Join-Path $RepoRoot '.venv\Scripts\Activate.ps1'
if (-not (Test-Path $VenvActivate)) {
    Write-Error "project .venv not found at $VenvActivate. Run the repo setup first (e.g. install-agentic-cli.sh under WSL or install-agentic-cli.ps1 if you have one)."
    exit 1
}
. $VenvActivate

# ---- PyInstaller -----------------------------------------------------------
$pyi = Get-Command pyinstaller -ErrorAction SilentlyContinue
if (-not $pyi) {
    Write-Host "pyinstaller not found in .venv; installing it now..." -ForegroundColor Yellow
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    $venvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
    if ($uv) {
        & uv pip install --python $venvPython pyinstaller
    } else {
        & $venvPython -m pip install pyinstaller
    }
    if ($LASTEXITCODE -ne 0) { Write-Error "pyinstaller install failed"; exit 1 }
}

# Windows-only: the frozen backend needs pywinpty for the terminal (PTY).
# Use importlib.util.find_spec so a missing module returns exit 1 without
# writing a Python traceback to stderr - Windows PowerShell surfaces
# native-command stderr as NativeCommandError even with Continue, and
# there is no need to pollute the log with a traceback we already expect.
#
# Note the SINGLE quotes around 'winpty': Windows argv parsing eats the
# outer double quotes PowerShell adds around the -c argument, so any inner
# double quotes get dropped and Python would see find_spec(winpty) - a
# NameError. Python accepts single quotes for strings, so 'winpty' survives.
$probe = "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('winpty') else 1)"
& python -c $probe
if ($LASTEXITCODE -ne 0) {
    Write-Host "pywinpty not found; installing it (needed for the terminal PTY)..." -ForegroundColor Yellow
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    $venvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'
    if ($uv) {
        & uv pip install --python $venvPython pywinpty
    } else {
        & $venvPython -m pip install pywinpty
    }
    if ($LASTEXITCODE -ne 0) { Write-Warning "pywinpty install failed; terminal PTY will not work in the packaged app." }
}

# ---- Node 22 --------------------------------------------------------------
# Prefer nvm-windows if installed; otherwise validate the ambient node.
$nvm = Get-Command nvm -ErrorAction SilentlyContinue
if ($nvm) {
    & nvm install 22.0.0 | Out-Null
    & nvm use 22.0.0     | Out-Null
} else {
    $nodeVersion = ''
    try { $nodeVersion = (& node --version) 2>$null } catch {}
    $major = ($nodeVersion -replace '^v','').Split('.')[0]
    if ($major -ne '22') {
        Write-Error "Node.js 22 is required and nvm-windows is not available. Install Node 22 (or nvm-windows) and re-run this script. Current node: $nodeVersion"
        exit 1
    }
}

# ---- Stale-build cleanup --------------------------------------------------
# Kill leftover frozen-backend processes that could lock files during rebuild.
# The smoke test spawns keel-backend.exe; if a previous run was force-killed
# the OS may still hold an exclusive lock on the exe.
function Stop-KeelBackendProcesses {
    Get-Process -Name 'keel-backend' -ErrorAction SilentlyContinue |
        ForEach-Object {
            Write-Host "Stopping stale keel-backend.exe (pid $($_.Id))" -ForegroundColor Yellow
            Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        }
}

function Remove-StaleBackendBundle {
    $bundle = 'resources\backend\keel-backend'
    if (-not (Test-Path $bundle)) { return }
    for ($i = 1; $i -le 3; $i++) {
        try {
            Remove-Item -Recurse -Force $bundle -ErrorAction Stop
            return
        } catch {
            Write-Host "  ... retrying backend cleanup ($i/3): $($_.Exception.Message)" -ForegroundColor Yellow
            Stop-KeelBackendProcesses
            Start-Sleep -Seconds 1
        }
    }
    Write-Error "Could not delete $bundle after 3 attempts. Close anything holding it (Explorer preview, AV scanner) and retry."
    exit 1
}

Stop-KeelBackendProcesses
Remove-StaleBackendBundle

# ---- Ensure output directory + log tee ------------------------------------
New-Item -ItemType Directory -Force -Path release | Out-Null
$LogPath = Join-Path (Resolve-Path 'release') 'package-win.log'
Start-Transcript -Path $LogPath -Force | Out-Null

try {
    # Same pipeline the Mac script uses, minus the DMG per-arch split. Windows
    # ships one NSIS installer (x64 per desktop\package.json build.win.target).
    & npm install
    if ($LASTEXITCODE -ne 0) { throw "npm install failed" }

    & npm run build:electron
    if ($LASTEXITCODE -ne 0) { throw "build:electron failed" }

    & npm run build:frontend
    if ($LASTEXITCODE -ne 0) { throw "build:frontend failed" }

    & npm run build:backend
    if ($LASTEXITCODE -ne 0) { throw "build:backend failed" }

    & npm run smoke:backend
    if ($LASTEXITCODE -ne 0) { throw "smoke:backend failed (frozen bundle is broken - do not ship)" }

    & npx electron-builder --win nsis --publish never
    if ($LASTEXITCODE -ne 0) { throw "electron-builder --win failed" }

    Write-Host ""
    Write-Host "Done. Installer(s) in desktop\release\:" -ForegroundColor Green
    Get-ChildItem release -Filter *.exe | ForEach-Object { Write-Host "  $($_.FullName)" }
}
finally {
    Stop-Transcript | Out-Null
    # Best-effort: leave no orphan sidecar behind after a smoke test.
    Stop-KeelBackendProcesses
}
