#!/bin/bash
#
# Agentic CLI Installation Script with KEEL Alias
#
# This script installs the agentic-cli package with all required dependencies
# and creates 'keel' / 'keel' aliases (keel is the platform name, same CLI).
# The Vertex AI SDK and other core dependencies are installed by default.
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
#   keel --version
#   keel --help
#   keel <command>
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

# ── Background service launch ────────────────────────────────────────────────
# Delegates to the cross-platform launcher (scripts/dashboard.py) so macOS,
# Linux, and Windows all share ONE implementation of the port-guard + start
# logic. Nothing OS-specific lives here anymore.

start_dashboard_services() {
  local launcher="$ROOT_DIR/scripts/dashboard.py"
  if [ ! -f "$launcher" ]; then
    log_warn "Launcher not found ($launcher); skipping dashboard start."
    return 0
  fi

  # Resolve a Python interpreter to run the launcher.
  local py=""
  if [ -x "$PROJECT_VENV/bin/python" ]; then
    py="$PROJECT_VENV/bin/python"
  elif command -v python3 &> /dev/null; then
    py="python3"
  elif command -v python &> /dev/null; then
    py="python"
  fi
  if [ -z "$py" ]; then
    log_warn "Python not found; start the dashboard manually: python scripts/dashboard.py start"
    return 0
  fi

  local args=(start)
  [ -n "$FORCE_RESTART" ] && args+=(--force-restart)
  "$py" "$launcher" "${args[@]}"
}

# Configuration
INSTALL_TYPE="project"  # project, local, or global
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHELL_CONFIG_FILES=()
ADDITIONAL_DEPS=""  # Additional dependencies for --with flag
DEPENDENCY_GROUP=""  # Predefined dependency group
DEV_MODE=""  # Development mode flag
FORCE_REINSTALL=""  # Force reinstall from source
USE_NATIVE_TLS=""  # Use system TLS certificates
SKIP_DASHBOARD=""  # Skip installing dashboard (frontend npm + backend pip) deps
REQUIRE_INTEGRATIONS=""  # Hard-fail install if Jira/Bitbucket/Confluence tokens are missing
START_SERVICES=""  # Start dashboard backend + frontend in the background after install
FORCE_RESTART=""  # Kill processes occupying the service ports without prompting
PROJECT_VENV="$ROOT_DIR/.venv"  # Project-level uv venv
BACKEND_DIR="$ROOT_DIR/dashboard/backend"
FRONTEND_DIR="$ROOT_DIR/dashboard/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=5173

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
    --skip-dashboard)
      SKIP_DASHBOARD="1"
      log_info "Skipping dashboard dependency installation"
      shift
      ;;
    --require-integrations)
      REQUIRE_INTEGRATIONS="1"
      log_info "Integration tokens (Jira/Bitbucket/Confluence) will be required"
      shift
      ;;
    --start)
      START_SERVICES="1"
      log_info "Dashboard backend + frontend will be started in the background"
      shift
      ;;
    --force-restart)
      FORCE_RESTART="1"
      shift
      ;;
    --project)
      INSTALL_TYPE="project"
      log_info "Installing into project venv"
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--project] [--local] [--global] [--with PACKAGE] [--group GROUP] [--dev] [--force] [--native-tls] [--skip-dashboard] [--require-integrations] [--start] [--force-restart]"
      echo ""
      echo "Options:"
      echo "  --start         Start dashboard backend (:$BACKEND_PORT) + frontend (:$FRONTEND_PORT) in the background after install"
      echo "  --force-restart Kill any process already using those ports (no prompt) before starting"
      echo "  --require-integrations  Fail install if Jira/Bitbucket/Confluence tokens are missing"
      echo "  --project     Install into project venv (default: $PROJECT_VENV)"
      echo "  --local       Install in local agentic-cli/.venv (legacy)"
      echo "  --global      Install globally with sudo"
      echo "  --with PACKAGE  Install with additional dependencies (optional)"
      echo "  --group GROUP  Install with predefined dependency group (optional)"
      echo "  --dev         Development mode - always install from latest source"
      echo "  --force       Force reinstall (useful after code changes)"
      echo "  --native-tls  Use system TLS certificates (fixes corporate VPN certificate issues)"
      echo "  --skip-dashboard  Do not install dashboard frontend (npm) / backend (pip) deps"
      exit 0
      ;;
    *)
      log_error "Unknown option: $1"
      exit 1
      ;;
  esac
done

# ─────────────────────────────────────────────────────────────────────────────

log_header "🚀 Agentic CLI Installation with KEEL Alias"

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

if [ -z "$SKIP_DASHBOARD" ]; then
    log_header "Dashboard dependencies"

    # Backend (Python) — install into the same venv the CLI was installed in.
    BACKEND_DIR="$ROOT_DIR/dashboard/backend"
    if [ -d "$BACKEND_DIR" ]; then
        if [ "$INSTALL_TYPE" = "project" ] || [ "$INSTALL_TYPE" = "local" ]; then
            log_info "Installing dashboard backend deps (FastAPI, uvicorn, httpx)..."
            if uv pip install ${UV_FLAGS:-} -e "$BACKEND_DIR[dev]"; then
                log_ok "Dashboard backend installed"
            else
                log_warn "Backend install failed — run manually: uv pip install -e dashboard/backend[dev]"
            fi
        else
            log_info "Global mode: skipping backend pip (install it inside the project venv)."
        fi
    fi

    # Frontend (Node) — the Vite app needs its npm deps (@xyflow/react, elkjs, …).
    FRONTEND_DIR="$ROOT_DIR/dashboard/frontend"
    if [ -d "$FRONTEND_DIR" ]; then
        if command -v npm &> /dev/null; then
            log_info "Installing dashboard frontend deps (npm install)..."
            if ( cd "$FRONTEND_DIR" && npm install ); then
                log_ok "Dashboard frontend installed"
            else
                log_warn "npm install failed — run manually: ( cd dashboard/frontend && npm install )"
            fi
        else
            log_warn "npm not found — install Node.js 18+, then run: ( cd dashboard/frontend && npm install )"
        fi
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────

log_header "Setting up 'keel' / 'keel' aliases"

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

# Create alias function based on shell. `keel` is the platform command.
case "$SHELL_NAME" in
    bash|zsh)
        ALIAS_COMMAND="alias keel='keel'"
        ;;
    fish)
        ALIAS_COMMAND="alias keel 'keel'"
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
            if ! grep -q "alias keel=" "$config_file" 2>/dev/null; then
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

# ── .env setup ──────────────────────────────────────────────────────────────
# Configure integration tokens (Jira/Confluence/Bitbucket/AI) ONCE in a .env
# file so users don't have to export them into the shell every session.
GLOBAL_ENV_DIR="$HOME/.keel"
GLOBAL_ENV_FILE="$GLOBAL_ENV_DIR/.env"
ENV_EXAMPLE="$ROOT_DIR/.env.example"

# Resolve the keel binary for the chosen install type (may not be on PATH yet).
KEEL_BIN=""
if [ "$INSTALL_TYPE" = "project" ] && [ -x "$PROJECT_VENV/bin/keel" ]; then
    KEEL_BIN="$PROJECT_VENV/bin/keel"
elif [ "$INSTALL_TYPE" = "local" ] && [ -x "$ROOT_DIR/agentic-cli/.venv/bin/keel" ]; then
    KEEL_BIN="$ROOT_DIR/agentic-cli/.venv/bin/keel"
elif command -v keel &> /dev/null; then
    KEEL_BIN="$(command -v keel)"
fi

if [ ! -f "$GLOBAL_ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        log_info "Creating $GLOBAL_ENV_FILE from .env.example..."
        mkdir -p "$GLOBAL_ENV_DIR"
        cp "$ENV_EXAMPLE" "$GLOBAL_ENV_FILE"
        chmod 600 "$GLOBAL_ENV_FILE"
        log_ok "Created $GLOBAL_ENV_FILE (chmod 600)"
        log_warn "Edit $GLOBAL_ENV_FILE and fill in your tokens (Jira/Confluence/Bitbucket)."
    else
        log_warn ".env.example not found — skipping .env scaffold."
    fi
else
    log_ok "Existing .env found at $GLOBAL_ENV_FILE"
fi

# Validate the environment. Non-blocking by default; with --require-integrations
# a missing Jira/Bitbucket/Confluence token fails the install.
if [ -n "$KEEL_BIN" ]; then
    DOCTOR_ARGS=""
    if [ -n "$REQUIRE_INTEGRATIONS" ]; then
        DOCTOR_ARGS="--require-integrations"
    fi
    log_info "Validating environment with 'keel doctor ${DOCTOR_ARGS}'..."
    if "$KEEL_BIN" doctor $DOCTOR_ARGS; then
        log_ok "Environment validation passed"
    elif [ -n "$REQUIRE_INTEGRATIONS" ]; then
        log_error "Required integration tokens are missing."
        log_error "Configure them, then re-run the installer:"
        log_error "  keel init jira|confluence|bitbucket --url <url> --token <pat>"
        log_error "  (or edit $GLOBAL_ENV_FILE)"
        exit 1
    else
        log_warn "Some checks failed — edit $GLOBAL_ENV_FILE (or run: keel init jira|confluence|bitbucket), then re-run: keel doctor"
    fi
else
    log_info "Run 'keel doctor' after activating your environment to check tokens."
fi

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
if command -v keel &> /dev/null; then
    KEEL_VERSION=$(keel --version 2>/dev/null || echo "unknown")
    log_ok "keel command available: $KEEL_VERSION"

    # Test for console formatting errors
    log_info "Testing console output..."
    if keel --version > /dev/null 2>&1; then
        log_ok "Console output working correctly"
    else
        log_warn "Console formatting issues detected (this is a known KEEL CLI issue)"
        log_info "The tool should still function despite formatting errors"
    fi
else
    log_error "keel command not found in PATH"
    if [ "$INSTALL_TYPE" = "project" ]; then
        log_info "For project installation, activate the venv:"
        echo "  source $PROJECT_VENV/bin/activate"
    elif [ "$INSTALL_TYPE" = "local" ]; then
        log_info "For local installation, activate the venv:"
        echo "  source $ROOT_DIR/agentic-cli/.venv/bin/activate"
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────

if [ -n "$START_SERVICES" ] && [ -z "$SKIP_DASHBOARD" ]; then
    log_header "Starting Dashboard Services (background)"
    start_dashboard_services
    echo ""
    log_info "Tail logs:   tail -f dashboard/backend.log dashboard/frontend.log"
    log_info "Stop later:  python scripts/dashboard.py stop   (or ./start-dashboard.ps1 -Stop on Windows)"
elif [ -z "$START_SERVICES" ] && [ -z "$SKIP_DASHBOARD" ]; then
    log_info "Start the dashboard (any OS):  python scripts/dashboard.py start"
    log_info "  or during install:  ./install-agentic-cli.sh --start [--force-restart]"
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
echo "     keel --version"
echo "     keel --help"
echo ""

if [ -n "$ADDITIONAL_DEPS" ]; then
    echo "  3. Your installation includes: $ADDITIONAL_DEPS"
    echo ""
fi

if [ $ALIAS_ADDED -eq 1 ]; then
    echo "  3. Use the 'keel' alias:"
    echo "     keel --version"
    echo "     keel --help"
    echo "     keel <command>"
    echo ""
    echo "  Note: You may need to restart your shell or run:"
    echo "     source ~/.bashrc   # or ~/.zshrc for zsh"
else
    echo "  3. Set up the 'keel' alias manually:"
    if [ -n "$ALIAS_COMMAND" ]; then
        echo "     echo '$ALIAS_COMMAND' >> ~/.${SHELL_NAME}rc"
    else
        echo "     alias keel='agent'"
    fi
fi

echo ""
echo "For more information:"
echo "  - Documentation: $ROOT_DIR/agentic-cli/README.md"
echo "  - Quickstart: $ROOT_DIR/agentic-cli/QUICKSTART.md"
echo ""

log_ok "Setup complete! Happy coding! 🎉"
