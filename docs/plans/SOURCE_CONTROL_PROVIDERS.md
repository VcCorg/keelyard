# Source-control providers: one coordinate, registry-backed

**Status:** backlog. Superseded by nothing yet — v19 shipped the stopgap.

## What shipped instead

Migration v19 added `domains.github_org` and `domains.github_url` beside the
existing `bitbucket_project` / `bitbucket_url`, and registration now requires
*any one* of the four rather than a Bitbucket coordinate specifically. That
unblocked GitHub-hosted teams, who previously could not create a domain at all.

It is a stopgap, and the cost is known and accepted: this is the **second**
hardcoded provider pair. A third — GitLab, Azure DevOps, Gitea — would be a
third pair of columns, a longer `or` chain in `create_domain`, two more form
fields in `DomainOnboarding.tsx`, and another `_integration_item` in the setup
wizard. That is precisely the shape [`CLAUDE.md`](../../CLAUDE.md) warns about:

> **Vendor neutrality is registry-driven.** Code-assist tools, execution
> engines, and watcher triggers are all registries. Add an adapter; do not add
> a branch to a dispatch chain. Sixteen hardcoded branches were removed once
> already — do not reintroduce the pattern.

## What this replaces it with

One provider-neutral coordinate on the domain, resolved through a registry the
way execution engines and code-assist tools already are.

```
domains.repo_provider   TEXT   -- 'bitbucket' | 'github' | …, a registry key
domains.repo_project    TEXT   -- project key, org, or group
domains.repo_url        TEXT   -- canonical project/repo URL
```

A `source_control` registry alongside `execution.registry` and
`code_assist.tools`, with `register_provider(name, adapter)` and an adapter
interface covering what the platform actually asks of a code host today:

- list candidate repositories for a domain (`domain fetch-repos`)
- resolve a clone URL for a repo slug
- report configuration status for the setup wizard

Then registration validates "a provider and a coordinate" once, the wizard
enumerates providers instead of listing them, and a new host is an adapter plus
a registry entry.

## Migration path

The v19 columns are what the neutral migration reads *from*, which is why they
were added rather than worked around:

1. Add the three neutral columns (migration).
2. Backfill: a row with `bitbucket_*` set becomes
   `repo_provider='bitbucket'`; one with `github_*` becomes `'github'`. A row
   with both is the only ambiguous case and is reported for a human decision
   rather than guessed — the same rule the fan-out plan uses for anything it
   cannot rule on.
3. Read from the neutral columns; keep writing both for one release.
4. Drop the per-provider columns once nothing reads them.

## Why it was deferred

Deliberately, with the tradeoff stated: the GitHub gap was blocking real
onboarding on Windows during hackathon testing, and a schema-plus-registry
change is not the thing to do under that pressure. The stopgap is small,
reversible, and leaves the neutral model strictly easier to reach than it was.

**Do this before adding a third provider, not after.**
