#!/bin/bash
#
# Dashboard Frontend Startup Script
# Uses Node.js directly (frontend doesn't use Python venv)
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/dashboard/frontend"

# Check if node_modules exists
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${BLUE}▸${NC} node_modules not found. Installing dependencies..."
    cd "$FRONTEND_DIR"
    npm install
    echo -e "${GREEN}✓${NC} Dependencies installed"
fi

# Start the frontend dev server
echo -e "${BLUE}▸${NC} Starting frontend dev server on http://localhost:5173..."
cd "$FRONTEND_DIR"
npm run dev
