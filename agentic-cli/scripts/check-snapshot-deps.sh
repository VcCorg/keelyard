#!/usr/bin/env bash
#
# check-snapshot-deps.sh — validate (and optionally install) the dependencies
# required to build a per-domain Devin snapshot from a meta-repo blueprint.
#
# Background:
#   `dva domain init-meta <slug>` commits a Devin DRS blueprint
#   (.devin/environment.yaml + .devin/setup.sh) into the domain meta-repo.
#   `dva domain build-snapshot <slug>` turns that blueprint into a reusable
#   snapshot_id. This script checks that everything that flow needs is present.
#
# Usage:
#   scripts/check-snapshot-deps.sh                 # validate only
#   scripts/check-snapshot-deps.sh --install       # validate + install what's safe
#   scripts/check-snapshot-deps.sh --meta <path>   # also validate a blueprint
#
# Exit code: 0 if all REQUIRED deps are satisfied, 1 otherwise.

set -uo pipefail

INSTALL=0
META_PATH=""

while [ $# -gt 0 ]; do
  case "$1" in
    --install) INSTALL=1; shift ;;
    --meta) META_PATH="${2:-}"; shift 2 ;;
    -h|--help)
      sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

# ── pretty output ────────────────────────────────────────────────────────────
if [ -t 1 ]; then
  GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; YELLOW=$'\033[0;33m'; DIM=$'\033[2m'; BOLD=$'\033[1m'; NC=$'\033[0m'
else
  GREEN=""; RED=""; YELLOW=""; DIM=""; BOLD=""; NC=""
fi

FAIL=0      # number of failed REQUIRED checks
WARN=0      # number of failed OPTIONAL checks

pass() { printf "  ${GREEN}✓${NC} %-22s %s\n" "$1" "${2:-}"; }
fail() { printf "  ${RED}✗${NC} %-22s %s\n" "$1" "${2:-}"; FAIL=$((FAIL+1)); }
warn() { printf "  ${YELLOW}!${NC} %-22s %s\n" "$1" "${2:-}"; WARN=$((WARN+1)); }
hint() { printf "      ${DIM}%s${NC}\n" "$1"; }

have() { command -v "$1" >/dev/null 2>&1; }

# ── checks ─────────────────────────────────────────────────────────────────--
printf "${BOLD}Devin snapshot build — dependency check${NC}\n\n"
printf "${BOLD}Required tools${NC}\n"

# git — submodule init inside setup.sh
if have git; then
  pass "git" "$(git --version 2>/dev/null)"
else
  fail "git" "not found"
  hint "Install via your OS package manager (e.g. 'brew install git')."
fi

# make — setup.sh runs 'make init' (has a git fallback, but make is expected)
if have make; then
  pass "make" "$(make --version 2>/dev/null | head -n1)"
else
  fail "make" "not found"
  hint "Install build tools (e.g. 'xcode-select --install' on macOS)."
fi

# python3 — required; pyyaml is bundled with `dva`, so a bare-python miss is
# only a warning (blueprint rendering happens inside the dva process).
if have python3; then
  PYV="$(python3 --version 2>/dev/null)"
  if python3 -c "import yaml" >/dev/null 2>&1; then
    pass "python3 + pyyaml" "$PYV"
  else
    pass "python3" "$PYV"
    if [ "$INSTALL" -eq 1 ]; then
      echo "      installing pyyaml..."
      if have uv; then uv pip install pyyaml >/dev/null 2>&1; else python3 -m pip install pyyaml >/dev/null 2>&1; fi
    fi
    python3 -c "import yaml" >/dev/null 2>&1 \
      && pass "pyyaml" "$PYV" \
      || warn "pyyaml" "not in system python (ok — bundled with dva)"
  fi
else
  fail "python3" "not found"
fi

# dva — the agentic CLI that owns init-meta / build-snapshot
if have dva; then
  pass "dva (agentic-cli)" "$(dva --version 2>/dev/null | head -n1)"
else
  if [ "$INSTALL" -eq 1 ] && [ -f "pyproject.toml" ]; then
    echo "      installing agentic-cli (editable)..."
    if have uv; then uv pip install -e . >/dev/null 2>&1; else python3 -m pip install -e . >/dev/null 2>&1; fi
    if have dva; then pass "dva (agentic-cli)" "installed"; else fail "dva" "install failed"; fi
  else
    fail "dva (agentic-cli)" "not found"
    hint "From agentic-cli/: 'make install' (or 'uv pip install -e .')."
  fi
fi

# devin CLI — performs the DRS build (only needed for an automated build;
# you can also build elsewhere and register with --snapshot-id).
if have devin; then
  pass "devin CLI" "$(devin --version 2>/dev/null | head -n1)"
  # DRS reachability: `whoami` needs a Devin (Cognition) API URL in credentials.
  # Enterprise/Windsurf logins populate api_server_url but NOT devin_api_url, so
  # DRS can be present yet unprovisioned. Distinguish those cases.
  DRS_OUT="$(devin cloud drs whoami 2>&1)"
  if echo "$DRS_OUT" | grep -qiE "no devin_api_url|no Devin API URL|re-authenticate"; then
    fail "devin DRS access" "not provisioned (no devin_api_url in credentials)"
    hint "Your login looks like enterprise/Windsurf (api_server_url only)."
    hint "DRS talks to Cognition's snapshot-setup backend and needs Devin creds."
    hint "Provision one of:"
    hint "  • env: DRS_DEVIN_API_URL=<url> DRS_API_KEY=<key> DRS_ORG_ID=<org>"
    hint "  • or re-auth against a Devin account: devin auth logout && devin auth login"
    hint "Until then, build elsewhere and register: dva domain build-snapshot <slug> --snapshot-id <id>"
  elif echo "$DRS_OUT" | grep -qiE "error"; then
    warn "devin DRS access" "whoami returned an error"
    hint "$(echo "$DRS_OUT" | head -n1)"
  else
    pass "devin DRS access" "reachable"
  fi
else
  fail "devin CLI" "not found"
  hint "Required for 'dva domain build-snapshot' DRS builds."
  hint "Install + authenticate the Devin CLI (see your Devin org's docs)."
  hint "Alternative: build elsewhere then register the id:"
  hint "  dva domain build-snapshot <slug> --snapshot-id <id>"
fi

printf "\n${BOLD}Credentials${NC}\n"
if [ -n "${DEVIN_API_KEY:-}" ]; then
  pass "DEVIN_API_KEY" "set (${#DEVIN_API_KEY} chars)"
else
  fail "DEVIN_API_KEY" "not set"
  hint "export DEVIN_API_KEY=... (needed for sessions + DRS auth)."
fi

printf "\n${BOLD}Optional${NC}\n"
# graphify — setup.sh refreshes the KG if present; safe no-op otherwise
if have graphify; then
  pass "graphify" "$(graphify --version 2>/dev/null | head -n1)"
else
  warn "graphify" "not found (KG refresh in setup.sh will be skipped)"
fi
# uv — preferred installer
if have uv; then pass "uv" "$(uv --version 2>/dev/null)"; else warn "uv" "not found (pip will be used instead)"; fi

# ── optional: validate a specific blueprint ──────────────────────────────────
if [ -n "$META_PATH" ]; then
  printf "\n${BOLD}Blueprint (%s)${NC}\n" "$META_PATH"
  ENV_FILE="$META_PATH/.devin/environment.yaml"
  SETUP_FILE="$META_PATH/.devin/setup.sh"
  if [ -f "$ENV_FILE" ]; then
    if have python3 && python3 -c "import yaml,sys; yaml.safe_load(open('$ENV_FILE'))" >/dev/null 2>&1; then
      pass "environment.yaml" "valid YAML"
    else
      pass "environment.yaml" "present"
    fi
  else
    fail "environment.yaml" "missing at $ENV_FILE"
    hint "Generate it: dva domain gen-blueprint <slug>"
  fi
  if [ -f "$SETUP_FILE" ]; then
    if [ -x "$SETUP_FILE" ]; then pass "setup.sh" "present (executable)"; else warn "setup.sh" "present but not executable"; fi
  else
    fail "setup.sh" "missing at $SETUP_FILE"
  fi
fi

# ── summary ───────────────────────────────────────────────────────────────--
printf "\n${BOLD}Summary${NC}: "
if [ "$FAIL" -eq 0 ]; then
  printf "${GREEN}all required dependencies satisfied${NC}"
  [ "$WARN" -gt 0 ] && printf " ${YELLOW}(%d optional missing)${NC}" "$WARN"
  printf "\n"
  exit 0
else
  printf "${RED}%d required dependency/ies missing${NC}" "$FAIL"
  [ "$WARN" -gt 0 ] && printf " ${YELLOW}(+%d optional)${NC}" "$WARN"
  printf "\n"
  [ "$INSTALL" -eq 0 ] && hint "Tip: re-run with --install to auto-install what's safe."
  exit 1
fi
