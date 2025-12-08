# =====================================================
# CRBOT - Start FastAPI Server (Local Development)
# PowerShell Version
# =====================================================

Write-Host "`n===============================================" -ForegroundColor Green
Write-Host "🚀 Starting CRBot FastAPI Server..." -ForegroundColor Green
Write-Host "===============================================`n" -ForegroundColor Green

# Set environment
$env:PYTHONUNBUFFERED = 1

# Get Python executable path
$pythonExe = "C:/CRBot/.venv/Scripts/python.exe"

if (-not (Test-Path $pythonExe)) {
    Write-Host "❌ Python executable not found at: $pythonExe" -ForegroundColor Red
    Write-Host "Please ensure the virtual environment is set up." -ForegroundColor Yellow
    exit 1
}

# Change to backend directory
Set-Location "c:\CRBot\backend"

Write-Host "📍 Working directory: $(Get-Location)" -ForegroundColor Cyan
Write-Host ""

# Start the server
Write-Host "Starting uvicorn server..." -ForegroundColor Cyan
Write-Host ""

& $pythonExe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Write-Host "`n===============================================" -ForegroundColor Green
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "===============================================`n" -ForegroundColor Green
