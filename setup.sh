#!/usr/bin/env bash
#
# Agentic Platform — one-shot setup
#
# Installs the CLI, configures the skills registry, bootstraps the MCP
# environment file, and runs preflight diagnostics. Existing component
# scripts are reused (install-agentic-cli.sh, mcp.sh, start-*.sh) so this
# is the single entrypoint for first-time setup.
#
# Usage:
#   ./setup.sh                 # install CLI + configure + bootstrap .env + doctor
#   ./setup.sh --with-mcp      # also start the MCP server stack (Docker)
#   ./setup.sh --skip-install  # skip CLI install (e.g. re-run config + doctor)
#   ./setup.sh --help
#
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}▸${NC} $*"; }
log_ok()    { echo -e "${GREEN}✓${NC} $*"; }
log_warn()  { echo -e "${YELLOW}⚠${NC} $*"; }
log_error() { echo -e "${RED}✗${NC} $*"; }
log_header(){ echo -e "\n${BOLD}$*${NC}"; }

WITH_MCP=0
SKIP_INSTALL=0
INSTALL_ARGS="--project --native-tls"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-mcp)     WITH_MCP=1; shift ;;
    --skip-install) SKIP_INSTALL=1; shift ;;
    --install-args) INSTALL_ARGS="$2"; shift 2 ;;
    -h|--help)
      awk 'NR>1 && /^#/ {sub(/^# ?/,""); print; next} NR>1 {exit}' "${BASH_SOURCE[0]}"
      exit 0 ;;
    *) log_error "Unknown option: $1"; exit 1 ;;
  esac
done

# ---------------------------------------------------------------------------
# 1. Prerequisites
# ---------------------------------------------------------------------------
log_header "1/5  Checking prerequisites"

if ! command -v uv >/dev/null 2>&1; then
  log_error "uv is not installed. Install it: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi
log_ok "uv found ($(uv --version 2>/dev/null || echo present))"

if command -v docker >/dev/null 2>&1; then
  log_ok "docker found"
else
  log_warn "docker not found — MCP/KG infrastructure won't be available (CLI still works)."
fi

# ---------------------------------------------------------------------------
# 2. Install CLI
# ---------------------------------------------------------------------------
log_header "2/5  Installing the CLI"
if [[ "$SKIP_INSTALL" -eq 1 ]]; then
  log_info "Skipping CLI install (--skip-install)."
else
  # shellcheck disable=SC2086
  "$ROOT_DIR/install-agentic-cli.sh" $INSTALL_ARGS
fi

# Resolve the CLI binary (project venv preferred, then PATH)
CLI_BIN=""
if [[ -x "$ROOT_DIR/.venv/bin/agent-cli" ]]; then
  CLI_BIN="$ROOT_DIR/.venv/bin/agent-cli"
elif [[ -x "$ROOT_DIR/.venv/bin/dva" ]]; then
  CLI_BIN="$ROOT_DIR/.venv/bin/dva"
elif command -v dva >/dev/null 2>&1; then
  CLI_BIN="dva"
elif command -v agent-cli >/dev/null 2>&1; then
  CLI_BIN="agent-cli"
fi

# ---------------------------------------------------------------------------
# 3. Configure skills registry
# ---------------------------------------------------------------------------
log_header "3/5  Configuring skills registry"
if [[ -n "$CLI_BIN" && -d "$ROOT_DIR/skills" ]]; then
  "$CLI_BIN" code config --registry "$ROOT_DIR/skills" || \
    log_warn "Could not set skills registry automatically; run: dva code config --registry ./skills"
  log_ok "Skills registry set to ./skills"
else
  log_warn "Skipping registry config (CLI or ./skills not found)."
fi

# ---------------------------------------------------------------------------
# 4. Bootstrap MCP environment + optionally start servers
# ---------------------------------------------------------------------------
log_header "4/5  MCP environment"
MCP_ENV="$ROOT_DIR/mcp-servers/.env"
MCP_ENV_EXAMPLE="$ROOT_DIR/mcp-servers/.env.example"
if [[ -f "$MCP_ENV" ]]; then
  log_ok "mcp-servers/.env already exists (leaving as-is)."
elif [[ -f "$MCP_ENV_EXAMPLE" ]]; then
  cp "$MCP_ENV_EXAMPLE" "$MCP_ENV"
  log_ok "Created mcp-servers/.env from .env.example"
  log_warn "Edit mcp-servers/.env to set your *_SERVER_URL and *_PERSONAL_ACCESS_TOKEN values."
else
  log_warn "No mcp-servers/.env.example found; skipping."
fi

if [[ "$WITH_MCP" -eq 1 ]]; then
  if command -v docker >/dev/null 2>&1; then
    log_info "Starting MCP server stack..."
    ( cd "$ROOT_DIR/mcp-servers" && docker compose up -d )
    log_ok "MCP servers started."
  else
    log_warn "--with-mcp requested but docker is unavailable; skipping."
  fi
else
  log_info "Skipping MCP server startup (pass --with-mcp to start them)."
fi

# ---------------------------------------------------------------------------
# 5. Preflight diagnostics
# ---------------------------------------------------------------------------
log_header "5/5  Running diagnostics (dva doctor)"
if [[ -n "$CLI_BIN" ]]; then
  "$CLI_BIN" doctor || true
else
  log_warn "CLI not found on PATH; activate the venv then run: dva doctor"
fi

log_header "Setup complete"
cat <<EOF
Next steps:
  • Activate the project venv:   source .venv/bin/activate
  • Re-run diagnostics anytime:  dva doctor
  • Onboard a repo:              dva code onboard --path ./your-project
  • Start the dashboard:         ./start-backend.sh   (and ./start-frontend.sh)
EOF
