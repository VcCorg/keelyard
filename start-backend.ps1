#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start the Agentic dashboard BACKEND (uvicorn, :8000) in the background on Windows.
.DESCRIPTION
    Thin wrapper around start-dashboard.ps1. Warns before killing a process that
    already occupies the port; pass -ForceRestart to reclaim it without asking.
.EXAMPLE
    ./start-backend.ps1
    ./start-backend.ps1 -ForceRestart
    ./start-backend.ps1 -Port 8010
#>
[CmdletBinding()]
param(
    [switch]$ForceRestart,
    [int]$Port = 8000
)

& (Join-Path $PSScriptRoot "start-dashboard.ps1") -Backend -ForceRestart:$ForceRestart -BackendPort $Port
