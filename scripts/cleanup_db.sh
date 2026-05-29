#!/bin/bash
# Quick database cleanup script for production
# Usage: ./scripts/cleanup_db.sh [--aggressive] [--dry-run]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧹 CRBot Database Cleanup${NC}\n"

# Check if in backend directory
if [ ! -f "cleanup_database.py" ]; then
    if [ ! -f "backend/cleanup_database.py" ]; then
        echo -e "${RED}❌ Error: Could not find cleanup_database.py${NC}"
        echo "Run this script from the project root or backend directory"
        exit 1
    fi
    cd backend
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found${NC}"
    exit 1
fi

# Check .env
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please configure DATABASE_URL in .env"
    exit 1
fi

# Parse arguments
ARGS=""
if [[ "$*" == *"--aggressive"* ]]; then
    ARGS="$ARGS --aggressive"
    echo -e "${YELLOW}⚠️  AGGRESSIVE MODE${NC} (short retention)"
fi

if [[ "$*" == *"--dry-run"* ]]; then
    ARGS="$ARGS --dry-run"
    echo -e "${YELLOW}🔍 DRY RUN MODE${NC} (no changes will be made)\n"
fi

if [[ "$*" == *"--analyze"* ]]; then
    ARGS="$ARGS --analyze"
fi

# Run cleanup
echo -e "${GREEN}Starting cleanup...${NC}\n"
python3 cleanup_database.py $ARGS

echo -e "\n${GREEN}✅ Done!${NC}"
