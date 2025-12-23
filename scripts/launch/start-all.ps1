# CRBot - Complete Application Launcher
# Lance le backend et le frontend en parallèle

param(
    [switch]$Backend = $false,
    [switch]$Frontend = $false,
    [switch]$All = $true
)

# Colors for output
function Write-Success {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

# Banner
Clear-Host
Write-Host "=" * 70 -ForegroundColor Magenta
Write-Host "CRBot - Complete Application Launcher" -ForegroundColor Magenta
Write-Host "=" * 70 -ForegroundColor Magenta
Write-Host ""

# Script directory (get project root - either current dir if launched from root, or 2 levels up if from scripts/launch)
$currentDir = Get-Location
if (Test-Path "$currentDir\.venv") {
    # Launched from project root
    $scriptDir = $currentDir
} else {
    # Launched from scripts/launch - go up 2 levels
    $scriptDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
}
Write-Info "Project Directory: $scriptDir"
Write-Host ""

# Determine what to launch
if ($Backend) {
    $All = $false
}
if ($Frontend) {
    $All = $false
}

# Display menu if not specified
if ($All -and -not $Backend -and -not $Frontend) {
    Write-Host "Select what to launch:" -ForegroundColor Yellow
    Write-Host "  1) Both Backend and Frontend (RECOMMENDED)"
    Write-Host "  2) Backend only"
    Write-Host "  3) Frontend only"
    Write-Host "  4) Exit"
    Write-Host ""
    
    $choice = Read-Host "Enter your choice (1-4)"
    
    switch ($choice) {
        "1" {
            $All = $true
            Write-Success "[OK] Launching both Backend and Frontend"
        }
        "2" {
            $Backend = $true
            $All = $false
            Write-Success "[OK] Launching Backend only"
        }
        "3" {
            $Frontend = $true
            $All = $false
            Write-Success "[OK] Launching Frontend only"
        }
        "4" {
            Write-Host "Exiting..."
            exit 0
        }
        default {
            Write-Error-Custom "Invalid choice"
            exit 1
        }
    }
}

Write-Host ""

# Check venv exists
$venvPython = Join-Path $scriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error-Custom "[ERROR] Python virtual environment not found!"
    Write-Error-Custom "Expected: $venvPython"
    Write-Host ""
    Write-Host "Please create a virtual environment first:"
    Write-Host "  python -m venv .venv"
    exit 1
}

# Function to launch backend
function Start-Backend {
    Write-Info "[INFO] Starting Backend Server..."
    Write-Host "       Backend will run on http://localhost:8002"
    Write-Host ""
    
    $backendDir = Join-Path $scriptDir "backend"
    $backendJob = Start-Job -ScriptBlock {
        param($python, $dir)
        Set-Location $dir
        & $python -m uvicorn app.main:app --host localhost --port 8002
    } -ArgumentList $venvPython, $backendDir -Name "CRBot-Backend"
    
    return $backendJob
}

# Function to launch frontend
function Start-Frontend {
    Write-Info "[INFO] Starting Frontend Server (Vite)..."
    Write-Host "       Frontend will run on http://localhost:3000"
    Write-Host ""
    
    $frontendDir = Join-Path $scriptDir "frontend"
    $frontendJob = Start-Job -ScriptBlock {
        param($dir)
        Set-Location $dir
        npm run dev
    } -ArgumentList $frontendDir -Name "CRBot-Frontend"
    
    return $frontendJob
}

# Launch services
$jobs = @()

if ($All -or $Backend) {
    $backendJob = Start-Backend
    $jobs += $backendJob
    Start-Sleep 2
}

if ($All -or $Frontend) {
    $frontendJob = Start-Frontend
    $jobs += $frontendJob
    Start-Sleep 2
}

Write-Host ""
Write-Success "=" * 70
Write-Success "Services are starting..."
Write-Success "=" * 70
Write-Host ""

if ($All) {
    Write-Success "[OK] Backend: http://127.0.0.1:8002"
    Write-Success "[OK] Frontend: http://localhost:3000"
    Write-Success "[OK] API Docs: http://127.0.0.1:8002/docs"
    Write-Host ""
    Write-Host "Open http://localhost:3000 in your web browser" -ForegroundColor Yellow
}
elseif ($Backend) {
    Write-Success "[OK] Backend: http://127.0.0.1:8002"
    Write-Success "[OK] API Docs: http://127.0.0.1:8002/docs"
}
else {
    Write-Success "[OK] Frontend: http://localhost:3000"
    Write-Host ""
    Write-Host "Open http://localhost:3000 in your web browser" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press CTRL+C to stop all services" -ForegroundColor Yellow
Write-Host ""

# Wait for all jobs
foreach ($job in $jobs) {
    Wait-Job -Job $job | Out-Null
}

Write-Info "[INFO] All services stopped"
exit 0
