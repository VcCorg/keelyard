#!/usr/bin/env bash
#
# Security-gate the skills registry with NVIDIA SkillSpector.
# https://github.com/NVIDIA/SkillSpector
#
# Scans every skill under skills/skills/<name>/ and fails the build if any
# skill is rated DO_NOT_INSTALL (SkillSpector exit code 1 / risk score > 50).
# Runs pattern-only for deterministic, offline-friendly CI results.
#
# Usage:
#   scripts/scan-skills-security.sh                 # scan skills/skills/*
#   scripts/scan-skills-security.sh path/to/skill   # scan a single skill dir
#   SKILLSPECTOR_BIN=/path/to/skillspector scripts/scan-skills-security.sh
#
# Exit code 0 = all skills clean (SAFE/CAUTION), 1 = at least one blocked.
set -uo pipefail

BIN="${SKILLSPECTOR_BIN:-skillspector}"

if ! command -v "$BIN" >/dev/null 2>&1; then
  echo "[scan-skills-security] SkillSpector not found on PATH." >&2
  echo "  Install: uv tool install git+https://github.com/NVIDIA/skillspector.git" >&2
  exit 2
fi

# Targets: explicit args, or every skill directory in the registry.
targets=()
if [[ $# -gt 0 ]]; then
  targets=("$@")
else
  for d in skills/skills/*/; do
    [[ -d "$d" ]] && targets+=("$d")
  done
fi

if [[ ${#targets[@]} -eq 0 ]]; then
  echo "[scan-skills-security] No skill directories found under skills/skills/." >&2
  exit 0
fi

blocked=0
scanned=0
for target in "${targets[@]}"; do
  scanned=$((scanned + 1))
  # Exit code 1 == DO_NOT_INSTALL (a valid verdict); 2 == error.
  "$BIN" scan "$target" --format sarif >"/tmp/skillspector-$(basename "$target").sarif" 2>/dev/null
  code=$?
  if [[ $code -eq 1 ]]; then
    echo "::error::SkillSpector blocked skill: $target (DO_NOT_INSTALL)"
    blocked=$((blocked + 1))
  elif [[ $code -eq 2 ]]; then
    echo "::warning::SkillSpector errored while scanning: $target"
  else
    echo "[scan-skills-security] OK: $target"
  fi
done

echo "[scan-skills-security] Scanned $scanned skill(s); $blocked blocked."
[[ $blocked -eq 0 ]] || exit 1
