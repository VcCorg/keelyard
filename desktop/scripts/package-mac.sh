#!/usr/bin/env bash
set -euo pipefail

# package-mac.sh — Node 22 + install + build/pack the Keel desktop app on macOS.
# Run from the desktop/ directory: ./scripts/package-mac.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

cleanup_mounted_images() {
    # Eject stray Keel/electron-builder temp disk images. Detach by device node
    # so we still remove images whose backing file has already been deleted.
    # Run in a subshell so a flaky hdiutil/awk pipeline can't abort the whole script.
    (
        set +e +o pipefail
        hdiutil info 2>/dev/null | awk '
            /^image-path[ \t]*:/ { img=$0; sub(/^image-path[ \t]*:[ \t]*/, "", img) }
            /^\/dev\/disk/ {
                if (img ~ /\/Keel.*\.dmg|\/T\/t-.*\/[0-9]+\.dmg/) print $1
            }
        ' | while read -r dev; do
            echo "Detaching stale disk device: $dev" >&2
            hdiutil detach "$dev" -force >/dev/null 2>&1 || true
        done
    )
}

trap 'cleanup_mounted_images || true' EXIT

# Activate the repo's Python venv so the backend build can find pyinstaller.
VENV_ACTIVATE="$SCRIPT_DIR/../../.venv/bin/activate"
if [ -f "$VENV_ACTIVATE" ]; then
    # shellcheck source=/dev/null
    source "$VENV_ACTIVATE"
else
    echo "ERROR: project .venv not found at $VENV_ACTIVATE" >&2
    echo "Run the repo setup first (e.g. ./install-agentic-cli.sh)." >&2
    exit 1
fi

if ! command -v pyinstaller >/dev/null 2>&1; then
    echo "pyinstaller not found in .venv; installing it now..." >&2
    if command -v uv >/dev/null 2>&1; then
        uv pip install --python "$SCRIPT_DIR/../../.venv/bin/python" pyinstaller
    else
        echo "ERROR: pyinstaller is missing and 'uv' is not available to install it." >&2
        exit 1
    fi
fi

# Ensure Node 22 is active (use nvm if available, otherwise validate system node)
if [ -s "$HOME/.nvm/nvm.sh" ]; then
    # shellcheck source=/dev/null
    source "$HOME/.nvm/nvm.sh"
    nvm install 22
    nvm use 22
else
    NODE_MAJOR=$(node --version 2>/dev/null | cut -d'v' -f2 | cut -d'.' -f1 || true)
    if [ "${NODE_MAJOR:-}" != "22" ]; then
        echo "ERROR: Node.js 22 is required and nvm is not available." >&2
        echo "Install Node 22 (or nvm) and re-run this script." >&2
        exit 1
    fi
fi

cleanup_stale_builds() {
    # Eject stray Keel/electron-builder temp disk images.
    cleanup_mounted_images

    # Kill smoke-test keel-backend processes that were not cleaned up.
    # These can lock files in resources/backend/keel-backend and prevent rebuild.
    pkill -f 'desktop/resources/backend/keel-backend/keel-backend' 2>/dev/null || true
    pkill -f 'release/mac.*/Keel.app/Contents/Resources/backend/keel-backend' 2>/dev/null || true

    # Remove the old frozen backend so PyInstaller doesn't fight stale locks/.DS_Store.
    # macOS Finder can drop .DS_Store files that block recursive removal; retry briefly.
    if [ -d resources/backend/keel-backend ]; then
        for i in 1 2 3; do
            find resources/backend/keel-backend -name .DS_Store -delete 2>/dev/null || true
            if rm -rf resources/backend/keel-backend 2>/dev/null; then
                break
            fi
            echo "  ... retrying backend cleanup ($i/3)" >&2
            sleep 1
        done
    fi
}

cleanup_stale_builds

mkdir -p release

{
    npm install
    npm run build:electron
    npm run build:frontend
    npm run build:backend
    npm run smoke:backend

    # Build one DMG arch at a time to avoid hdiutil "Resource temporarily unavailable" races.
    npx electron-builder --mac dmg:arm64 --publish never
    npx electron-builder --mac dmg:x64 --publish never
} 2>&1 | tee release/package-mac.log
