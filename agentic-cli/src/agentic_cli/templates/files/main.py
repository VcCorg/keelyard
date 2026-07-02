"""Generate main.py content."""

from agentic_cli.templates.config import TemplateConfig
from agentic_cli.templates.enums import Framework, UseCase


def get_main_content(config: TemplateConfig) -> str:
    """Generate main.py content based on configuration."""
    if config.use_case == UseCase.PR_REVIEWER:
        return _get_pr_reviewer_main(config)
    agent_import = _get_agent_import(config.use_case)
    agent_class = _get_agent_class(config.use_case)
    
    return f'''"""Main entry point for the {config.use_case.display_name} agent."""

import argparse
import asyncio

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

{agent_import}
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
        f"[bold cyan]{config.name}[/bold cyan]\\n"
        f"Framework: {config.framework.display_name}\\n"
        f"Use Case: {config.use_case.display_name}\\n"
        f"Mode: {{mode}}",
        border_style="cyan"
    ))

    settings = Settings()
    agent = {agent_class}(settings=settings)

    if mode == "daemon":
        await run_daemon(agent)
    elif mode == "once":
        await run_once(agent)
    else:
        await run_interactive(agent)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="{config.name} agent")
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
        console.print("\\n[yellow]Interrupted.[/yellow]")
'''


def _get_pr_reviewer_main(config: TemplateConfig) -> str:
    """Generate PR reviewer-specific main.py with daemon and interactive modes."""
    return f'''"""Main entry point for the {config.name} PR Reviewer agent."""

import argparse
import asyncio
import logging
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from agents.pr_reviewer_agent import PRReviewerAgent
from config import Settings

load_dotenv()
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)


async def run_daemon(settings: Settings) -> None:
    """Run the PR watcher as a continuous background daemon."""
    console.print(Panel.fit(
        "[bold cyan]{config.name}[/bold cyan]\\n"
        "Mode: daemon (continuous polling)\\n"
        f"Review mode: {{settings.review_mode}}\\n"
        f"Poll interval: {{settings.poll_interval}}s\\n"
        f"Bitbucket MCP: {{settings.bitbucket_mcp_url}}",
        border_style="cyan",
    ))
    agent = PRReviewerAgent(settings=settings)
    await agent.run_daemon()


async def run_interactive(settings: Settings) -> None:
    """Run in interactive mode (manual commands)."""
    console.print(Panel.fit(
        "[bold cyan]{config.name}[/bold cyan]\\n"
        "Mode: interactive\\n"
        "Commands: start, status, reset, quit",
        border_style="cyan",
    ))
    agent = PRReviewerAgent(settings=settings)
    await agent.run_interactive()


async def run_once(settings: Settings) -> None:
    """Run a single poll cycle and exit."""
    agent = PRReviewerAgent(settings=settings)
    await agent.initialize()
    await agent.watcher._poll_cycle()
    console.print("[green]Single poll cycle complete.[/green]")


def main():
    parser = argparse.ArgumentParser(description="{config.name} - PR Review Automation Agent")
    parser.add_argument(
        "--mode", choices=["daemon", "interactive", "once"],
        default="interactive",
        help="Run mode: daemon (continuous), interactive (manual), once (single poll)",
    )
    parser.add_argument("--review-mode", choices=["notify", "review", "auto-approve"], help="Override review mode")
    parser.add_argument("--poll-interval", type=int, help="Override poll interval (seconds)")
    args = parser.parse_args()

    settings = Settings()
    if args.review_mode:
        settings.review_mode = args.review_mode
    if args.poll_interval:
        settings.poll_interval = args.poll_interval

    try:
        if args.mode == "daemon":
            asyncio.run(run_daemon(settings))
        elif args.mode == "once":
            asyncio.run(run_once(settings))
        else:
            asyncio.run(run_interactive(settings))
    except KeyboardInterrupt:
        console.print("\\n[yellow]Interrupted.[/yellow]")


if __name__ == "__main__":
    main()
'''


def _get_agent_import(use_case: UseCase) -> str:
    """Get the appropriate agent import."""
    imports = {
        UseCase.BASIC: "from agents.basic_agent import BasicAgent",
        UseCase.RAG: "from agents.rag_agent import RAGAgent",
        UseCase.KNOWLEDGE_GRAPH: "from agents.kg_agent import KnowledgeGraphAgent",
        UseCase.MULTI_AGENT: "from agents.orchestrator import OrchestratorAgent",
        UseCase.CHATBOT: "from agents.chatbot import ChatbotAgent",
        UseCase.DATA_PIPELINE: "from agents.pipeline_agent import PipelineAgent",
        UseCase.CODE_ASSISTANT: "from agents.code_agent import CodeAssistantAgent",
        UseCase.PR_REVIEWER: "from agents.pr_reviewer_agent import PRReviewerAgent",
    }
    return imports.get(use_case, "from agents.basic_agent import BasicAgent")


def _get_agent_class(use_case: UseCase) -> str:
    """Get the agent class name."""
    classes = {
        UseCase.BASIC: "BasicAgent",
        UseCase.RAG: "RAGAgent",
        UseCase.KNOWLEDGE_GRAPH: "KnowledgeGraphAgent",
        UseCase.MULTI_AGENT: "OrchestratorAgent",
        UseCase.CHATBOT: "ChatbotAgent",
        UseCase.DATA_PIPELINE: "PipelineAgent",
        UseCase.CODE_ASSISTANT: "CodeAssistantAgent",
        UseCase.PR_REVIEWER: "PRReviewerAgent",
    }
    return classes.get(use_case, "BasicAgent")
