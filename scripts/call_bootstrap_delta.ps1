#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Call the admin bootstrap endpoint in DELTA mode (fetch only new data)

.DESCRIPTION
  Makes an HTTP POST request to the Railway backend to trigger market data bootstrap.
  - Mode: DELTA (force=false) - only fetches new data since last run
  - Cryptos: 200 top pairs
  - Days: 730 (2 years) 
  - Runs in background (non-blocking)

.PARAMETER Token
  JWT access token from localStorage. Can be obtained from browser console.

.PARAMETER Cryptos
  Number of top cryptos to fetch (default: 200)

.EXAMPLE
  # Get token from browser:
  # 1. Open https://deep-pulse-ai.vercel.app
  # 2. Login
  # 3. Open DevTools (F12) > Console
  # 4. Run: localStorage.getItem('access_token')
  # 5. Copy the token

  # Then run this script:
  .\call_bootstrap_delta.ps1 -Token "eyJhbGc..."
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Token,
    
    [Parameter(Mandatory=$false)]
    [int]$Cryptos = 200,
    
    [Parameter(Mandatory=$false)]
    [string]$BackendUrl = "https://deeppulseai-production.up.railway.app"
)

Write-Host "🚀 Calling Admin Bootstrap Endpoint (DELTA MODE)" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# Prepare request
$url = "$BackendUrl/api/admin/bootstrap?cryptos=$Cryptos&days=730&force=false"
$headers = @{
    "Authorization" = "Bearer $Token"
    "Content-Type" = "application/json"
}

Write-Host "📊 Config:" -ForegroundColor Yellow
Write-Host "   Backend: $BackendUrl" -ForegroundColor Gray
Write-Host "   Mode: DELTA (fetch only new data)" -ForegroundColor Yellow
Write-Host "   Cryptos: $Cryptos" -ForegroundColor Gray
Write-Host "   Days: 730 (2 years history)" -ForegroundColor Gray
Write-Host "   Token: $(($Token -split '' | Select-Object -First 20) -join '')..." -ForegroundColor Gray
Write-Host ""

try {
    Write-Host "📤 Sending request..." -ForegroundColor Cyan
    
    $response = Invoke-RestMethod `
        -Uri $url `
        -Method POST `
        -Headers $headers `
        -ContentType "application/json" `
        -TimeoutSec 10
    
    Write-Host "✅ Bootstrap triggered successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Response:" -ForegroundColor Cyan
    Write-Host ($response | ConvertTo-Json -Depth 3) -ForegroundColor Green
    Write-Host ""
    Write-Host "⏳ Bootstrap is running in background..." -ForegroundColor Yellow
    Write-Host "   Check the logs with: railway logs" -ForegroundColor Gray
    Write-Host ""
    
} catch {
    Write-Host "❌ Error calling bootstrap endpoint:" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    
    if ($_.Exception.Response) {
        Write-Host "Response Status: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
        try {
            $errorBody = $_ | ConvertFrom-Json
            Write-Host "Error Details: $($errorBody.detail)" -ForegroundColor Red
        } catch {
            Write-Host "Could not parse error response" -ForegroundColor Gray
        }
    }
    
    exit 1
}
