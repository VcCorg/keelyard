#!/bin/bash
#
# Agentic CLI Installation Script with DVA Alias
#
# This script installs the agentic-cli package with all required dependencies
# and creates a 'dva' alias. The Vertex AI SDK and other core dependencies
# are installed by default.
#
# Usage:
#   ./install-agentic-cli.sh [--local] [--global] [--with PACKAGE] [--group GROUP]
#   --local   Install for current user only (default)
#   --global  Install globally with sudo
#   --with PACKAGE  Install with additional dependencies (optional)
#   --group GROUP  Install with predefined dependency group (optional)
#
# Examples:
#   ./install-agentic-cli.sh --global                    # Install with all core dependencies
#   ./install-agentic-cli.sh --global --group kg         # Add knowledge graph features
#   ./install-agentic-cli.sh --global --with neo4j       # Add specific package
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
INSTALL_TYPE="project"  # project, local, or global
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHELL_CONFIG_FILES=()
ADDITIONAL_DEPS=""  # Additional dependencies for --with flag
DEPENDENCY_GROUP=""  # Predefined dependency group
DEV_MODE=""  # Development mode flag
FORCE_REINSTALL=""  # Force reinstall from source
USE_NATIVE_TLS=""  # Use system TLS certificates
PROJECT_VENV="$ROOT_DIR/.venv"  # Project-level uv venv

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --local)  INSTALL_TYPE="local"; shift ;;
    --global) INSTALL_TYPE="global"; shift ;;
    --with)
      if [[ -n "${2:-}" ]]; then
        ADDITIONAL_DEPS="$2"
        shift 2
      else
        log_error "--with requires a package name"
        exit 1
      fi
      ;;
    --group)
      if [[ -n "${2:-}" ]]; then
        DEPENDENCY_GROUP="$2"
        shift 2
      else
        log_error "--group requires a dependency group name"
        exit 1
      fi
      ;;
    --dev)
      DEV_MODE="1"
      log_info "Development mode enabled - will install from source"
      shift
      ;;
    --force)
      FORCE_REINSTALL="1"
      log_info "Force reinstall enabled"
      shift
      ;;
    --native-tls)
      USE_NATIVE_TLS="1"
      log_info "Using system TLS certificates for uv"
      shift
      ;;
    --project)
      INSTALL_TYPE="project"
      log_info "Installing into project venv"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--project] [--local] [--global] [--with PACKAGE] [--group GROUP] [--dev] [--force] [--native-tls]"
      echo ""
      echo "Options:"
      echo "  --project     Install into project venv (default: $PROJECT_VENV)"
      echo "  --local       Install in local agentic-cli/.venv (legacy)"
      echo "  --global      Install globally with sudo"
      echo "  --with PACKAGE  Install with additional dependencies (optional)"
      echo "  --group GROUP  Install with predefined dependency group (optional)"
      echo "  --dev         Development mode - always install from latest source"
      echo "  --force       Force reinstall (useful after code changes)"
      echo "  --native-tls  Use system TLS certificates (fixes corporate VPN certificate issues)"
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

if [ "$INSTALL_TYPE" = "project" ]; then
    log_info "Installing into project venv ($PROJECT_VENV)..."
    cd "$ROOT_DIR"

    # Ensure project venv exists
    if [ ! -d "$PROJECT_VENV" ]; then
        log_info "Creating project venv with uv (Python 3.12)..."
        uv venv --python 3.12
    fi

    # Install in editable mode with all core dependencies
    UV_FLAGS=""
    if [ -n "$USE_NATIVE_TLS" ]; then
        UV_FLAGS="--native-tls"
    fi

    if [ -n "$DEPENDENCY_GROUP" ]; then
        log_info "Installing with dependency group: $DEPENDENCY_GROUP"
        uv pip install $UV_FLAGS -e "agentic-cli/[dev,$DEPENDENCY_GROUP]"
    elif [ -n "$ADDITIONAL_DEPS" ]; then
        log_info "Installing with additional dependencies: $ADDITIONAL_DEPS"
        uv pip install $UV_FLAGS -e "agentic-cli/[dev]" "$ADDITIONAL_DEPS"
    else
        log_info "Installing with all core dependencies (including Vertex AI SDK)"
        uv pip install $UV_FLAGS -e "agentic-cli/[dev]"
    fi
    log_ok "Installed in project venv: $PROJECT_VENV"

elif [ "$INSTALL_TYPE" = "local" ]; then
    log_info "Installing in development mode (local)..."
    cd "$ROOT_DIR/agentic-cli"

    # Create/activate venv if needed
    if [ ! -d ".venv" ]; then
        log_info "Creating virtual environment..."
        uv venv
    fi

    # Install in editable mode with all core dependencies
    UV_FLAGS=""
    if [ -n "$USE_NATIVE_TLS" ]; then
        UV_FLAGS="--native-tls"
    fi

    if [ -n "$DEPENDENCY_GROUP" ]; then
        log_info "Installing with dependency group: $DEPENDENCY_GROUP"
        uv pip install $UV_FLAGS -e ".[dev,$DEPENDENCY_GROUP]"
    elif [ -n "$ADDITIONAL_DEPS" ]; then
        log_info "Installing with additional dependencies: $ADDITIONAL_DEPS"
        uv pip install $UV_FLAGS -e ".[dev]" "$ADDITIONAL_DEPS"
    else
        log_info "Installing with all core dependencies (including Vertex AI SDK)"
        uv pip install $UV_FLAGS -e ".[dev]"
    fi
    log_ok "Installed in $ROOT_DIR/agentic-cli"

elif [ "$INSTALL_TYPE" = "global" ]; then
    log_info "Installing globally..."
    cd "$ROOT_DIR/agentic-cli"

    # Install with uv tool, including all core dependencies
    # Always use --force to ensure latest source code is used
    UV_FLAGS=""
    if [ -n "$USE_NATIVE_TLS" ]; then
        UV_FLAGS="--native-tls"
    fi

    if [ -n "$DEPENDENCY_GROUP" ]; then
        log_info "Installing with dependency group: $DEPENDENCY_GROUP"
        uv tool install $UV_FLAGS --force --with ".[$DEPENDENCY_GROUP]" .
    elif [ -n "$ADDITIONAL_DEPS" ]; then
        log_info "Installing with additional dependencies: $ADDITIONAL_DEPS"
        uv tool install $UV_FLAGS --force --with "$ADDITIONAL_DEPS" .
    else
        log_info "Installing with all core dependencies (including Vertex AI SDK)"
        uv tool install $UV_FLAGS --force .
    fi

    # In dev mode, ensure we're using the latest source
    if [ -n "$DEV_MODE" ] || [ -n "$FORCE_REINSTALL" ]; then
        log_info "Development mode: Ensuring latest source code is installed"
        # The --force flag above should handle this, but let's be explicit
        log_ok "Source installation complete"
    fi
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
        ALIAS_COMMAND="alias dva='dva'"
        ;;
    fish)
        ALIAS_COMMAND="alias dva 'dva'"
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

log_header "Environment Validation"

# Validate environment and dependencies
if [ "$INSTALL_TYPE" = "global" ]; then
    # Test if dependencies are available in the isolated environment
    if [ -n "$ADDITIONAL_DEPS" ]; then
        log_info "Validating additional dependencies..."
        # Extract package name from --with argument (remove version specs if any)
        PACKAGE_NAME=$(echo "$ADDITIONAL_DEPS" | cut -d'[' -f1 | cut -d'=' -f1 | cut -d'<' -f1 | cut -d'>' -f1)
        if python3 -c "import $PACKAGE_NAME" 2>/dev/null; then
            log_ok "$PACKAGE_NAME is available in the environment"
        else
            log_warn "$PACKAGE_NAME may not be properly installed in the isolated environment"
            log_info "Try: uv tool install --force --with $ADDITIONAL_DEPS agentic-cli"
        fi
    fi
fi

log_header "Verification"

# Test the installation
if command -v dva &> /dev/null; then
    DVA_VERSION=$(dva --version 2>/dev/null || echo "unknown")
    log_ok "dva command available: $DVA_VERSION"

    # Test for console formatting errors
    log_info "Testing console output..."
    if dva --version > /dev/null 2>&1; then
        log_ok "Console output working correctly"
    else
        log_warn "Console formatting issues detected (this is a known DVA CLI issue)"
        log_info "The tool should still function despite formatting errors"
    fi
else
    log_error "dva command not found in PATH"
    if [ "$INSTALL_TYPE" = "project" ]; then
        log_info "For project installation, activate the venv:"
        echo "  source $PROJECT_VENV/bin/activate"
    elif [ "$INSTALL_TYPE" = "local" ]; then
        log_info "For local installation, activate the venv:"
        echo "  source $ROOT_DIR/agentic-cli/.venv/bin/activate"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────

log_header "Installation Complete!"

echo "Quick start:"
if [ "$INSTALL_TYPE" = "project" ]; then
    echo "  1. Activate the project venv:"
    echo "     source $PROJECT_VENV/bin/activate"
    echo ""
elif [ "$INSTALL_TYPE" = "local" ]; then
    echo "  1. Activate the virtual environment:"
    echo "     source $ROOT_DIR/agentic-cli/.venv/bin/activate"
    echo ""
else
    echo "  1. The tool is now available globally"
    echo ""
fi

echo "  2. Test the installation:"
echo "     dva --version"
echo "     dva --help"
echo ""

if [ -n "$ADDITIONAL_DEPS" ]; then
    echo "  3. Your installation includes: $ADDITIONAL_DEPS"
    echo ""
fi

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
