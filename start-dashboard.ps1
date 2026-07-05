#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start/stop the Agentic dashboard (backend :8000 + frontend :5173) on Windows.

.DESCRIPTION
    Thin PowerShell wrapper around the cross-platform launcher
    scripts/dashboard.py, so macOS, Linux, and Windows all share ONE
    implementation of the background-start + port-guard logic.

    Runs each service in the background, logs to dashboard\backend.log /
    dashboard\frontend.log, and warns before killing a process that already owns
    a port (unless -ForceRestart, or a non-interactive session, which skips).

.EXAMPLE
    ./start-dashboard.ps1                 # start backend + frontend
    ./start-dashboard.ps1 -ForceRestart   # reclaim busy ports without prompting
    ./start-dashboard.ps1 -Backend        # backend only
    ./start-dashboard.ps1 -Status
    ./start-dashboard.ps1 -Stop

.NOTES
    Equivalent one-liner on any OS:  python scripts/dashboard.py start
#>
[CmdletBinding()]
param(
    [switch]$Backend,
    [switch]$Frontend,
    [switch]$Stop,
    [switch]$Status,
    [switch]$ForceRestart,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$root = $PSScriptRoot
$launcher = Join-Path $root "scripts\dashboard.py"
if (-not (Test-Path $launcher)) {
    Write-Error "Launcher not found: $launcher"
    exit 1
}

# Resolve a Python interpreter (prefer the project venv).
$py = $null
foreach ($c in @("$root\.venv\Scripts\python.exe", "$root\agentic-cli\.venv\Scripts\python.exe")) {
    if (Test-Path $c) { $py = $c; break }
}
if (-not $py) {
    foreach ($name in @("python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { $py = $cmd.Source; break }
    }
}
if (-not $py) {
    Write-Error "Python not found. Install the CLI first (install-agentic-cli)."
    exit 1
}

# Map the switches to the launcher's sub-command + flags.
$sub = "start"
if ($Status) { $sub = "status" }
elseif ($Stop) { $sub = "stop" }

$argList = @($launcher, $sub, "--backend-port", "$BackendPort", "--frontend-port", "$FrontendPort")
if ($sub -eq "start") {
    if ($Backend)      { $argList += "--backend" }
    if ($Frontend)     { $argList += "--frontend" }
    if ($ForceRestart) { $argList += "--force-restart" }
}

& $py @argList
exit $LASTEXITCODE
