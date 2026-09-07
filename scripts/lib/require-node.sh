#!/usr/bin/env bash
# Node version gate — one implementation, sourced by every script that runs npm.
#
# The range mirrors dashboard/frontend/package.json `engines.node`, which is
# itself copied from the toolchain: vite 8 and rolldown both declare
# ^20.19.0 || >=22.12.0, and react-router 7 wants >=20. Keep them in step; if
# they ever drift, package.json is the source of truth.
#
# Why this exists rather than a check per script: three scripts had three
# different answers. One demanded exactly 22 (rejecting the Node 20 that CI
# packaged with), one compared version strings lexically — which quietly passes
# Node 8 and 9, since "v8" sorts after "v20" — and one told the user to install
# "Node.js 18+", a version this toolchain cannot run at all. A developer on the
# wrong Node got EBADENGINE warnings that scroll past, then a failure further
# down that reads like a network problem.

# Lowest acceptable release in each supported major line.
KEEL_NODE_MIN_20_MINOR=19   # 20.19.0
KEEL_NODE_MIN_22_MINOR=12   # 22.12.0
KEEL_NODE_RANGE="^20.19.0 || >=22.12.0"

# keel_node_ok <version-string>  — e.g. "v22.22.2" or "20.19.0"
# Returns 0 when the version satisfies the range. Numeric throughout: the point
# of this file is that string comparison gets it wrong.
keel_node_ok() {
    local raw="${1#v}"
    local major minor
    major="${raw%%.*}"
    minor="${raw#*.}"
    minor="${minor%%.*}"
    # A non-numeric component means we could not establish the version, which is
    # not the same as it being acceptable.
    case "$major$minor" in ''|*[!0-9]*) return 1 ;; esac

    if [ "$major" -eq 20 ]; then [ "$minor" -ge "$KEEL_NODE_MIN_20_MINOR" ] && return 0; fi
    if [ "$major" -eq 21 ]; then return 1; fi   # odd release line, outside the range
    if [ "$major" -eq 22 ]; then [ "$minor" -ge "$KEEL_NODE_MIN_22_MINOR" ] && return 0; fi
    if [ "$major" -gt 22 ]; then return 0; fi
    return 1
}

# keel_require_node [--warn]  — check the active node, or explain and exit 1.
# With --warn it reports and returns non-zero instead of exiting, for callers
# that want to continue degraded.
keel_require_node() {
    local mode="${1:-strict}" found
    found="$(node --version 2>/dev/null || true)"

    if [ -z "$found" ]; then
        echo "ERROR: Node.js not found. This project needs $KEEL_NODE_RANGE." >&2
        echo "       Install it, or run 'nvm use' (see dashboard/frontend/.nvmrc)." >&2
        [ "$mode" = "--warn" ] && return 1
        exit 1
    fi

    if keel_node_ok "$found"; then
        return 0
    fi

    echo "ERROR: Node.js $found is not supported. This project needs $KEEL_NODE_RANGE." >&2
    echo "       vite and rolldown refuse to run below it; npm only warns, then the" >&2
    echo "       install fails later in a way that looks like a network problem." >&2
    echo "       Fix: nvm install 22 && nvm use 22   (see dashboard/frontend/.nvmrc)" >&2
    [ "$mode" = "--warn" ] && return 1
    exit 1
}
