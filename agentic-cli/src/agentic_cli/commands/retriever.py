"""Retriever commands — manage named semantic/full-text index instances."""

from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from agentic_cli import retrievers as retr

console = Console()
retriever_app = typer.Typer(help="Manage named retriever instances (FAISS / FTS / KG / hybrid)")


@retriever_app.command("list", help="List named retriever instances.")
def list_retrievers() -> None:
    items = retr.list_instances()
    if not items:
        console.print("[yellow]No retrievers yet.[/yellow]")
        console.print("[dim]Create one with: dva retriever create <name>[/dim]")
        return
    table = Table(show_header=True, header_style="bold magenta", title="Retrievers")
    table.add_column("Name", style="cyan")
    table.add_column("Backend")
    table.add_column("Embedding")
    table.add_column("Source")
    table.add_column("ID", style="dim")
    for r in items:
        table.add_row(
            r.get("name", "—"),
            r.get("backend", "—"),
            r.get("embedding_model") or "—",
            r.get("source") or "—",
            r.get("id", "—"),
        )
    console.print(table)


@retriever_app.command("create", help="Create a named retriever instance.")
def create_retriever(
    name: Annotated[str, typer.Argument(help="Retriever name")],
    backend: Annotated[
        str, typer.Option("--backend", "-b", help="faiss | fts | kg | hybrid")
    ] = "faiss",
    embedding_model: Annotated[
        Optional[str], typer.Option("--embedding", "-e", help="Embedding model")
    ] = None,
    source: Annotated[
        Optional[str], typer.Option("--source", "-s", help="Data source name")
    ] = None,
    description: Annotated[str, typer.Option("--description", "-d", help="Description")] = "",
) -> None:
    try:
        inst = retr.create_instance(
            name, backend=backend, embedding_model=embedding_model,
            source=source, description=description, origin="cli",
        )
    except ValueError as e:
        console.print(f"[red]✗ {e}[/red]")
        raise typer.Exit(1)
    console.print(Panel.fit(
        f"[bold green]✓ Retriever created[/bold green]\n\n"
        f"[bold]Name:[/bold] {inst['name']}\n"
        f"[bold]Backend:[/bold] {inst['backend']}\n"
        f"[bold]Embedding:[/bold] {inst.get('embedding_model') or '—'}\n"
        f"[bold]ID:[/bold] {inst['id']}",
        border_style="green",
    ))


@retriever_app.command("delete", help="Delete a named retriever instance by id.")
def delete_retriever(
    retriever_id: Annotated[str, typer.Argument(help="Retriever id")],
) -> None:
    if retr.delete_instance(retriever_id, origin="cli"):
        console.print(f"[green]✓ Deleted retriever {retriever_id}[/green]")
    else:
        console.print(f"[yellow]No retriever with id {retriever_id}[/yellow]")
        raise typer.Exit(1)
