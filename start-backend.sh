#!/bin/bash
#
# Dashboard Backend Startup Script
# Uses the project-level uv venv at .venv
#

set -euo pipefail

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_VENV="$SCRIPT_DIR/.venv"
BACKEND_DIR="$SCRIPT_DIR/dashboard/backend"

# Check if project venv exists
if [ ! -d "$PROJECT_VENV" ]; then
    echo -e "${BLUE}▸${NC} Project venv not found. Creating..."
    cd "$SCRIPT_DIR"
    uv venv --python 3.12
    echo -e "${GREEN}✓${NC} Created project venv"
fi

# Install dashboard backend if not already installed
echo -e "${BLUE}▸${NC} Installing dashboard backend..."
cd "$BACKEND_DIR"
uv pip install -e . --python "$PROJECT_VENV/bin/python" --native-tls > /dev/null 2>&1
echo -e "${GREEN}✓${NC} Dashboard backend installed"

# Start the backend server
echo -e "${BLUE}▸${NC} Starting backend server on http://localhost:8000..."
"$PROJECT_VENV/bin/python" -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
