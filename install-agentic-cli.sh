#!/bin/bash
#
# Agentic CLI Installation Script with DVA Alias
#
# This script installs the agentic-cli package and creates a 'dva' alias
# Usage:
#   ./install-agentic-cli.sh [--local] [--global]
#   --local   Install for current user only (default)
#   --global  Install globally with sudo
#
# After installation, use:
#   dva --version
#   dva --help
#   dva <command>
#

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# Logging functions
log_info()  { echo -e "${BLUE}▸${NC} $*"; }
log_ok()    { echo -e "${GREEN}✓${NC} $*"; }
log_warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
log_error() { echo -e "${RED}✗${NC} $*"; }
log_header(){ echo -e "\n${BOLD}$*${NC}\n"; }

# Configuration
INSTALL_TYPE="local"  # local or global
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHELL_CONFIG_FILES=()

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --local)  INSTALL_TYPE="local"; shift ;;
    --global) INSTALL_TYPE="global"; shift ;;
    --help|-h)
      echo "Usage: $0 [--local] [--global]"
      echo ""
      echo "Options:"
      echo "  --local   Install for current user only (default)"
      echo "  --global  Install globally with sudo"
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

# ─────────────────────────────────────────────────────────────────────────────

log_header "🚀 Agentic CLI Installation with DVA Alias"

# Check if uv is installed
log_info "Checking dependencies..."
if ! command -v uv &> /dev/null; then
    log_warn "uv not found, installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    log_ok "uv installed"
else
    log_ok "uv available"
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is required"
    exit 1
fi
log_ok "Python $(python3 --version | cut -d' ' -f2)"

# ─────────────────────────────────────────────────────────────────────────────

log_info "Installing agentic-cli..."

if [ "$INSTALL_TYPE" = "local" ]; then
    log_info "Installing in development mode (local)..."
    cd "$ROOT_DIR/agentic-cli"

    # Create/activate venv if needed
    if [ ! -d ".venv" ]; then
        log_info "Creating virtual environment..."
        uv venv
    fi

    # Install in editable mode
    uv pip install -e ".[dev]"
    log_ok "Installed in $ROOT_DIR/agentic-cli"

elif [ "$INSTALL_TYPE" = "global" ]; then
    log_info "Installing globally..."
    cd "$ROOT_DIR/agentic-cli"

    # Install with uv tool
    uv tool install --force .
    log_ok "Installed globally"
fi

# ─────────────────────────────────────────────────────────────────────────────

log_header "Setting up 'dva' alias"

# Detect shell
SHELL_NAME=$(basename "$SHELL")
log_info "Detected shell: $SHELL_NAME"

# Determine config files to update
case "$SHELL_NAME" in
    bash)
        SHELL_CONFIG_FILES=(
            "$HOME/.bashrc"
            "$HOME/.bash_profile"
        )
        ;;
    zsh)
        SHELL_CONFIG_FILES=(
            "$HOME/.zshrc"
            "$HOME/.zsh_profile"
        )
        ;;
    fish)
        SHELL_CONFIG_FILES=(
            "$HOME/.config/fish/config.fish"
        )
        ;;
    *)
        log_warn "Unknown shell: $SHELL_NAME"
        log_warn "Skipping automatic alias setup"
        SHELL_CONFIG_FILES=()
        ;;
esac

# Create alias function based on shell
case "$SHELL_NAME" in
    bash|zsh)
        ALIAS_COMMAND="alias dva='agent'"
        ;;
    fish)
        ALIAS_COMMAND="alias dva 'agent'"
        ;;
    *)
        ALIAS_COMMAND=""
        ;;
esac

# Add alias to shell config files
ALIAS_ADDED=0
if [ -n "$ALIAS_COMMAND" ]; then
    for config_file in "${SHELL_CONFIG_FILES[@]}"; do
        if [ -f "$config_file" ]; then
            # Check if alias already exists
            if ! grep -q "alias dva=" "$config_file" 2>/dev/null; then
                log_info "Adding alias to $config_file"
                echo "" >> "$config_file"
                echo "# Agentic CLI alias (installed by install-agentic-cli.sh)" >> "$config_file"
                echo "$ALIAS_COMMAND" >> "$config_file"
                ALIAS_ADDED=1
                log_ok "Alias added to $config_file"
            else
                log_ok "Alias already exists in $config_file"
                ALIAS_ADDED=1
            fi
        fi
    done
else
    log_warn "Could not determine how to set up alias for $SHELL_NAME"
fi

# ─────────────────────────────────────────────────────────────────────────────

log_header "Verification"

# Test the installation
if command -v agent &> /dev/null; then
    AGENT_VERSION=$(agent --version 2>/dev/null || echo "unknown")
    log_ok "agent command available: $AGENT_VERSION"
else
    log_error "agent command not found"
    if [ "$INSTALL_TYPE" = "local" ]; then
        log_info "For local installation, activate the venv:"
        echo "  source $ROOT_DIR/agentic-cli/.venv/bin/activate"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────

log_header "Installation Complete!"

echo "Quick start:"
if [ "$INSTALL_TYPE" = "local" ]; then
    echo "  1. Activate the virtual environment:"
    echo "     source $ROOT_DIR/agentic-cli/.venv/bin/activate"
    echo ""
fi

echo "  2. Test the installation:"
echo "     agent --version"
echo "     agent --help"
echo ""

if [ $ALIAS_ADDED -eq 1 ]; then
    echo "  3. Use the 'dva' alias:"
    echo "     dva --version"
    echo "     dva --help"
    echo "     dva <command>"
    echo ""
    echo "  Note: You may need to restart your shell or run:"
    echo "     source ~/.bashrc   # or ~/.zshrc for zsh"
else
    echo "  3. Set up the 'dva' alias manually:"
    if [ -n "$ALIAS_COMMAND" ]; then
        echo "     echo '$ALIAS_COMMAND' >> ~/.${SHELL_NAME}rc"
    else
        echo "     alias dva='agent'"
    fi
fi

echo ""
echo "For more information:"
echo "  - Documentation: $ROOT_DIR/agentic-cli/README.md"
echo "  - Quickstart: $ROOT_DIR/agentic-cli/QUICKSTART.md"
echo ""

log_ok "Setup complete! Happy coding! 🎉"
