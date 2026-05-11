#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Interactive Domain Onboarding Script
#
# Walks you through onboarding a project and domain with superpowers skills,
# KG context, Confluence docs, and repo linking.
#
# Usage:
#   bash scripts/onboard-domain.sh
#   bash scripts/onboard-domain.sh --non-interactive  (uses env vars)
#
# Required env vars (for non-interactive mode):
#   PRODUCT         - Product name (e.g. CWOW)
#   DOMAIN          - Domain name (e.g. Facility)
#   BB_PROJECT      - Bitbucket project key (e.g. CGF)
#   CONF_SPACE      - Confluence space key (e.g. MTT or CWOV)
#   JIRA_PROJECT    - Jira project key (e.g. CWOW)
#
# Optional env vars:
#   DESCRIPTION     - Domain description
#   CONF_RELEASE_URL - Confluence release page URL for KG ingestion
#   GIT_REMOTE      - Git remote for domain-context repo
#   WORKSPACE       - Workspace directory (default: parent of script dir)
#   LIGHTRAG_URL    - LightRAG server URL (default: http://localhost:8001)
#   SKIP_KG         - Set to "1" to skip KG ingestion
#   SKIP_SKILLS     - Set to "1" to skip superpowers skill injection
# ---------------------------------------------------------------------------

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Determine CLI command (prefer dva alias if available)
if command -v dva &>/dev/null; then
    CLI="dva"
else
    CLI="${AGENT_CLI_NAME:-agent-cli}"
fi

# Default workspace: parent of script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WORKSPACE="$(dirname "$SCRIPT_DIR")"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

banner() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║  ${BOLD}Domain Onboarding — Superpowers Skills Integration${NC}${CYAN}  ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

step() {
    echo ""
    echo -e "${BOLD}${GREEN}▶ Step $1: $2${NC}"
    echo -e "${DIM}─────────────────────────────────────────────${NC}"
}

info() {
    echo -e "${DIM}  ℹ $1${NC}"
}

success() {
    echo -e "${GREEN}  ✓ $1${NC}"
}

warn() {
    echo -e "${YELLOW}  ⚠ $1${NC}"
}

error() {
    echo -e "${RED}  ✗ $1${NC}"
}

prompt() {
    local var_name="$1"
    local prompt_msg="$2"
    local default="$3"
    local current_val="${!var_name:-}"

    if [[ -n "$current_val" ]]; then
        echo -e "  ${CYAN}${prompt_msg}${NC} [${current_val}]: \c"
        read -r input
        if [[ -z "$input" ]]; then
            eval "$var_name='$current_val'"
        else
            eval "$var_name='$input'"
        fi
    elif [[ -n "$default" ]]; then
        echo -e "  ${CYAN}${prompt_msg}${NC} [${default}]: \c"
        read -r input
        if [[ -z "$input" ]]; then
            eval "$var_name='$default'"
        else
            eval "$var_name='$input'"
        fi
    else
        echo -e "  ${CYAN}${prompt_msg}${NC}: \c"
        read -r input
        eval "$var_name='$input'"
    fi
}

confirm() {
    local msg="$1"
    echo -e "  ${CYAN}${msg}${NC} [Y/n]: \c"
    read -r yn
    case "$yn" in
        [Nn]*) return 1 ;;
        *) return 0 ;;
    esac
}

# ---------------------------------------------------------------------------
# Parse args
# ---------------------------------------------------------------------------
NON_INTERACTIVE=false
for arg in "$@"; do
    case "$arg" in
        --non-interactive) NON_INTERACTIVE=true ;;
    esac
done

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

banner

# ========================================================================
# Step 1: Gather inputs
# ========================================================================

step "1" "Project & Domain Configuration"

if [[ "$NON_INTERACTIVE" == "true" ]]; then
    : "${PRODUCT:?PRODUCT env var required in non-interactive mode}"
    : "${DOMAIN:?DOMAIN env var required in non-interactive mode}"
    : "${BB_PROJECT:?BB_PROJECT env var required in non-interactive mode}"
    : "${CONF_SPACE:?CONF_SPACE env var required in non-interactive mode}"
    JIRA_PROJECT="${JIRA_PROJECT:-$PRODUCT}"
    DESCRIPTION="${DESCRIPTION:-}"
    CONF_RELEASE_URL="${CONF_RELEASE_URL:-}"
    GIT_REMOTE="${GIT_REMOTE:-}"
    WORKSPACE="${WORKSPACE:-$DEFAULT_WORKSPACE}"
    LIGHTRAG_URL="${LIGHTRAG_URL:-http://localhost:8001}"
    SKIP_KG="${SKIP_KG:-0}"
    SKIP_SKILLS="${SKIP_SKILLS:-0}"
else
    echo -e "  ${DIM}Configure your project and domain. Press Enter to accept defaults.${NC}"
    echo ""

    prompt PRODUCT "Product name (e.g. CWOW, IMTO)" ""
    if [[ -z "$PRODUCT" ]]; then
        error "Product name is required"
        exit 1
    fi
    PRODUCT=$(echo "$PRODUCT" | tr '[:lower:]' '[:upper:]')

    prompt DOMAIN "Domain name (e.g. Facility, Patient)" ""
    if [[ -z "$DOMAIN" ]]; then
        error "Domain name is required"
        exit 1
    fi

    prompt BB_PROJECT "Bitbucket project key (e.g. CGF)" ""
    if [[ -z "$BB_PROJECT" ]]; then
        error "Bitbucket project key is required"
        exit 1
    fi
    BB_PROJECT=$(echo "$BB_PROJECT" | tr '[:lower:]' '[:upper:]')

    prompt CONF_SPACE "Confluence space key (e.g. MTT, CWOV)" ""
    if [[ -z "$CONF_SPACE" ]]; then
        error "Confluence space key is required"
        exit 1
    fi
    CONF_SPACE=$(echo "$CONF_SPACE" | tr '[:lower:]' '[:upper:]')

    prompt JIRA_PROJECT "Jira project key" "$PRODUCT"
    JIRA_PROJECT=$(echo "$JIRA_PROJECT" | tr '[:lower:]' '[:upper:]')

    prompt DESCRIPTION "Domain description (optional)" ""

    prompt CONF_RELEASE_URL "Confluence release page URL for KG ingestion (optional)" ""

    prompt GIT_REMOTE "Git remote URL for domain-context repo (optional)" ""

    WORKSPACE="${WORKSPACE:-$DEFAULT_WORKSPACE}"
    prompt WORKSPACE "Workspace directory" "$WORKSPACE"

    LIGHTRAG_URL="${LIGHTRAG_URL:-http://localhost:8001}"
    prompt LIGHTRAG_URL "LightRAG server URL" "$LIGHTRAG_URL"

    SKIP_KG="${SKIP_KG:-0}"
    SKIP_SKILLS="${SKIP_SKILLS:-0}"

    if ! confirm "Skip KG ingestion?"; then
        SKIP_KG=0
    else
        SKIP_KG=1
    fi

    if ! confirm "Skip superpowers skill injection?"; then
        SKIP_SKILLS=0
    else
        SKIP_SKILLS=1
    fi
fi

# Derived values
PRODUCT_UPPER=$(echo "$PRODUCT" | tr '[:lower:]' '[:upper:]')
DOMAIN_SLUG=$(echo "${PRODUCT_UPPER}-${DOMAIN}" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

echo ""
echo -e "  ${BOLD}Configuration Summary:${NC}"
echo -e "  ─────────────────────────────────"
echo -e "  ${CYAN}Product:${NC}         $PRODUCT_UPPER"
echo -e "  ${CYAN}Domain:${NC}          $DOMAIN"
echo -e "  ${CYAN}Domain Slug:${NC}     $DOMAIN_SLUG"
echo -e "  ${CYAN}Bitbucket:${NC}       $BB_PROJECT"
echo -e "  ${CYAN}Confluence:${NC}      $CONF_SPACE"
echo -e "  ${CYAN}Jira:${NC}            $JIRA_PROJECT"
echo -e "  ${CYAN}Workspace:${NC}       $WORKSPACE"
echo -e "  ${CYAN}LightRAG:${NC}        $LIGHTRAG_URL"
echo -e "  ${CYAN}KG Ingestion:${NC}    $([ "$SKIP_KG" == "1" ] && echo "Skipped" || echo "Enabled")"
echo -e "  ${CYAN}Skills:${NC}          $([ "$SKIP_SKILLS" == "1" ] && echo "Skipped" || echo "Enabled")"
if [[ -n "${CONF_RELEASE_URL:-}" ]]; then
    echo -e "  ${CYAN}Release Page:${NC}    $CONF_RELEASE_URL"
fi
if [[ -n "${GIT_REMOTE:-}" ]]; then
    echo -e "  ${CYAN}Git Remote:${NC}      $GIT_REMOTE"
fi
echo ""

if [[ "$NON_INTERACTIVE" != "true" ]]; then
    if ! confirm "Proceed with this configuration?"; then
        echo "Aborted."
        exit 0
    fi
fi

# ========================================================================
# Step 2: Register product (if not exists)
# ========================================================================

step "2" "Register Product"

if $CLI product show "$PRODUCT_UPPER" &>/dev/null 2>&1; then
    success "Product '$PRODUCT_UPPER' already registered"
else
    info "Registering product '$PRODUCT_UPPER'..."
    $CLI product create "$PRODUCT_UPPER" || {
        error "Failed to register product"
        exit 1
    }
    success "Product '$PRODUCT_UPPER' registered"
fi

# ========================================================================
# Step 3: Register domain
# ========================================================================

step "3" "Register Domain"

DOMAIN_CREATE_ARGS=(
    "$DOMAIN"
    "--product" "$PRODUCT_UPPER"
    "--bb" "$BB_PROJECT"
    "--confluence" "$CONF_SPACE"
    "--jira" "$JIRA_PROJECT"
)

if [[ -n "${DESCRIPTION:-}" ]]; then
    DOMAIN_CREATE_ARGS+=("--description" "$DESCRIPTION")
fi

info "Registering domain '$DOMAIN_SLUG'..."
$CLI domain create "${DOMAIN_CREATE_ARGS[@]}" || {
    warn "Domain create returned non-zero (may already exist)"
}
success "Domain '$DOMAIN_SLUG' registered"

# ========================================================================
# Step 4: Fetch and link repositories
# ========================================================================

step "4" "Fetch & Link Repositories"

info "Fetching repos from Bitbucket project '$BB_PROJECT'..."
$CLI domain fetch-repos "$DOMAIN_SLUG" --all 2>/dev/null || {
    warn "Could not fetch repos (Bitbucket MCP may not be running)"
    info "You can link repos manually later: $CLI domain link-repo $DOMAIN_SLUG <repo-slug>"
}

# ========================================================================
# Step 5: Fetch and track Confluence docs
# ========================================================================

step "5" "Fetch & Track Confluence Docs"

info "Fetching Confluence docs from space '$CONF_SPACE'..."
$CLI domain add-docs "$DOMAIN_SLUG" --all 2>/dev/null || {
    warn "Could not fetch Confluence docs (Confluence MCP may not be running)"
    info "You can add docs manually later: $CLI domain add-docs $DOMAIN_SLUG"
}

# ========================================================================
# Step 6: Ingest into Knowledge Graph
# ========================================================================

if [[ "$SKIP_KG" != "1" ]]; then
    step "6" "Ingest into Knowledge Graph"

    # Domain docs
    info "Ingesting domain docs into KG..."
    $CLI kg ingest submit --domain "$DOMAIN_SLUG" --lightrag-url "$LIGHTRAG_URL" 2>/dev/null || {
        warn "KG ingestion failed (LightRAG may not be running)"
        info "Retry later: $CLI kg ingest submit --domain $DOMAIN_SLUG"
    }

    # Release page (if provided)
    if [[ -n "${CONF_RELEASE_URL:-}" ]]; then
        info "Ingesting Confluence release page..."
        $CLI kg ingest submit \
            --source "$CONF_RELEASE_URL" \
            --format confluence \
            --workspace "$DOMAIN_SLUG" \
            --lightrag-url "$LIGHTRAG_URL" 2>/dev/null || {
            warn "Release page ingestion failed"
            info "Retry: $CLI kg ingest submit --source $CONF_RELEASE_URL --format confluence"
        }
    fi
else
    step "6" "Ingest into Knowledge Graph (SKIPPED)"
    info "KG ingestion skipped. Run later: $CLI kg ingest submit --domain $DOMAIN_SLUG"
fi

# ========================================================================
# Step 7: Initialize domain context repo with superpowers skills
# ========================================================================

step "7" "Initialize Domain Context Repo"

INIT_CONTEXT_ARGS=(
    "$DOMAIN_SLUG"
    "--lightrag-url" "$LIGHTRAG_URL"
)

if [[ "$SKIP_SKILLS" == "1" ]]; then
    INIT_CONTEXT_ARGS+=("--no-bootstrap-skills")
fi

if [[ -n "${GIT_REMOTE:-}" ]]; then
    INIT_CONTEXT_ARGS+=("--git-remote" "$GIT_REMOTE")
fi

CONTEXT_DIR="$WORKSPACE/${DOMAIN_SLUG}-domain-context"
INIT_CONTEXT_ARGS+=("--output" "$CONTEXT_DIR")

info "Creating domain context repo at $CONTEXT_DIR..."
$CLI domain init-context "${INIT_CONTEXT_ARGS[@]}" || {
    error "Domain context initialization failed"
    exit 1
}
success "Domain context repo created at $CONTEXT_DIR"

# ========================================================================
# Step 8: Generate domain-specific persona skills
# ========================================================================

step "8" "Generate Domain Persona Skills"

info "Generating domain persona skills (domain, dev, qa, sm, ba)..."
$CLI domain gen-skills "$DOMAIN_SLUG" 2>/dev/null || {
    warn "Skill generation failed (may need KG context)"
    info "Retry later: $CLI domain gen-skills $DOMAIN_SLUG"
}

# ========================================================================
# Step 9: Summary
# ========================================================================

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  ${BOLD}${GREEN}Onboarding Complete!${NC}${CYAN}                                   ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  ${BOLD}Domain:${NC}       $DOMAIN_SLUG"
echo -e "  ${BOLD}Context:${NC}      $CONTEXT_DIR"
echo -e "  ${BOLD}Skills:${NC}       $([ "$SKIP_SKILLS" == "1" ] && echo "Skipped" || echo "Superpowers injected")"
echo -e "  ${BOLD}KG:${NC}           $([ "$SKIP_KG" == "1" ] && echo "Skipped" || echo "Ingested")"
echo ""
echo -e "  ${BOLD}Next Steps:${NC}"
echo -e "  ${DIM}─────────────────────────────────────────────${NC}"
echo ""

if [[ -n "${GIT_REMOTE:-}" ]]; then
    echo -e "  1. Push context repo:"
    echo -e "     ${CYAN}cd $CONTEXT_DIR && git push -u origin main${NC}"
    echo ""
fi

echo -e "  2. Onboard a repo with domain skills:"
echo -e "     ${CYAN}$CLI code onboard --path ./<repo-name> \\${NC}"
echo -e "     ${CYAN}  --domain $DOMAIN_SLUG \\${NC}"
echo -e "     ${CYAN}  --use-domain-skills \\${NC}"
if [[ -n "${GIT_REMOTE:-}" ]]; then
    echo -e "     ${CYAN}  --domain-context-repo $GIT_REMOTE \\${NC}"
fi
echo -e "     ${CYAN}  --kg${NC}"
echo ""

echo -e "  3. Validate skills against real tasks:"
echo -e "     ${CYAN}$CLI domain validate-skills $DOMAIN_SLUG --list${NC}"
echo -e "     ${CYAN}$CLI domain validate-skills $DOMAIN_SLUG \\${NC}"
echo -e "     ${CYAN}  --skill requesting-code-review --feedback works${NC}"
echo ""

echo -e "  4. Fork a skill for domain customization:"
echo -e "     ${CYAN}$CLI domain fork-skill $DOMAIN_SLUG \\${NC}"
echo -e "     ${CYAN}  --skill requesting-code-review \\${NC}"
echo -e "     ${CYAN}  --reason \"Add domain-specific rules\"${NC}"
echo ""

echo -e "  5. View domain details:"
echo -e "     ${CYAN}$CLI domain show $DOMAIN_SLUG${NC}"
echo -e "     ${CYAN}$CLI domain repos $DOMAIN_SLUG${NC}"
echo -e "     ${CYAN}$CLI domain docs $DOMAIN_SLUG${NC}"
echo -e "     ${CYAN}$CLI domain list-skills $DOMAIN_SLUG${NC}"
echo ""
