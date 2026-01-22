# ============================================
# Apply Database Migrations to Railway
# ============================================
# This script applies pending migrations to the Railway PostgreSQL database
# It will:
# 1. Create user_trading_settings table (Migration 007)
# 2. Add CLOSING status to trade_status enum (Migration 008)
# 3. Track applied migrations to avoid duplication

Write-Host "🚀 Applying Database Migrations to Railway..." -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "backend/apply_migrations.py")) {
    Write-Host "❌ Error: Could not find backend/apply_migrations.py" -ForegroundColor Red
    Write-Host "Please run this script from the project root directory" -ForegroundColor Yellow
    exit 1
}

# Check if DATABASE_URL is set
if (-not $env:DATABASE_URL) {
    Write-Host "❌ Error: DATABASE_URL environment variable not set" -ForegroundColor Red
    Write-Host ""
    Write-Host "To set it, copy-paste your Railway database URL from Dashboard:" -ForegroundColor Yellow
    Write-Host '  $env:DATABASE_URL = "postgresql://user:pass@host:port/db"' -ForegroundColor Green
    Write-Host ""
    Write-Host "Then run this script again" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ DATABASE_URL is set" -ForegroundColor Green
Write-Host ""

# Run migration script
Write-Host "🔄 Executing migrations..." -ForegroundColor Cyan
Write-Host ""

cd backend
python apply_migrations.py
$exitCode = $LASTEXITCODE

cd ..

if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "✅ Migrations applied successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Verify tables were created: railway run psql -c '\dt user_trading_settings'" -ForegroundColor Yellow
    Write-Host "2. Restart the backend: railway redeploy backend" -ForegroundColor Yellow
    Write-Host "3. Test the API endpoints" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "❌ Migration failed" -ForegroundColor Red
    Write-Host "Check the error messages above and fix any issues" -ForegroundColor Yellow
    exit 1
}
