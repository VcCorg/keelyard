"""``keel guard`` — what a session can reach, before it runs.

``inventory`` is phase one: the Bill of Materials, with no verdict attached.
``findings`` is phase two: a verdict about each component's own surface — whose
credential is shared with whose, and where retrieved context goes to reach the
model.

Neither composes those into a session-level judgement. Whether a set of
components adds up to a refusal is policy, and policy belongs where every other
governance dial lives: a product sets a floor, a domain may tighten it. ``check`` is phase three: that arithmetic, composed against the product's
governance floor — which a domain may tighten freely and may loosen only with a
recorded exception. It is the one place a session-level verdict is reached, and
it never turns "could not establish" into a pass.
"""
from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from agentic_cli.config import CLI_NAME
from agentic_cli.tracker import record_activity

console = Console()

guard_app = typer.Typer(help="What an agent can reach — the Agent Bill of Materials.")


@guard_app.command("inventory")
def guard_inventory(
    domain: Annotated[Optional[str], typer.Argument(help="Domain to inventory")] = None,
    session: Annotated[Optional[str], typer.Option(
        "--session", "-s", help="Also show which of these that session actually reached")] = None,
    unused: Annotated[bool, typer.Option(
        "--unused", help="Only what is configured and was never touched")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="Emit the inventory as JSON")] = False,
) -> None:
    """Everything a session could reach: skills, MCP servers, repos, engine.

    KeelTrace answers what an agent *did* reach, after the fact. This is the
    other question, asked before anything runs — and the two together are the
    useful pair: a component configured and never touched is surface carried for
    nothing, which is invisible until they sit side by side.

    No risk scores. Whether a set of components adds up to a refusal is policy,
    and policy belongs with the governance floor rather than being invented here.

    Credential *names* are shown; values are never read. What a credential can do
    is not knowable from here without asking the service, so this stops at naming
    it rather than guessing.
    """
    from agentic_cli import guard

    inventory = guard.collect(domain=domain or "", session_id=session or "")

    if as_json:
        console.print_json(json.dumps(inventory.to_dict()))
        raise typer.Exit(0)

    components = inventory.unused if unused else inventory.components
    if not components:
        if unused:
            console.print("[green]✓[/green] Nothing configured went untouched.")
        else:
            console.print(f"[yellow]Nothing enumerable"
                          f"{f' for {domain}' if domain else ''}.[/yellow]")
            console.print(f"[dim]An inventory needs a domain to resolve skills and "
                          f"repos: {CLI_NAME} guard inventory <domain>[/dim]")
        raise typer.Exit(0)

    title = "Agent Bill of Materials" + (f" — {domain}" if domain else "")
    table = Table(title=title + (" (unused only)" if unused else ""), show_lines=False)
    table.add_column("Kind", no_wrap=True)
    table.add_column("Name", no_wrap=True)
    table.add_column("Detail", overflow="fold")
    table.add_column("Credentials", overflow="fold")
    if session:
        table.add_column("Reached", justify="center", no_wrap=True)

    for kind in guard.KIND_ORDER:
        for component in [c for c in components if c.kind == kind]:
            # A disabled component is still surface — it is one config edit from
            # being live — so it is listed and marked, never dropped.
            name = (f"{component.name}" if component.enabled
                    else f"[dim]{component.name} (disabled)[/dim]")
            creds = (", ".join(component.credentials) if component.credentials
                     else "[dim]—[/dim]")
            row = [guard.KIND_LABELS.get(kind, kind), name,
                   component.detail or "[dim]—[/dim]", creds]
            if session:
                row.append("[green]yes[/green]" if component.reached
                           else ("[dim]no[/dim]" if component.reached is False
                                 else "[dim]?[/dim]"))
            table.add_row(*row)
    console.print(table)

    credentialed = len(inventory.credentialed)
    if credentialed:
        console.print(f"[yellow]{credentialed} component(s) are handed "
                      f"credentials.[/yellow] [dim]Names only — what they grant "
                      f"is not knowable from here.[/dim]")
    if session and not unused:
        never = len(inventory.unused)
        if never:
            console.print(f"[dim]{never} configured and untouched by that session "
                          f"— see `--unused`.[/dim]")
    if not inventory.complete:
        # Named rather than omitted: a Bill of Materials silently missing a
        # section reads as a clean bill.
        console.print(f"[yellow]Could not enumerate: "
                      f"{', '.join(inventory.unknown)}. This inventory is "
                      f"incomplete.[/yellow]")

    record_activity(command="guard", subcommand="inventory",
                    args={"domain": domain or "*", "components": len(components),
                          "complete": inventory.complete})


@guard_app.command("findings")
def guard_findings(
    domain: Annotated[Optional[str], typer.Argument(help="Domain to assess")] = None,
    session: Annotated[Optional[str], typer.Option(
        "--session", "-s", help="A session id, so an idle credential can be spotted")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Emit the findings as JSON")] = False,
) -> None:
    """What is true about each component: credential sharing, and model egress.

    One verdict per component, never composed into a verdict about the session.
    There are no severities and no score here — ranking findings is a severity
    judgement wearing a different hat, and severity belongs to the governance
    floor that a product sets and a domain may tighten.

    **Credential scope stops at what a name supports.** What a key can do is not
    knowable without asking the service, so nothing here guesses it. What names
    alone *do* establish is sharing: one credential handed to two servers means
    compromising either reaches both. With a session, the other knowable fact is
    a credential held for a server that run never touched.

    **Egress is checked at the runtime, not the prefix.** `local:` means
    OpenAI-compatible, not on-host, and a runtime URL can point anywhere — so a
    model named local whose runtime is remote is reported as what it is.
    """
    from agentic_cli import guard, guard_findings as assessor

    inventory = guard.collect(domain=domain or "", session_id=session or "")
    result = assessor.assess(inventory)

    if as_json:
        console.print_json(json.dumps(result.to_dict()))
        raise typer.Exit(0)

    if not result.findings:
        console.print("[green]✓[/green] Nothing to report about these components.")
        console.print("[dim]Not a clean bill: this rules on credential sharing "
                      "and model egress only.[/dim]")
    else:
        table = Table(title="Component findings" + (f" — {domain}" if domain else ""),
                      show_lines=True)
        table.add_column("Component", no_wrap=True)
        table.add_column("Finding", no_wrap=True)
        table.add_column("What is true", overflow="fold")

        for finding in result.findings:
            statement = finding.statement
            if not finding.observed:
                statement += "\n[dim](rests on absence of evidence, not an "
                statement += "observation)[/dim]"
            if finding.limit:
                statement += f"\n[dim]Not saying: {finding.limit}[/dim]"
            table.add_row(finding.component, finding.code, statement)
        console.print(table)

    if not result.complete:
        # Same rule as the inventory: a report silently missing a verdict reads
        # as a report that reached one.
        console.print(f"[yellow]Could not rule on: "
                      f"{', '.join(result.unruled)}.[/yellow]")
    if not session and inventory.credentialed:
        console.print(f"[dim]No session given, so an unused credential cannot be "
                      f"spotted: {CLI_NAME} guard findings {domain or '<domain>'} "
                      f"--session <id>[/dim]")

    record_activity(command="guard", subcommand="findings",
                    args={"domain": domain or "*", "findings": len(result.findings),
                          "complete": result.complete})


@guard_app.command("check")
def guard_check(
    domain: Annotated[str, typer.Argument(help="Domain to judge")],
    session: Annotated[Optional[str], typer.Option(
        "--session", "-s", help="A session id, so an idle credential can be spotted")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Emit the judgement as JSON")] = False,
) -> None:
    """Judge this domain's agent surface against its product's governance floor.

    The one place a session-level verdict is reached. `inventory` says what is
    reachable, `findings` says what is true about each piece, and this says
    whether the floor permits it — a floor the product sets, a domain may
    tighten freely, and a domain may loosen only with a recorded exception.

    **Where a domain loosened the floor with nothing on record, the floor
    applies.** Judging a session against a policy its owner had no authority to
    set would let anyone pass by editing their own governance.yaml.

    **Undetermined is not a soft pass.** If a section could not be enumerated, or
    where inference is served from could not be established, the answer is
    undetermined — we might be failing and cannot tell. Passing there would
    certify exactly what was never examined.

    Exit status: 0 pass, 1 fail, 2 undetermined — so a pipeline can tell a
    refusal from a gap without parsing the output.
    """
    from agentic_cli import guard, guard_findings as assessor, guard_floor

    inventory = guard.collect(domain=domain, session_id=session or "")
    judgement = guard_floor.compose(assessor.assess(inventory), domain)

    if as_json:
        console.print_json(json.dumps(judgement.to_dict()))
        raise typer.Exit(_exit_for(judgement))

    style = {guard_floor.PASS: "green", guard_floor.FAIL: "red",
             guard_floor.UNDETERMINED: "yellow"}[judgement.verdict]
    console.print(f"[bold {style}]{judgement.verdict.upper()}[/bold {style}] "
                  f"— {domain}")
    if judgement.detail:
        console.print(f"[dim]{judgement.detail}[/dim]")

    if judgement.rulings:
        table = Table(show_lines=False)
        table.add_column("Component", no_wrap=True)
        table.add_column("Finding", no_wrap=True)
        table.add_column("Outcome", no_wrap=True)
        table.add_column("Why", overflow="fold")
        for ruling in judgement.rulings:
            colour = {guard_floor.DENIED: "red",
                      guard_floor.INDETERMINATE: "yellow",
                      guard_floor.WAIVED: "cyan",
                      guard_floor.UNGOVERNED: "dim"}.get(ruling.outcome, "green")
            why = ruling.detail or ""
            if ruling.exception_id:
                why += f" [dim](exception {ruling.exception_id})[/dim]"
            if ruling.disregarded_domain_value:
                # The loosening is itself the violation, and it is the fleet
                # report that carries it — say where to look.
                why += ("\n[dim]This domain set a looser value with nothing on "
                        "record permitting it, so the floor applied. See "
                        f"`{CLI_NAME} governance fleet`.[/dim]")
            table.add_row(ruling.component, ruling.code,
                          f"[{colour}]{ruling.outcome}[/{colour}]",
                          why or "[dim]—[/dim]")
        console.print(table)

    if judgement.unruled:
        console.print(f"[yellow]Could not rule on: "
                      f"{', '.join(judgement.unruled)}.[/yellow] "
                      f"[dim]Not a pass — we might be failing and cannot tell.[/dim]")
    if judgement.ungoverned:
        console.print(f"[dim]{len(judgement.ungoverned)} finding(s) the floor "
                      f"makes no rule about. A gap in the policy, not a "
                      f"violation.[/dim]")

    record_activity(command="guard", subcommand="check",
                    args={"domain": domain, "verdict": judgement.verdict,
                          "violations": len(judgement.violations)})
    raise typer.Exit(_exit_for(judgement))


def _exit_for(judgement) -> int:
    """0 pass, 1 fail, 2 undetermined — a refusal and a gap are different."""
    from agentic_cli import guard_floor

    return {guard_floor.PASS: 0, guard_floor.FAIL: 1,
            guard_floor.UNDETERMINED: 2}[judgement.verdict]
