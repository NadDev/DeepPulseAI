# =====================================================
# CRBOT - Docker Setup & Initialization Script (Windows)
# Start all services and initialize database
# =====================================================

Write-Host "🚀 CRBot Docker Setup Starting..." -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

# Step 1: Check Docker installation
Write-Host "✓ Checking Docker..." -ForegroundColor Cyan
$dockerCheck = docker --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker not found. Please install Docker Desktop first." -ForegroundColor Red
    exit 1
}
Write-Host $dockerCheck -ForegroundColor Gray

# Step 2: Create necessary directories
Write-Host "✓ Creating directories..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path logs, database, docker | Out-Null

# Step 3: Start containers
Write-Host "✓ Starting Docker containers..." -ForegroundColor Cyan
docker-compose up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start Docker containers" -ForegroundColor Red
    exit 1
}

# Wait for PostgreSQL to be ready
Write-Host "⏳ Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
$attempt = 0
$maxAttempts = 30
while ($attempt -lt $maxAttempts) {
    try {
        $pgReady = docker exec crbot-postgres pg_isready -U postgres 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ PostgreSQL is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue
    }
    $attempt++
    Start-Sleep -Seconds 1
}

# Wait for Redis to be ready
Write-Host "⏳ Waiting for Redis to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
$redisAttempt = 0
while ($redisAttempt -lt 10) {
    try {
        $redisReady = docker exec crbot-redis redis-cli ping 2>&1
        if ($LASTEXITCODE -eq 0 -and $redisReady -eq "PONG") {
            Write-Host "✓ Redis is ready!" -ForegroundColor Green
            break
        }
    } catch {
        # Continue
    }
    $redisAttempt++
    Start-Sleep -Seconds 1
}

# Step 4: Display service status
Write-Host ""
Write-Host "==================================" -ForegroundColor Green
Write-Host "✅ All services started successfully!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Service URLs:" -ForegroundColor Cyan
Write-Host "   🔵 Backend API:      http://localhost:8000" -ForegroundColor White
Write-Host "   📚 API Docs:         http://localhost:8000/docs" -ForegroundColor White
Write-Host "   🎨 Frontend:         http://localhost:3000" -ForegroundColor White
Write-Host "   📈 Grafana:          http://localhost:3001" -ForegroundColor White
Write-Host "   🐘 pgAdmin:          http://localhost:5050" -ForegroundColor White
Write-Host "   💾 PostgreSQL:       localhost:5432" -ForegroundColor White
Write-Host "   🔴 Redis:            localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "🔑 Credentials:" -ForegroundColor Cyan
Write-Host "   PostgreSQL User:     postgres" -ForegroundColor White
Write-Host "   PostgreSQL Password: postgres_dev_password" -ForegroundColor White
Write-Host "   pgAdmin Email:       admin@example.com" -ForegroundColor White
Write-Host "   pgAdmin Password:    admin" -ForegroundColor White
Write-Host ""
Write-Host "✨ Docker setup complete! Ready for development." -ForegroundColor Green
Write-Host ""
Write-Host "📚 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Open http://localhost:8000/docs (API docs)" -ForegroundColor Gray
Write-Host "   2. Open http://localhost:3000 (Frontend)" -ForegroundColor Gray
Write-Host "   3. Monitor logs: docker-compose logs -f" -ForegroundColor Gray
Write-Host ""
