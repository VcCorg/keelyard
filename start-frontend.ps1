#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Start the Agentic dashboard FRONTEND (Vite, :5173) in the background on Windows.
.DESCRIPTION
    Thin wrapper around start-dashboard.ps1. Warns before killing a process that
    already occupies the port; pass -ForceRestart to reclaim it without asking.
.EXAMPLE
    ./start-frontend.ps1
    ./start-frontend.ps1 -ForceRestart
    ./start-frontend.ps1 -Port 5174
#>
[CmdletBinding()]
param(
    [switch]$ForceRestart,
    [int]$Port = 5173
)

& (Join-Path $PSScriptRoot "start-dashboard.ps1") -Frontend -ForceRestart:$ForceRestart -FrontendPort $Port
