#!/bin/bash

# =====================================================
# CRBOT - Docker Setup & Initialization Script
# Start all services and initialize database
# =====================================================

set -e

echo "🚀 CRBot Docker Setup Starting..."
echo "=================================="

# Step 1: Check Docker installation
echo "✓ Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

# Step 2: Create necessary directories
echo "✓ Creating directories..."
mkdir -p logs database docker

# Step 3: Start containers
echo "✓ Starting Docker containers..."
cd "$(dirname "$0")"
docker-compose up -d --build

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 10
attempt=0
max_attempts=30
until docker exec crbot-postgres pg_isready -U postgres > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        echo "❌ PostgreSQL failed to start"
        exit 1
    fi
    sleep 1
done
echo "✓ PostgreSQL is ready!"

# Wait for Redis to be ready
echo "⏳ Waiting for Redis to be ready..."
sleep 5
until docker exec crbot-redis redis-cli ping > /dev/null 2>&1; do
    echo "Retrying Redis..."
    sleep 1
done
echo "✓ Redis is ready!"

# Step 4: Display service status
echo ""
echo "=================================="
echo "✅ All services started successfully!"
echo "=================================="
echo ""
echo "📊 Service URLs:"
echo "   🔵 Backend API:      http://localhost:8000"
echo "   📚 API Docs:         http://localhost:8000/docs"
echo "   🎨 Frontend:         http://localhost:3000"
echo "   📈 Grafana:          http://localhost:3001"
echo "   🐘 pgAdmin:          http://localhost:5050"
echo "   💾 PostgreSQL:       localhost:5432"
echo "   🔴 Redis:            localhost:6379"
echo ""
echo "🔑 Credentials:"
echo "   PostgreSQL User:     postgres"
echo "   PostgreSQL Password: postgres_dev_password"
echo "   pgAdmin Email:       admin@example.com"
echo "   pgAdmin Password:    admin"
echo ""
echo "✨ Docker setup complete! Ready for development."
echo ""
