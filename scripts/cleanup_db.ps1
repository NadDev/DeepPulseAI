#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Quick database cleanup script for CRBot production

.DESCRIPTION
  Cleans up old data from PostgreSQL to free disk space
  Supports aggressive mode and dry-run preview

.PARAMETER Mode
  Cleanup mode: 'normal' (default) or 'aggressive'

.PARAMETER DryRun
  Preview changes without deleting

.PARAMETER Analyze
  Show storage usage and exit

.EXAMPLE
  .\cleanup_db.ps1
  .\cleanup_db.ps1 -Mode aggressive
  .\cleanup_db.ps1 -DryRun
  .\cleanup_db.ps1 -Analyze
#>

param(
    [ValidateSet('normal', 'aggressive')]
    [string]$Mode = 'normal',
    
    [switch]$DryRun,
    [switch]$Analyze
)

Write-Host "🧹 CRBot Database Cleanup" -ForegroundColor Green
Write-Host ""

# Find cleanup script
$scriptPath = $null
if (Test-Path "backend/cleanup_database.py") {
    $scriptPath = "backend/cleanup_database.py"
    Push-Location "backend"
} elseif (Test-Path "cleanup_database.py") {
    $scriptPath = "cleanup_database.py"
} else {
    Write-Host "❌ Error: Could not find cleanup_database.py" -ForegroundColor Red
    Write-Host "Run from project root or backend directory" -ForegroundColor Yellow
    exit 1
}

# Check Python
$pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Host "❌ Python not found" -ForegroundColor Red
    exit 1
}

# Check .env
if (-not (Test-Path ".env")) {
    Write-Host "❌ Error: .env file not found" -ForegroundColor Red
    Write-Host "Configure DATABASE_URL in .env" -ForegroundColor Yellow
    exit 1
}

# Build arguments
$args = @("cleanup_database.py")

if ($Mode -eq 'aggressive') {
    Write-Host "⚠️ AGGRESSIVE MODE" -ForegroundColor Yellow
    Write-Host "   Shorter retention periods, more aggressive cleaning" -ForegroundColor Yellow
    $args += "--aggressive"
}

if ($DryRun) {
    Write-Host "🔍 DRY RUN MODE" -ForegroundColor Yellow
    Write-Host "   No data will be deleted" -ForegroundColor Yellow
    $args += "--dry-run"
}

if ($Analyze) {
    Write-Host "📊 ANALYSIS MODE" -ForegroundColor Yellow
    $args += "--analyze"
}

Write-Host ""

# Run cleanup
Write-Host "Starting cleanup..." -ForegroundColor Green
Write-Host ""

& python3 $args

Write-Host ""
Write-Host "✅ Done!" -ForegroundColor Green

# Pop location if we changed it
if ($scriptPath -eq "backend/cleanup_database.py") {
    Pop-Location
}
