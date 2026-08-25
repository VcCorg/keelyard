# Domain meta-repo template overlay

Files here are rendered over the built-in scaffold defaults at the **end** of
`keel domain init-meta`, and offered to existing meta-repos by
`keel domain template upgrade`. This is the writable half of the template: the
defaults live as Python string literals in `../scaffold.py` and cannot be
written back to programmatically.

Nothing is hand-authored here. Files arrive by promotion:

```bash
keel domain template promote <domain>                      # what could I contribute?
keel domain template promote <domain> -f docs/PLAYBOOK.md --show   # review the tokenized body
keel domain template promote <domain> -f docs/PLAYBOOK.md --apply  # write + branch it
```

Layout mirrors the meta-repo exactly — `docs/PLAYBOOK.md` here becomes
`docs/PLAYBOOK.md` in every domain.

## Placeholders

Bodies are tokenized: `{{domain}}`, `{{product}}`, `{{description}}`,
`{{owner}}`. Doubled braces (not single) so that literal JSON and shell
`${VAR}` expansion in template bodies stay unambiguous. Anything else is
rendered verbatim into every domain — which is why promotion refuses content
that still contains emails, ticket keys, URLs, dates or the source domain's own
words unless a human passes `--allow-unreviewed`.

`README.md` at this top level (this file) and `.keep`/`.gitkeep` are overlay
bookkeeping and are never rendered into a meta-repo. `docs/README.md` *would*
be, since only the top level is treated as bookkeeping.

## Hosting the overlay elsewhere

Set `KEEL_TEMPLATE_OVERLAY=/path/to/overlay` to keep promoted governance content
in your own repo instead of inside the installed package. Promotions branch and
commit in whatever git repo contains that directory, then hand you the push
command — the overlay is shared by every domain, so publishing stays a reviewed
step.
