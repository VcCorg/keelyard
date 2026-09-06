"""``keel guard`` — what a session can reach, before it runs.

``inventory`` is phase one: the Bill of Materials, with no verdict attached.
``findings`` is phase two: a verdict about each component's own surface — whose
credential is shared with whose, and where retrieved context goes to reach the
model.

Neither composes those into a session-level judgement. Whether a set of
components adds up to a refusal is policy, and policy belongs where every other
governance dial lives: a product sets a floor, a domain may tighten it. That
arithmetic is a separate phase and needs a decision about how an organisation
works rather than a default invented here.
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
