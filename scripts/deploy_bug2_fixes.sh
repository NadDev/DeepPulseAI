#!/bin/bash
# Quick deployment script for Bug #2 fixes
# Usage: bash deploy_bug2_fixes.sh

echo "🚀 Deploying Bug #2 Fixes (Commit 5f05a87)"
echo "==========================================="

# Step 1: Verify we're on the right commit
echo "📍 Checking git status..."
git log --oneline -1

# Step 2: Verify changes
echo ""
echo "📋 Files changed in this commit:"
git show --stat 5f05a87

# Step 3: Pull latest
echo ""
echo "🔄 Pulling latest changes..."
git pull origin main

# Step 4: Build backend
echo ""
echo "🔨 Building backend Docker image..."
docker-compose build backend

# Step 5: Deploy
echo ""
echo "▶️  Starting backend service..."
docker-compose up -d backend

# Step 6: Check logs
echo ""
echo "📊 Backend logs (last 20 lines):"
docker-compose logs -f --tail 20 backend &

# Wait a bit for container to start
sleep 3

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Create a test bot with Grid Trading strategy"
echo "2. Monitor logs for 📊 [GRID-SIGNAL] BUY/SELL events"
echo "3. Verify ✅ [BUY-EXEC] and ✅ [CLOSE-EXEC] logs"
echo "4. Share logs output for verification"
echo ""
echo "To view logs: docker-compose logs -f backend"
echo "To stop logs: Ctrl+C"
