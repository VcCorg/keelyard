"""``keel governance`` — one product's floor, across every domain.

    keel governance status --product ACME
    keel governance promote test_coverage_min=85 --product ACME --dry-run
    keel governance promote test_coverage_min=85 --product ACME --apply

Domains may tighten governance freely; loosening needs a recorded exception.
That asymmetry was written into the product meta-repo and never reported on or
enforced across a fleet, so a domain could sit below the floor indefinitely with
nothing to say so.
"""
from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from agentic_cli.config import CLI_NAME
from agentic_cli.meta_repo import governance_fleet as fleet
from agentic_cli.meta_repo import governance_promote as promote_core
from agentic_cli.tracker import get_domains, record_activity

governance_app = typer.Typer(
    help="Governance across a product's domains — compare against the floor, "
         "and promote a value to all of them",
    rich_markup_mode=None,
)
console = Console()

_VERDICT_STYLE = {
    fleet.LOOSER: "red",
    fleet.DIFFERS: "yellow",
    fleet.STRICTER: "green",
    fleet.SAME: "dim",
    fleet.UNSET: "dim",
}
_STATUS_STYLE = {
    "violation": "red", "differs": "yellow", "waived": "cyan",
    "ok": "green", "missing": "dim",
}


def _domains_for(product: Optional[str]) -> tuple[str, list[str]]:
    """Resolve the product and its domain slugs from the tracker."""
    rows = get_domains()
    if product:
        rows = [d for d in rows if (d.get("product") or "").lower() == product.lower()]
    if not rows:
        console.print(f"[red]✗ No domains found{f' for product {product}' if product else ''}.[/red]")
        raise typer.Exit(1)
    resolved = product or (rows[0].get("product") or "")
    return resolved, [d["name"] for d in rows]


@governance_app.command("status")
def status(
    product: Annotated[Optional[str], typer.Option("--product", "-p", help="Product to report on")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Emit the report as JSON")] = False,
    violations_only: Annotated[bool, typer.Option("--violations", help="Only domains below the floor")] = False,
) -> None:
    """Compare every domain's governance to the product floor.

    Read-only and deterministic — no model, no network. A field nobody can
    order (a branch regex, a promotion path) is reported as ``differs`` rather
    than guessed at: calling a different regex "looser" would be a fabrication,
    and calling it "same" would hide it.
    """
    resolved, slugs = _domains_for(product)
    report = fleet.build_report(resolved, slugs)

    if as_json:
        console.print_json(json.dumps(report.to_dict()))
        raise typer.Exit(1 if report.violations else 0)

    if not report.product_meta:
        console.print(f"[yellow]⚠ No product meta-repo found for '{resolved}' — "
                      f"there is no floor to compare against.[/yellow]")
        console.print(f"[dim]Create one with: {CLI_NAME} product init-meta {resolved}[/dim]")
        raise typer.Exit(1)

    # Four columns, not six: the verdict is the point of the report, and at
    # 80 characters a six-column table collapses it to nothing.
    table = Table(title=f"Governance — {resolved}", show_lines=True)
    table.add_column("Domain", no_wrap=True)
    table.add_column("Field", no_wrap=True)
    table.add_column("Domain → floor", overflow="fold")
    table.add_column("Verdict", no_wrap=True)

    shown = report.violations if violations_only else report.domains
    for domain in shown:
        label = (f"{domain.domain}\n"
                 f"[{_STATUS_STYLE.get(domain.status, '')}]{domain.status}[/]")
        if not domain.verdicts:
            table.add_row(label, "[dim]—[/dim]", "[dim]matches the floor[/dim]", "")
            continue
        for index, verdict in enumerate(domain.verdicts):
            note = verdict.verdict
            if verdict.exception_id:
                note += f"\n[cyan]{verdict.exception_id}[/cyan]"
            floor = "unset" if verdict.floor_value is None else verdict.floor_value
            table.add_row(
                label if index == 0 else "",
                verdict.field,
                f"{verdict.domain_value}  →  {floor}",
                f"[{_VERDICT_STYLE.get(verdict.verdict, '')}]{note}[/]",
            )

    console.print(table)
    console.print("  ".join(
        f"[{_STATUS_STYLE.get(k, '')}]{v} {k}[/]" for k, v in report.counts.items()))

    record_activity(command="governance", subcommand="status",
                    args={"product": resolved, "domains": len(slugs),
                          "violations": len(report.violations)})

    if report.violations:
        console.print(
            f"\n[red]{len(report.violations)} domain(s) sit below the floor with no "
            f"recorded exception.[/red]")
        raise typer.Exit(1)


@governance_app.command("promote")
def promote(
    assignment: Annotated[str, typer.Argument(help="<key>=<value>, e.g. test_coverage_min=85")],
    product: Annotated[Optional[str], typer.Option("--product", "-p", help="Product to promote across")] = None,
    domain: Annotated[Optional[list[str]], typer.Option("--domain", help="Limit to these domains. Repeatable.")] = None,
    apply_: Annotated[bool, typer.Option("--apply", help="Write the change (default is a dry run)")] = False,
) -> None:
    """Set one governance value across a product's domains.

    Dry runs by default. A value looser than the product floor is refused
    unless an exception already permits it — refusing at plan time rather than
    warning after the write is the difference between a guard and a comment.
    """
    try:
        key, value = promote_core.parse_assignment(assignment)
    except ValueError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    resolved, slugs = _domains_for(product)
    if domain:
        wanted = {d.strip() for d in domain}
        slugs = [s for s in slugs if s in wanted]
        if not slugs:
            console.print("[red]✗ None of the named domains belong to this product.[/red]")
            raise typer.Exit(1)

    plan = promote_core.plan(resolved, slugs, key, value)

    table = Table(title=f"{key} = {value!r} — blast radius", show_lines=False)
    table.add_column("Domain", no_wrap=True)
    table.add_column("Current", justify="right", no_wrap=True)
    table.add_column("Proposed", justify="right", no_wrap=True)
    table.add_column("vs floor", no_wrap=True)
    table.add_column("", no_wrap=True)

    for change in plan.changes:
        if change.blocked:
            marker = "[red]blocked[/red]"
        elif not change.writable:
            marker = f"[dim]{change.note}[/dim]"
        elif change.is_noop:
            marker = "[dim]no change[/dim]"
        elif change.relaxes_domain:
            marker = "[yellow]will write — relaxes this domain[/yellow]"
        else:
            marker = "[green]will write[/green]"
        table.add_row(
            change.domain,
            "[dim]unset[/dim]" if change.current is None else str(change.current),
            str(change.proposed),
            f"[{_VERDICT_STYLE.get(change.effect, '')}]{change.effect}[/]"
            + (f" ({change.exception_id})" if change.exception_id else ""),
            marker,
        )
    console.print(table)
    console.print(f"[dim]Product floor for {key}: "
                  f"{plan.floor_value if plan.floor_value is not None else 'unset'}[/dim]")

    if plan.relaxing:
        names = ", ".join(c.domain for c in plan.relaxing)
        console.print(
            f"[yellow]⚠ This clears the floor but loosens {len(plan.relaxing)} "
            f"domain(s) that had chosen stricter: {names}.[/yellow]")

    if not apply_:
        console.print("\n[dim](dry run — nothing written. Re-run with --apply.)[/dim]")
        raise typer.Exit(1 if plan.blocked else 0)

    try:
        written = promote_core.apply(plan)
    except promote_core.PromotionRefused as exc:
        console.print(f"\n[red]✗ {exc}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold green]✓[/bold green] Wrote {key} to "
                  f"[bold]{len(written)}[/bold] domain(s).")
    record_activity(command="governance", subcommand="promote",
                    args={"product": resolved, "key": key, "value": value,
                          "written": len(written)})
