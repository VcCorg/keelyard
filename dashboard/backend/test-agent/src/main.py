"""Main entry point for the Basic Agent agent."""

import argparse
import asyncio

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from agents.basic_agent import BasicAgent
from config import Settings

load_dotenv()
console = Console()


async def run_interactive(agent) -> None:
    """Run the agent in interactive (stdin) mode."""
    await agent.run_interactive()


async def run_daemon(agent) -> None:
    """Initialize the agent and idle so it runs as a background daemon."""
    await agent.initialize()
    console.print("[green]Agent initialized (daemon mode). Idling for work...[/green]")
    while True:
        await asyncio.sleep(3600)


async def run_once(agent) -> None:
    """Initialize the agent, confirm readiness, then exit cleanly."""
    await agent.initialize()
    console.print("[green]Agent initialized (once mode). Exiting.[/green]")


async def main(mode: str) -> None:
    """Run the agent in the selected mode."""
    console.print(Panel.fit(
        f"[bold cyan]test-agent[/bold cyan]\n"
        f"Framework: Google ADK (Agent Development Kit)\n"
        f"Use Case: Basic Agent\n"
        f"Mode: {mode}",
        border_style="cyan"
    ))

    settings = Settings()
    agent = BasicAgent(settings=settings)

    if mode == "daemon":
        await run_daemon(agent)
    elif mode == "once":
        await run_once(agent)
    else:
        await run_interactive(agent)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="test-agent agent")
    parser.add_argument(
        "--mode", choices=["interactive", "daemon", "once"], default="interactive",
        help="Run mode: interactive (stdin), daemon (background), once (init + exit)",
    )
    # Accepted for compatibility with `agent start` (ignored by non-PR agents).
    parser.add_argument("--review-mode")
    parser.add_argument("--poll-interval", type=int)
    args = parser.parse_args()

    try:
        asyncio.run(main(args.mode))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
