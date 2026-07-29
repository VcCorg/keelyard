<#
.SYNOPSIS
    Rewrite git author/committer identities across ALL history, in preparation
    for publishing this repository publicly. PowerShell port of
    scripts/rewrite-history.sh.

.DESCRIPTION
    The working tree can be completely clean while `git log` still discloses an
    employer through commit metadata. Publishing a repo publishes its history,
    so identities must be rewritten before the first public push.

    This script never rewrites your working repo in place. It produces a fresh
    rewritten clone alongside it, so the original stays intact.

    The identity mapping is injected at runtime, never committed: a mailmap
    mapping old->new necessarily contains the very address being scrubbed.

.PARAMETER Branches
    Comma-separated list of branches to KEEP. All others are deleted before the
    rewrite, so commits reachable only from them are pruned too.
    Recommended for publishing: -Branches main

.PARAMETER Out
    Output directory. Defaults to ..\<repo>-rewritten

.EXAMPLE
    .\scripts\rewrite-history.ps1 -Branches main -Out ..\keelyard

.NOTES
    Requires git-filter-repo:  pip install git-filter-repo
    Mapping source (either):
      $env:KEEL_REWRITE_MAP   newline-separated mailmap lines
      .mailmap-local          same content, git-ignored, at the repo root

    Afterwards, push to a BRAND-NEW empty remote. Do NOT force-push over an
    existing one: GitHub keeps unreferenced commits reachable by SHA more or
    less indefinitely, and forks retain them regardless.
#>
[CmdletBinding()]
param(
    [string]$Branches,
    [string]$Out
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# PowerShell 7.3+ can turn a non-zero native exit code into a terminating error.
# This script probes exit codes deliberately (`git show-ref --verify` to test
# whether a branch exists), so that behaviour must be off. Declared at SCRIPT
# scope: preference variables resolve up the scope chain, so this applies
# throughout the script without mutating the caller's global state. Harmless
# on 5.1, where the variable is simply unused.
$PSNativeCommandUseErrorActionPreference = $false

# Native commands do not honour $ErrorActionPreference consistently across
# PowerShell 5.1 and 7.x, so exit codes are checked explicitly throughout.
function Invoke-Git {
    param([Parameter(Mandatory)][string[]]$GitArgs, [switch]$Quiet)
    # git writes progress to stderr even when it SUCCEEDS ("Cloning into ...").
    # With `2>&1` those lines become ErrorRecord objects, and under
    # $ErrorActionPreference='Stop' PowerShell promotes them to terminating
    # errors - failing the script on a perfectly good clone. Relax the
    # preference for the duration of the native call and judge success solely
    # by $LASTEXITCODE.
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & git @GitArgs 2>&1
    } finally {
        $ErrorActionPreference = $prev
    }
    if ($LASTEXITCODE -ne 0) {
        throw "git $($GitArgs -join ' ') failed (exit $LASTEXITCODE):`n$($output -join "`n")"
    }
    if (-not $Quiet) { return $output }
}

function Fail([string]$Message) { Write-Error $Message; exit 1 }

# --- 1. Locate the repo ------------------------------------------------------
$src = (Invoke-Git @('rev-parse', '--show-toplevel')) | Select-Object -First 1
$src = $src.Trim()
if (-not $src) { Fail "not inside a git repository" }
$repoName = Split-Path $src -Leaf

if (-not $Out) { $Out = Join-Path (Split-Path $src -Parent) "$repoName-rewritten" }
# .NET APIs use their own working directory; resolve to an absolute path.
$Out = [System.IO.Path]::GetFullPath(
    [System.IO.Path]::Combine((Get-Location).Path, $Out))

# --- 2. Resolve the identity mapping (never committed) -----------------------
$map = $null
if ($env:KEEL_REWRITE_MAP) {
    $map = $env:KEEL_REWRITE_MAP
} else {
    $localMap = Join-Path $src '.mailmap-local'
    if (Test-Path $localMap) { $map = Get-Content $localMap -Raw }
}
if (-not $map -or -not $map.Trim()) {
    Fail @"
no identity mapping found.
  Set `$env:KEEL_REWRITE_MAP or create .mailmap-local (git-ignored) containing
  git mailmap lines, e.g.:
      Jane Doe <jane@users.noreply.github.com> <jane@oldcompany.com>
"@
}

# --- 3. Require git-filter-repo ---------------------------------------------
# filter-branch is deliberately NOT offered as a fallback: git documents it as
# unsafe, and it is easy to get subtly wrong across hundreds of commits.
if (-not (Get-Command git-filter-repo -ErrorAction SilentlyContinue)) {
    Fail "git-filter-repo not found. Install it first:`n    pip install git-filter-repo"
}

# --- 4. Refuse to clobber an existing output dir -----------------------------
if (Test-Path $Out) {
    Fail "output path already exists: $Out`n  Remove it or pass a different -Out."
}

Write-Host "==> Source repo : $src"
Write-Host "==> Output repo : $Out`n"

# --- 5. Fresh clone (keeps the original safe) --------------------------------
Write-Host "==> Cloning..."
Invoke-Git @('clone', '--no-local', '--no-hardlinks', $src, $Out) -Quiet
Push-Location $Out
try {
    # `git clone` materialises a LOCAL branch only for HEAD; every other branch
    # exists solely as a remote-tracking ref. Removing the remote would delete
    # those refs and filter-repo would silently rewrite only one branch. So
    # promote every origin/* ref to a local branch FIRST.
    #
    # Iterate FULL refnames: %(refname:short) renders refs/remotes/origin/HEAD
    # as plain "origin", which would create a junk branch of that name.
    Write-Host "==> Promoting remote branches to local branches..."
    $remoteRefs = @(& git for-each-ref --format='%(refname)' refs/remotes/)
    foreach ($full in $remoteRefs) {
        $full = $full.Trim()
        if (-not $full -or $full.EndsWith('/HEAD')) { continue }
        $prefix = 'refs/remotes/origin/'
        if (-not $full.StartsWith($prefix)) { continue }
        $b = $full.Substring($prefix.Length)
        if (-not $b) { continue }
        & git show-ref --verify --quiet "refs/heads/$b"
        if ($LASTEXITCODE -ne 0) {
            Invoke-Git @('branch', $b, $full) -Quiet
            Write-Host "    + $b"
        }
    }

    Invoke-Git @('remote', 'remove', 'origin') -Quiet

    # --- 5b. Optionally restrict to a subset of branches ---------------------
    if ($Branches) {
        Write-Host "==> Restricting to branches: $Branches"
        # @(...) is REQUIRED: a pipeline yielding one item collapses to a
        # scalar string, and $keep[0] would then index the first CHARACTER
        # ("main" -> "m") rather than the first element.
        $keep = @($Branches.Split(',') | ForEach-Object { $_.Trim() } | Where-Object { $_ })
        if ($keep.Count -eq 0) { Fail "-Branches was given but resolved to no branch names" }
        foreach ($b in $keep) {
            & git show-ref --verify --quiet "refs/heads/$b"
            if ($LASTEXITCODE -ne 0) { Fail "branch not found in clone: $b" }
        }
        # Detach so the checked-out branch can be deleted if it is not kept.
        Invoke-Git @('checkout', '--quiet', '--detach') -Quiet
        $localRefs = @(& git for-each-ref --format='%(refname:short)' refs/heads/)
        foreach ($b in $localRefs) {
            $b = $b.Trim()
            if (-not $b -or ($keep -contains $b)) { continue }
            Invoke-Git @('branch', '-D', $b) -Quiet
            Write-Host "    - dropped $b"
        }
        Invoke-Git @('checkout', '--quiet', $keep[0]) -Quiet
    }

    Write-Host "==> Branches to be rewritten:"
    (& git branch --format='    %(refname:short)') | ForEach-Object { Write-Host $_ }
    Write-Host ""

    # --- 6. Identities BEFORE ------------------------------------------------
    function Get-Identities {
        $a = & git log --all --format='%an <%ae>'
        $c = & git log --all --format='%cn <%ce>'
        return @($a) + @($c)
    }
    Write-Host "==> Identities BEFORE rewrite:"
    Get-Identities | Group-Object | Sort-Object Count -Descending |
        ForEach-Object { Write-Host ("    {0,5}  {1}" -f $_.Count, $_.Name) }
    Write-Host ""

    # --- 7. Rewrite ----------------------------------------------------------
    # Write the mailmap as UTF-8 WITHOUT a BOM and with LF endings. PowerShell
    # 5.1's Out-File defaults to UTF-16LE, and even -Encoding utf8 emits a BOM;
    # either would corrupt the mapping.
    $mailmap = [System.IO.Path]::GetTempFileName()
    try {
        $normalized = ($map -replace "`r`n", "`n").TrimEnd("`n") + "`n"
        [System.IO.File]::WriteAllText(
            $mailmap, $normalized, (New-Object System.Text.UTF8Encoding $false))

        # --- 6b. Pre-flight: does each mapping actually MATCH this repo? ------
        # Without this, a mapping containing a placeholder or a typo rewrites
        # nothing, and the post-rewrite check then "passes" because the bogus
        # address was never in the history to begin with - reporting success
        # while leaving every real address exposed. Record before-counts so the
        # final check can require present-before AND absent-after.
        $preAll = @(& git log --all --format='%ae%n%ce')
        $expected = @()   # list of @{ Old = <addr>; Before = <count> }
        foreach ($line in ($normalized -split "`n")) {
            $line = $line.Trim()
            if (-not $line -or $line.StartsWith('#')) { continue }
            $found = [regex]::Matches($line, '<([^>]*)>')
            if ($found.Count -eq 0) { continue }
            $old = $found[$found.Count - 1].Groups[1].Value
            if (-not $old) { continue }

            if ($old -match '(?i)paste|_here|changeme|oldcompany|example\.com|your[-_.]') {
                Fail @"
the identity mapping still contains placeholder text: '$old'
  Edit .mailmap-local (or `$env:KEEL_REWRITE_MAP) and put your REAL old address there.
  Find it with:  git log --all --format='%ae' | Sort-Object -Unique
"@
            }

            $n = @($preAll | Where-Object { $_ -and $_.Contains($old) }).Count
            if ($n -eq 0) {
                $present = ($preAll | Sort-Object -Unique) -join "`n      "
                Fail @"
the mapping's old address matched NOTHING in this repository: '$old'
  Nothing would be rewritten. This is almost always a typo or a leftover
  placeholder. Addresses actually present in this history:
      $present
"@
            }
            $expected += @{ Old = $old; Before = $n }
            Write-Host "==> Mapping will rewrite $n commit reference(s) for: $old"
        }
        if ($expected.Count -eq 0) {
            Fail "no usable mapping lines found (need: Name <new> <old>)"
        }
        Write-Host ""

        Write-Host "==> Rewriting all commits..."
        & git filter-repo --mailmap $mailmap --force
        if ($LASTEXITCODE -ne 0) { Fail "git filter-repo failed (exit $LASTEXITCODE)" }

        # --- 8. Identities AFTER ---------------------------------------------
        Write-Host "`n==> Identities AFTER rewrite:"
        Get-Identities | Group-Object | Sort-Object Count -Descending |
            ForEach-Object { Write-Host ("    {0,5}  {1}" -f $_.Count, $_.Name) }

        # --- 9. Verify the scrubbed addresses are gone -----------------------
        # Checked against the recorded before-count, so "absent after" counts
        # as success only when the address was actually PRESENT before. An
        # address that never matched cannot certify a no-op rewrite.
        Write-Host "`n==> Verifying old addresses no longer appear anywhere in history..."
        $failed = $false
        $all = @(& git log --all --format='%ae%n%ce')
        foreach ($e in $expected) {
            $after = @($all | Where-Object { $_ -and $_.Contains($e.Old) }).Count
            if ($after -gt 0) {
                Write-Host "    FAIL: $after commit(s) still reference the old address"
                $failed = $true
            } elseif ($e.Before -eq 0) {
                Write-Host "    FAIL: mapping never matched anything - nothing was rewritten"
                $failed = $true
            } else {
                Write-Host "    OK: $($e.Before) reference(s) rewritten, 0 remaining"
            }
        }
        if ($failed) { Fail "rewrite incomplete - do NOT publish this clone." }
    }
    finally { Remove-Item $mailmap -ErrorAction SilentlyContinue }
}
finally { Pop-Location }

Write-Host @"

==> Rewrite complete: $Out

Next steps (review before publishing):
  1. Inspect the result:
       cd "$Out"; git log --format='%h %an <%ae> %s' | Select-Object -First 20
  2. Confirm the tree still builds and tests pass.
  3. Create a BRAND-NEW empty remote repository, then:
       cd "$Out"
       git remote add origin <new-remote-url>
       git push -u origin --all

  Do NOT force-push this over the existing remote - old commits stay reachable
  by SHA there, so the old metadata would remain exposed.
"@
