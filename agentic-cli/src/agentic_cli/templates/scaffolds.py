"""Scaffold individual agents into existing projects.

Supports adding new agents to projects created via ``agent-cli project create``,
or to any project that follows the ``src/agents/`` convention.
"""

import tempfile
from pathlib import Path
from typing import Optional

from agentic_cli.templates.enums import Framework, Tool, UseCase
from agentic_cli.templates.config import TemplateConfig, USE_CASE_TOOLS


# ------------------------------------------------------------------
# Agent type registry
# ------------------------------------------------------------------

AGENT_TYPES: dict[str, dict] = {
    "basic": {
        "use_case": UseCase.BASIC,
        "description": "Simple Gemini-backed LLM agent",
        "system_prompt": "a helpful assistant",
    },
    "rag": {
        "use_case": UseCase.RAG,
        "description": "RAG agent with document retrieval and vector search",
        "system_prompt": "a RAG agent that retrieves and synthesizes information from documents",
    },
    "chatbot": {
        "use_case": UseCase.CHATBOT,
        "description": "Conversational agent with memory and context management",
        "system_prompt": "a conversational chatbot with persistent memory",
    },
    "knowledge-graph": {
        "use_case": UseCase.KNOWLEDGE_GRAPH,
        "description": "Agent integrated with Neo4j knowledge graph",
        "system_prompt": "a knowledge graph agent that queries and manages graph data",
    },
    "code-assistant": {
        "use_case": UseCase.CODE_ASSISTANT,
        "description": "Code generation, review, and refactoring agent",
        "system_prompt": "a code assistant that helps with generation, review, and refactoring",
    },
    "data-pipeline": {
        "use_case": UseCase.DATA_PIPELINE,
        "description": "Data processing and ETL pipeline agent",
        "system_prompt": "a data pipeline agent for ETL and data processing workflows",
    },
    "pr-reviewer": {
        "use_case": UseCase.PR_REVIEWER,
        "description": "Automated PR review with Bitbucket MCP integration",
        "complex": True,
    },
    "scrum-master": {
        "use_case": UseCase.SCRUM_MASTER,
        "description": "Domain-scoped Scrum Master with Jira/Confluence/Bitbucket MCP",
        "complex": True,
    },
    "custom": {
        "use_case": None,
        "description": "Blank agent skeleton — implement process() and initialize()",
        "system_prompt": "a helpful agent",
    },
}


# ------------------------------------------------------------------
# Name helpers
# ------------------------------------------------------------------

def to_class_name(name: str) -> str:
    """Convert agent name to PascalCase class name ending in Agent."""
    parts = name.replace("-", "_").split("_")
    cls = "".join(p.capitalize() for p in parts if p)
    if not cls.endswith("Agent"):
        cls += "Agent"
    return cls


def to_file_name(name: str) -> str:
    """Convert agent name to snake_case .py file name."""
    return name.replace("-", "_") + ".py"


def get_agent_tools(agent_type: str) -> list[Tool]:
    """Get the tools associated with an agent type."""
    info = AGENT_TYPES.get(agent_type, {})
    uc = info.get("use_case")
    if uc:
        return USE_CASE_TOOLS.get(uc, [])
    return []


# ------------------------------------------------------------------
# Main scaffold entry point
# ------------------------------------------------------------------

def scaffold_agent(
    project_path: Path,
    agent_name: str,
    agent_type: str,
    domain: Optional[str] = None,
    force: bool = False,
) -> dict:
    """Scaffold an agent into an existing project.

    Returns a dict with keys:
        created      – list of relative paths created
        skipped      – list of relative paths skipped (already exist)
        agent_class  – generated class name
        agent_file   – generated file name
    """
    info = AGENT_TYPES.get(agent_type)
    if not info:
        raise ValueError(
            f"Unknown agent type: {agent_type}. "
            f"Available: {', '.join(AGENT_TYPES.keys())}"
        )

    agents_dir = project_path / "src" / "agents"
    tools_dir = project_path / "src" / "tools"

    agents_dir.mkdir(parents=True, exist_ok=True)
    tools_dir.mkdir(parents=True, exist_ok=True)

    # Ensure __init__.py exists
    for d in [agents_dir, tools_dir]:
        init = d / "__init__.py"
        if not init.exists():
            init.write_text('"""Package initialization."""\n')

    created: list[str] = []
    skipped: list[str] = []

    class_name = to_class_name(agent_name)
    file_name = to_file_name(agent_name)
    agent_file = agents_dir / file_name

    # --- 1. Agent file ------------------------------------------------
    if agent_file.exists() and not force:
        skipped.append(f"src/agents/{file_name}")
    else:
        if info.get("complex") and agent_type == "pr-reviewer":
            content = _pr_reviewer_agent_content(class_name)
        elif info.get("complex") and agent_type == "scrum-master":
            content = _scrum_master_agent_content(class_name, agent_name)
        else:
            content = _simple_agent_content(
                class_name,
                agent_type,
                info.get("system_prompt", "a helpful agent"),
            )
        agent_file.write_text(content)
        created.append(f"src/agents/{file_name}")

    # --- 2. Missing tool files ----------------------------------------
    from agentic_cli.templates.files.tools import TOOL_TEMPLATES

    tools = get_agent_tools(agent_type)
    for tool in tools:
        if tool in TOOL_TEMPLATES:
            tool_file = tools_dir / f"{tool.value}.py"
            if not tool_file.exists():
                tool_file.write_text(TOOL_TEMPLATES[tool])
                created.append(f"src/tools/{tool_file.name}")
            else:
                skipped.append(f"src/tools/{tool_file.name}")

    # --- 3. Complex supporting files ----------------------------------
    if info.get("complex"):
        c, s = _scaffold_complex_support(
            project_path, agent_type, agent_name, domain,
        )
        created.extend(c)
        skipped.extend(s)

    return {
        "created": created,
        "skipped": skipped,
        "agent_class": class_name,
        "agent_file": file_name,
    }


# ------------------------------------------------------------------
# Simple agent template
# ------------------------------------------------------------------

def _simple_agent_content(class_name: str, agent_type: str, system_prompt: str) -> str:
    display = agent_type.replace("-", " ").title()
    return f'''"""{display} agent."""

from typing import Any, Dict
import os

from google import genai
from agents.base import BaseAgent


class {class_name}(BaseAgent):
    """{display} — {system_prompt}."""

    def __init__(self, settings: Any = None):
        super().__init__(settings)
        self.client = None
        self.model_name = "gemini-2.0-flash-001"

    async def initialize(self) -> None:
        self.model_name = (
            self.settings.vertex_ai_model if self.settings else "gemini-2.0-flash-001"
        )
        self.client = None
        try:
            if self.settings and self.settings.google_project_id:
                self.client = genai.Client(
                    vertexai=True,
                    project=self.settings.google_project_id,
                    location=self.settings.google_location,
                )
            elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
                self.client = genai.Client()
        except Exception:
            self.client = None
        self._initialized = True

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            await self.initialize()
        if self.client is None:
            return {{
                "response": "Model client not configured. Set GOOGLE_PROJECT_ID (Vertex AI) or GOOGLE_API_KEY (AI Studio).",
                "status": "error",
            }}
        message = input_data.get("message", "")
        history = "\\n".join(
            f"{{m.role}}: {{m.content}}" for m in self.get_history(10)
        )
        prompt = (
            f"You are {system_prompt}.\\n\\n"
            f"History:\\n{{history}}\\n\\n"
            f"User: {{message}}\\n\\nAssistant:"
        )
        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            return {{"response": response.text, "status": "success"}}
        except Exception as e:
            return {{"response": f"Error: {{str(e)}}", "status": "error"}}


# --- Evaluation entrypoint --------------------------------------------------
# Module-level callable so this agent is evaluation-ready by default:
#   dva eval run agent <module.path>:answer <eval-config>
# The eval framework's resolve_agent() calls fn(str) -> str; this wraps the
# agent's async process() and returns just the response text.
_eval_agent = None


async def answer(input_text: str) -> str:
    """Run {class_name} on a single input and return its response text."""
    global _eval_agent
    if _eval_agent is None:
        try:
            from config import Settings
            _eval_agent = {class_name}(settings=Settings())
        except Exception:
            _eval_agent = {class_name}()
    result = await _eval_agent.process({{"message": input_text}})
    if isinstance(result, dict):
        return str(result.get("response", ""))
    return str(result)
'''


# ------------------------------------------------------------------
# PR reviewer agent template
# ------------------------------------------------------------------

def _pr_reviewer_agent_content(class_name: str) -> str:
    return f'''"""PR Reviewer Agent — watches for PRs and performs AI code review."""

import asyncio
import logging
from typing import Any, Dict

from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class {class_name}(BaseAgent):
    """Agent that watches for new PRs and performs AI-powered code review.

    Modes:
        - notify:       Log new PRs only (no actions taken)
        - review:       Post AI review comments on new PRs
        - auto-approve: Review + automatically approve/needs-work
    """

    def __init__(self, settings: Any = None):
        super().__init__(settings)
        self.watcher = None

    async def initialize(self) -> None:
        from watcher import PRWatcher

        self.watcher = PRWatcher(self.settings)
        self._initialized = True
        logger.info("{class_name} initialized")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            await self.initialize()
        message = input_data.get("message", "").strip().lower()

        if message in ("start", "watch", "run"):
            await self.watcher._poll_cycle()
            return {{"response": "Poll cycle completed.", "status": "success"}}

        elif message == "status":
            count = self.watcher.state.get_seen_count()
            return {{
                "response": (
                    f"Seen {{count}} PR(s). "
                    f"Mode: {{self.settings.review_mode}}. "
                    f"Polling: {{self.settings.poll_interval}}s"
                ),
                "status": "success",
            }}

        elif message == "reset":
            self.watcher.state.reset()
            return {{"response": "PR state reset.", "status": "success"}}

        else:
            return {{
                "response": "Commands: start (run poll), status, reset, quit",
                "status": "success",
            }}

    async def run_daemon(self) -> None:
        """Run the watcher as a continuous background daemon."""
        if not self._initialized:
            await self.initialize()
        await self.watcher.start()
'''


# ------------------------------------------------------------------
# Scrum master agent template
# ------------------------------------------------------------------

def _scrum_master_agent_content(class_name: str, name: str) -> str:
    display = name.replace("-", " ").title()
    return f'''"""{display} — Scrum Master agent with MCP integration."""

import logging
import os
from typing import Any, Dict

from google import genai
from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class {class_name}(BaseAgent):
    """{display} — uses Jira, Confluence, and Bitbucket MCP servers.

    Capabilities:
        - Sprint status summaries
        - Daily standup generation
        - Blocker detection
        - Stale ticket and un-reviewed PR detection
    """

    def __init__(self, settings: Any = None):
        super().__init__(settings)
        self.client = None
        self.model_name = "gemini-2.0-flash-001"
        self.sprint_mgr = None
        self.standup_gen = None

    async def initialize(self) -> None:
        self.model_name = (
            self.settings.vertex_ai_model if self.settings else "gemini-2.0-flash-001"
        )
        self.client = None
        try:
            if self.settings and self.settings.google_project_id:
                self.client = genai.Client(
                    vertexai=True,
                    project=self.settings.google_project_id,
                    location=self.settings.google_location,
                )
            elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
                self.client = genai.Client()
        except Exception:
            self.client = None

        from sprint_manager import SprintManager
        from standup_generator import StandupGenerator

        self.sprint_mgr = SprintManager()
        self.standup_gen = StandupGenerator()
        self._initialized = True
        logger.info("{class_name} initialized")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            await self.initialize()
        if self.client is None:
            return {{
                "response": "Model client not configured. Set GOOGLE_PROJECT_ID (Vertex AI) or GOOGLE_API_KEY (AI Studio).",
                "status": "error",
            }}
        message = input_data.get("message", "")
        history = "\\n".join(
            f"{{m.role}}: {{m.content}}" for m in self.get_history(10)
        )
        prompt = (
            "You are a Scrum Master assistant. Help the team with sprint "
            "management, blockers, standup notes, and process improvements.\\n\\n"
            f"History:\\n{{history}}\\n\\n"
            f"User: {{message}}\\n\\nAssistant:"
        )
        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            return {{"response": response.text, "status": "success"}}
        except Exception as e:
            return {{"response": f"Error: {{str(e)}}", "status": "error"}}
'''


# ------------------------------------------------------------------
# Complex type supporting files (reuses existing template generators)
# ------------------------------------------------------------------

def _scaffold_complex_support(
    project_path: Path,
    agent_type: str,
    agent_name: str,
    domain: Optional[str] = None,
) -> tuple[list[str], list[str]]:
    """Generate supporting files for complex agent types.

    Uses the existing template generators in a temp directory, then copies
    only files that do not already exist in the target project.
    """
    use_case = AGENT_TYPES[agent_type]["use_case"]
    config = TemplateConfig(
        name=agent_name,
        framework=Framework.ADK,
        use_case=use_case,
        domain_name=domain,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        (tmp / "src" / "agents").mkdir(parents=True)
        (tmp / "src" / "tools").mkdir(parents=True)
        (tmp / "src" / "workflows").mkdir(parents=True)

        if agent_type == "pr-reviewer":
            from agentic_cli.templates.files.pr_reviewer import (
                generate_pr_reviewer_files,
            )
            generate_pr_reviewer_files(tmp, config)
        elif agent_type == "scrum-master":
            from agentic_cli.templates.files.scrum_master import (
                generate_scrum_master_files,
            )
            generate_scrum_master_files(tmp, config)

        created: list[str] = []
        skipped: list[str] = []

        for f in tmp.rglob("*.py"):
            rel = f.relative_to(tmp)
            rel_str = str(rel)
            # Skip agent files — we generated the agent class separately
            if rel_str.startswith("src/agents/"):
                continue
            target = project_path / rel
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f.read_text())
                created.append(rel_str)
            else:
                skipped.append(rel_str)

        return created, skipped
