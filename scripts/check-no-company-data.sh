#!/usr/bin/env bash
#
# Guard against committing company-specific / internal / secret data.
#
# Usage:
#   scripts/check-no-company-data.sh            # scan STAGED changes (pre-commit)
#   scripts/check-no-company-data.sh --all      # scan ALL tracked files (CI)
#   ALLOW_COMPANY_DATA=1 git commit ...         # emergency bypass (discouraged)
#
# Exit code 0 = clean, 1 = violations found.
set -uo pipefail

if [[ "${ALLOW_COMPANY_DATA:-0}" == "1" ]]; then
  echo "[check-no-company-data] BYPASSED via ALLOW_COMPANY_DATA=1" >&2
  exit 0
fi

# HARD patterns — always block (company data + real secret formats).
# NOTE: 'dva' alone is the CLI/product name and is intentionally NOT blocked.
HARD_PATTERNS=(
  '\bexample\b'                                   # company name (any case)
  '\byour-user\b'                                  # internal username
  '\.example\.(com|net|org)'                      # internal hostnames
  'BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY'
  'AKIA[0-9A-Z]{16}'                             # AWS access key id
  'AIza[0-9A-Za-z_-]{30,}'                       # Google API key
  'gh[pousr]_[A-Za-z0-9]{30,}'                   # GitHub token
  'xox[baprs]-[A-Za-z0-9-]{20,}'                 # Slack token
)

# SECRET patterns — likely hardcoded credentials. Filtered by PLACEHOLDER below
# so documented .env.example placeholders do not trip the guard.
SECRET_PATTERNS=(
  '(secret|token|passwd|password|api[_-]?key)["'"'"' ]*[:=]["'"'"' ]*[A-Za-z0-9/_+-]{20,}'
  'sk-[A-Za-z0-9]{20,}'                          # OpenAI-style key
)

# Values containing any of these are treated as safe placeholders (not secrets).
PLACEHOLDER='your[_-]?|[_-]here|<[a-z]|\$\{|xxx|changeme|placeholder|dummy|redacted|example|todo|fixme|actual-key'

# Forbidden staged paths (real domain data that must stay local/ignored).
PATH_PATTERNS='^(skills/domains/cwow-|kg-infrastructure/docs/(CWOW_|SNF_)|kg-infrastructure/postgres-graph/INGEST_.*_DOMAIN|graphify-out/|knowledge-export/)'

HARD_REGEX=$(IFS='|'; echo "${HARD_PATTERNS[*]}")
SECRET_REGEX=$(IFS='|'; echo "${SECRET_PATTERNS[*]}")

# Skip binary/vendored/large-noise paths, and this guard script itself (it must
# contain the very patterns it searches for).
SKIP='(^|/)(node_modules|dist|build|\.venv|venv)/|package-lock\.json$|\.(html|png|jpg|jpeg|gif|pdf|ico|lock)$|scripts/check-no-company-data\.sh$'

violations=0

report() { echo "  ✗ $1" >&2; violations=$((violations+1)); }

if [[ "${1:-}" == "--all" ]]; then
  SCAN_MODE=all
  list_files() { git ls-files; }
else
  SCAN_MODE=staged
  list_files() { git diff --cached --name-only --diff-filter=ACM; }
fi

# Use process substitution so the loop runs in this shell (bash 3.2 has no
# mapfile) and the `violations` counter persists after the loop.
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  if echo "$f" | grep -qE "$PATH_PATTERNS"; then
    report "forbidden path staged: $f"
    continue
  fi
  echo "$f" | grep -qE "$SKIP" && continue
  [[ -f "$f" ]] || continue

  if [[ "$SCAN_MODE" == "all" ]]; then
    content=$(cat -- "$f")
  else
    # Only inspect ADDED lines in the staged diff.
    content=$(git diff --cached -U0 -- "$f" | grep '^+' | grep -v '^+++')
  fi

  hard=$(printf '%s\n' "$content" | grep -inE "$HARD_REGEX")
  secret=$(printf '%s\n' "$content" | grep -inE "$SECRET_REGEX" | grep -viE "$PLACEHOLDER")
  matches=$(printf '%s\n%s\n' "$hard" "$secret" | grep -v '^$' | head -5)
  if [[ -n "$matches" ]]; then
    report "forbidden content in: $f"
    printf '%s\n' "$matches" | sed 's/^/      /' >&2
  fi
done < <(list_files)

if [[ "$violations" -gt 0 ]]; then
  echo "" >&2
  echo "[check-no-company-data] BLOCKED: $violations issue(s) found." >&2
  echo "Remove the company/internal/secret data above, or (last resort) bypass with:" >&2
  echo "  ALLOW_COMPANY_DATA=1 git commit ..." >&2
  exit 1
fi

echo "[check-no-company-data] OK ($SCAN_MODE scan clean)"
exit 0
