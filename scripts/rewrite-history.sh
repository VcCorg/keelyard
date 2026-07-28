#!/usr/bin/env bash
#
# Rewrite git author/committer identities across ALL history, in preparation for
# publishing this repository publicly.
#
# WHY THIS EXISTS
#   The working tree can be completely clean while `git log` still discloses an
#   employer through commit metadata. Publishing a repo publishes its history,
#   so identities must be rewritten before the first public push.
#
# WHY IT WRITES TO A NEW DIRECTORY
#   This script never rewrites your working repo in place. It produces a fresh
#   rewritten clone alongside it, so the original stays intact and you can diff
#   the two before trusting the result.
#
# WHY THE MAPPING IS NOT COMMITTED
#   A mailmap mapping old->new identities necessarily contains the very address
#   we are scrubbing. Committing it would defeat the exercise, exactly like the
#   old guard script that assembled the company name from fragments. So the
#   mapping is injected at runtime and written only to a temp file.
#
# USAGE
#   Provide the mapping via either:
#     1. $KEEL_REWRITE_MAP  — newline-separated "Proper Name <new> <old>" lines
#                             (git mailmap format)
#     2. .mailmap-local     — same content, git-ignored, at the repo root
#
#   Then:
#     bash scripts/rewrite-history.sh [--branches main[,other]] [output-dir]
#
#   --branches  Keep ONLY these branches; all others are deleted before the
#               rewrite, so commits reachable only from them are pruned too.
#               Recommended for publishing: --branches main
#   Default output-dir is ../<repo>-rewritten
#
# AFTERWARDS
#   Push the rewritten clone to a BRAND-NEW empty remote. Do NOT force-push over
#   the existing one: GitHub keeps unreferenced commits reachable by SHA more or
#   less indefinitely, and forks retain them regardless, so a force-push does not
#   actually retract the old metadata.
#
set -euo pipefail

SRC="$(git rev-parse --show-toplevel)"
REPO_NAME="$(basename "$SRC")"

die() { echo "ERROR: $*" >&2; exit 1; }

KEEP_BRANCHES=""
OUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --branches)
      [[ -n "${2:-}" ]] || die "--branches requires a value, e.g. --branches main"
      KEEP_BRANCHES="$2"; shift 2 ;;
    --branches=*)
      KEEP_BRANCHES="${1#*=}"; shift ;;
    -h|--help)
      sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)
      die "unknown option: $1" ;;
    *)
      [[ -n "$OUT" ]] && die "unexpected extra argument: $1"
      OUT="$1"; shift ;;
  esac
done
OUT="${OUT:-$(dirname "$SRC")/${REPO_NAME}-rewritten}"

# --- 1. Resolve the identity mapping (never committed) -----------------------
MAP=""
if [[ -n "${KEEL_REWRITE_MAP:-}" ]]; then
  MAP="$KEEL_REWRITE_MAP"
elif [[ -f "$SRC/.mailmap-local" ]]; then
  MAP="$(cat "$SRC/.mailmap-local")"
else
  die "no identity mapping found.
  Set \$KEEL_REWRITE_MAP or create .mailmap-local (git-ignored) containing
  git mailmap lines, e.g.:
      Jane Doe <jane@users.noreply.github.com> <jane@oldcompany.com>"
fi
[[ -n "${MAP//[[:space:]]/}" ]] || die ".mailmap-local / \$KEEL_REWRITE_MAP is empty"

# --- 2. Require git-filter-repo ----------------------------------------------
# filter-branch is deliberately NOT used as a fallback: it is documented as
# unsafe/deprecated by git itself, mishandles signed tags, and is easy to get
# subtly wrong across 180+ commits.
command -v git-filter-repo >/dev/null 2>&1 || die "git-filter-repo not found.
  Install it first:
      pip install git-filter-repo
  (or: brew install git-filter-repo / apt install git-filter-repo)"

# --- 3. Refuse to clobber an existing output dir -----------------------------
[[ -e "$OUT" ]] && die "output path already exists: $OUT
  Remove it or pass a different output directory."

echo "==> Source repo : $SRC"
echo "==> Output repo : $OUT"
echo

# --- 4. Fresh clone (filter-repo requires one; also keeps the original safe) --
echo "==> Cloning..."
git clone --no-local --no-hardlinks "$SRC" "$OUT" >/dev/null 2>&1
cd "$OUT"

# `git clone` materialises a LOCAL branch only for HEAD; every other branch
# exists solely as a remote-tracking ref. Removing the remote would delete
# those refs, and filter-repo would then rewrite only the one branch it can
# see — silently dropping main and everything else. So promote every remote
# branch to a local branch FIRST, then drop the remote.
# NOTE: iterate FULL refnames. `%(refname:short)` renders refs/remotes/origin/HEAD
# as plain "origin", which slips past a *HEAD filter and would create a junk
# local branch literally named "origin".
echo "==> Promoting remote branches to local branches..."
while IFS= read -r full; do
  [[ -z "$full" || "$full" == */HEAD ]] && continue      # skip the symbolic HEAD
  b="${full#refs/remotes/origin/}"
  [[ -z "$b" || "$b" == "$full" ]] && continue           # not an origin/* ref
  if ! git show-ref --verify --quiet "refs/heads/$b"; then
    git branch "$b" "$full" >/dev/null 2>&1 && echo "    + $b"
  fi
done < <(git for-each-ref --format='%(refname)' refs/remotes/)

# Drop the origin pointing back at the source so nothing can be pushed there.
git remote remove origin 2>/dev/null || true

# --- 4b. Optionally restrict to a subset of branches -------------------------
# Publishing usually wants main ONLY: merged feature branches are noise in a
# public repo. Deleting the other refs before filter-repo runs also makes
# filter-repo prune commits reachable only from them, so their history is
# genuinely dropped rather than merely unreferenced.
if [[ -n "$KEEP_BRANCHES" ]]; then
  echo "==> Restricting to branches: $KEEP_BRANCHES"
  IFS=',' read -r -a _keep <<< "$KEEP_BRANCHES"
  for b in "${_keep[@]}"; do
    b="${b//[[:space:]]/}"
    git show-ref --verify --quiet "refs/heads/$b" || die "branch not found in clone: $b"
  done
  # Detach HEAD so the branch it points at can be deleted if it is not kept.
  git checkout --quiet --detach
  while IFS= read -r b; do
    keep=0
    for k in "${_keep[@]}"; do [[ "$b" == "${k//[[:space:]]/}" ]] && keep=1; done
    if [[ "$keep" -eq 0 ]]; then
      git branch -D "$b" >/dev/null 2>&1 && echo "    - dropped $b"
    fi
  done < <(git for-each-ref --format='%(refname:short)' refs/heads/)
  # Re-attach HEAD to the first kept branch.
  git checkout --quiet "${_keep[0]//[[:space:]]/}"
fi

echo "==> Branches to be rewritten:"
git branch --format='    %(refname:short)'
echo

# --- 5. Identities BEFORE ----------------------------------------------------
echo "==> Identities BEFORE rewrite:"
{ git log --all --format='%an <%ae>'; git log --all --format='%cn <%ce>'; } \
  | sort | uniq -c | sort -rn | sed 's/^/    /'
echo

# --- 6. Rewrite --------------------------------------------------------------
MAILMAP="$(mktemp)"
trap 'rm -f "$MAILMAP"' EXIT
printf '%s\n' "$MAP" > "$MAILMAP"

echo "==> Rewriting all commits..."
git filter-repo --mailmap "$MAILMAP" --force

# --- 7. Identities AFTER -----------------------------------------------------
echo
echo "==> Identities AFTER rewrite:"
{ git log --all --format='%an <%ae>'; git log --all --format='%cn <%ce>'; } \
  | sort | uniq -c | sort -rn | sed 's/^/    /'

# --- 8. Verify the scrubbed addresses are actually gone ----------------------
echo
echo "==> Verifying old addresses no longer appear anywhere in history..."
FAIL=0
# Extract the old address from each mapping line: the LAST <...> on the line.
while IFS= read -r line; do
  [[ -z "${line//[[:space:]]/}" || "$line" == \#* ]] && continue
  old="$(echo "$line" | grep -o '<[^>]*>' | tail -1 | tr -d '<>')"
  [[ -z "$old" ]] && continue
  hits=$({ git log --all --format='%ae'; git log --all --format='%ce'; } \
          | grep -Fc "$old" || true)
  if [[ "$hits" -gt 0 ]]; then
    echo "    FAIL: $hits commit(s) still reference the old address" >&2
    FAIL=1
  else
    echo "    OK: old address fully removed"
  fi
done <<< "$MAP"

echo
if [[ "$FAIL" -ne 0 ]]; then
  die "rewrite incomplete — do NOT publish this clone."
fi

cat <<EOF
==> Rewrite complete: $OUT

Next steps (review before publishing):
  1. Inspect the result:
       cd "$OUT" && git log --format='%h %an <%ae> %s' | less
  2. Confirm the tree still builds and tests pass.
  3. Create a BRAND-NEW empty remote repository, then:
       cd "$OUT"
       git remote add origin <new-remote-url>
       git push -u origin --all
       git push origin --tags

  Do NOT force-push this over the existing remote — old commits stay reachable
  by SHA there, so the old metadata would remain exposed.
EOF
