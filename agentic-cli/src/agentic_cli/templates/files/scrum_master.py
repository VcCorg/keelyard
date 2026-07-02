"""Generate Scrum Master agent template files.

Produces a domain-scoped Scrum Master agent that uses Jira, Confluence, and
Bitbucket MCP servers to:
  - Summarise sprint status and blockers
  - Generate standup / sprint review notes
  - Detect stale tickets and un-reviewed PRs
  - Read persona skills for domain context
"""

from pathlib import Path
from agentic_cli.templates.config import TemplateConfig


def generate_scrum_master_files(target_dir: Path, config: TemplateConfig) -> None:
    """Generate Scrum Master specific files."""
    src_dir = target_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    _generate_mcp_clients(src_dir, config)
    _generate_sprint_manager(src_dir, config)
    _generate_standup_generator(src_dir, config)
    _generate_domain_loader(src_dir)


# ---------------------------------------------------------------------------
# MCP client wrapper (reusable SSE client)
# ---------------------------------------------------------------------------

def _generate_mcp_clients(src_dir: Path, config: TemplateConfig) -> None:
    content = '''"""MCP Client wrappers for Jira, Confluence, and Bitbucket servers."""

import asyncio
import json
import logging
import os
from typing import Any, Optional

from mcp.client.sse import sse_client
from mcp import ClientSession

logger = logging.getLogger(__name__)


class MCPClient:
    """Generic SSE MCP client."""

    def __init__(self, sse_url: str, name: str = "mcp"):
        self.sse_url = sse_url
        self.name = name

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> str:
        arguments = arguments or {}
        try:
            async with sse_client(self.sse_url) as streams:
                read_stream, write_stream = streams
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    if result.content:
                        texts = [item.text for item in result.content if hasattr(item, "text")]
                        return "\\n".join(texts) if texts else str(result.content)
                    return ""
        except Exception as e:
            logger.error(f"[{self.name}] Error calling {tool_name}: {e}")
            raise

    async def list_tools(self) -> list[dict]:
        try:
            async with sse_client(self.sse_url) as streams:
                read_stream, write_stream = streams
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return [{"name": t.name, "description": t.description or ""} for t in result.tools]
        except Exception as e:
            logger.error(f"[{self.name}] Error listing tools: {e}")
            return []


class JiraMCP:
    """High-level Jira MCP helper."""

    def __init__(self, sse_url: str | None = None):
        url = sse_url or os.getenv("MCP_JIRA_URL", "http://localhost:8128/sse")
        self._client = MCPClient(url, name="jira")

    async def search_issues(self, jql: str, max_results: int = 50) -> str:
        return await self._client.call_tool("search_issues", {"jql": jql, "max_results": max_results})

    async def get_issue(self, issue_key: str) -> str:
        return await self._client.call_tool("get_issue", {"issue_key": issue_key})

    async def get_sprint_issues(self, board_id: int, state: str = "active") -> str:
        return await self._client.call_tool("get_sprint_issues", {"board_id": board_id, "state": state})

    async def get_my_issues(self) -> str:
        return await self._client.call_tool("get_my_issues", {})

    async def add_comment(self, issue_key: str, body: str) -> str:
        return await self._client.call_tool("add_comment", {"issue_key": issue_key, "body": body})

    async def transition_issue(self, issue_key: str, transition: str) -> str:
        return await self._client.call_tool("transition_issue", {"issue_key": issue_key, "transition": transition})


class ConfluenceMCP:
    """High-level Confluence MCP helper."""

    def __init__(self, sse_url: str | None = None):
        url = sse_url or os.getenv("MCP_CONFLUENCE_URL", "http://localhost:8129/sse")
        self._client = MCPClient(url, name="confluence")

    async def search(self, query: str, limit: int = 10) -> str:
        return await self._client.call_tool("search_confluence", {"query": query, "limit": limit})

    async def get_page(self, page_id: str) -> str:
        return await self._client.call_tool("get_confluence_page", {"page_id": page_id})

    async def create_page(self, space_key: str, title: str, body: str, parent_id: str | None = None) -> str:
        args = {"space_key": space_key, "title": title, "body": body}
        if parent_id:
            args["parent_id"] = parent_id
        return await self._client.call_tool("create_confluence_page", args)

    async def update_page(self, page_id: str, title: str, body: str, version: int = None) -> str:
        args = {"page_id": page_id, "title": title, "body": body}
        if version is not None:
            args["version"] = version
        return await self._client.call_tool("update_confluence_page", args)


class BitbucketMCP:
    """High-level Bitbucket MCP helper."""

    def __init__(self, sse_url: str | None = None):
        url = sse_url or os.getenv("MCP_BITBUCKET_URL", "http://localhost:8126/sse")
        self._client = MCPClient(url, name="bitbucket")

    async def list_my_prs(self, role: str = "reviewer", state: str = "OPEN", limit: int = 25) -> str:
        return await self._client.call_tool("list_my_prs", {"role": role, "state": state, "limit": limit})

    async def get_pr_overview(self, pr_url: str) -> str:
        return await self._client.call_tool("get_pr_overview", {"pr_url": pr_url})
'''
    (src_dir / "mcp_clients.py").write_text(content)


# ---------------------------------------------------------------------------
# Sprint manager — core logic
# ---------------------------------------------------------------------------

def _generate_sprint_manager(src_dir: Path, config: TemplateConfig) -> None:
    content = '''"""Sprint Manager — orchestrates Jira queries and generates sprint summaries."""

import json
import logging
import os
from typing import Any

from google import genai

from domain_loader import load_domain_context

logger = logging.getLogger(__name__)

SPRINT_SUMMARY_PROMPT = """You are a Scrum Master assistant for the {domain} domain ({product} product).

Use the following domain context to inform your responses:
{domain_context}

Given the sprint data below, produce a concise sprint summary covering:
1. **Sprint Progress** — tickets completed vs total, story points burned
2. **In Progress** — who is working on what
3. **Blockers** — any blocked tickets and why
4. **At Risk** — tickets that might not finish in the sprint
5. **PRs Needing Review** — open PRs without approvals

Respond in well-structured Markdown.

## Sprint Data
{sprint_data}
"""


class SprintManager:
    """Queries Jira + Bitbucket via MCP and produces AI-powered sprint summaries."""

    def __init__(self):
        self.domain_ctx = load_domain_context()
        self._init_model()

    def _init_model(self):
        project_id = os.getenv("GOOGLE_PROJECT_ID")
        self.model_name = os.getenv("VERTEX_AI_MODEL", "gemini-2.0-flash-001")
        self.client = None
        try:
            if project_id:
                self.client = genai.Client(vertexai=True, project=project_id, location=os.getenv("GOOGLE_LOCATION", "us-central1"))
            elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
                self.client = genai.Client()
        except Exception as e:
            logger.warning(f"Could not initialize model client: {e}")
            self.client = None
        logger.info(f"SprintManager initialised with model: {self.model_name}")

    async def get_sprint_summary(self, jira_client, bitbucket_client, jql_override: str | None = None) -> str:
        """Fetch sprint data from Jira + open PRs from Bitbucket and produce an AI summary."""
        jira_project = self.domain_ctx.get("jira_project", os.getenv("JIRA_PROJECT", ""))

        # Fetch issues
        jql = jql_override or f"project = {jira_project} AND sprint in openSprints() ORDER BY status"
        issues_raw = await jira_client.search_issues(jql)
        issues = self._parse_json(issues_raw)

        # Fetch open PRs
        prs_raw = await bitbucket_client.list_my_prs(role="reviewer", state="OPEN")
        prs = self._parse_json(prs_raw)

        sprint_data = json.dumps({"issues": issues, "open_prs": prs}, indent=2, default=str)

        prompt = SPRINT_SUMMARY_PROMPT.format(
            domain=self.domain_ctx.get("domain", "Unknown"),
            product=self.domain_ctx.get("product", "Unknown"),
            domain_context=json.dumps(self.domain_ctx, indent=2, default=str)[:2000],
            sprint_data=sprint_data[:30000],
        )

        if self.client is None:
            return "Model client not configured. Set GOOGLE_PROJECT_ID (Vertex AI) or GOOGLE_API_KEY (AI Studio)."
        response = self.client.models.generate_content(model=self.model_name, contents=prompt)
        return response.text

    async def get_blockers(self, jira_client) -> str:
        """Fetch blocked / flagged tickets."""
        jira_project = self.domain_ctx.get("jira_project", os.getenv("JIRA_PROJECT", ""))
        jql = f"project = {jira_project} AND (status = Blocked OR flagged = Impediment) ORDER BY priority DESC"
        return await jira_client.search_issues(jql)

    async def get_stale_tickets(self, jira_client, days: int = 5) -> str:
        """Fetch in-progress tickets with no update in N days."""
        jira_project = self.domain_ctx.get("jira_project", os.getenv("JIRA_PROJECT", ""))
        jql = (
            f"project = {jira_project} AND status = \\"In Progress\\" "
            f"AND updated <= -{days}d ORDER BY updated ASC"
        )
        return await jira_client.search_issues(jql)

    @staticmethod
    def _parse_json(raw: str) -> Any:
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            return raw
'''
    (src_dir / "sprint_manager.py").write_text(content)


# ---------------------------------------------------------------------------
# Standup generator
# ---------------------------------------------------------------------------

def _generate_standup_generator(src_dir: Path, config: TemplateConfig) -> None:
    content = '''"""Standup & Sprint Review note generator."""

import json
import logging
import os
from typing import Any

from google import genai

from domain_loader import load_domain_context

logger = logging.getLogger(__name__)

STANDUP_PROMPT = """You are a Scrum Master for the {domain} domain ({product} product).
Generate a concise **Daily Standup Summary** from the following data.

Format:
## Standup — {domain}
### Done (since yesterday)
- bullet points

### In Progress
- bullet points with assignee

### Blockers
- bullet points

### PRs Needing Review
- bullet points

## Data
{data}
"""

SPRINT_REVIEW_PROMPT = """You are a Scrum Master for the {domain} domain ({product} product).
Generate **Sprint Review Notes** from the following sprint data.

Cover:
1. Sprint goal achievement
2. Completed items (with story points)
3. Carried-over items
4. Key metrics (velocity, completion rate)
5. Demo-worthy items
6. Risks & action items for next sprint

## Data
{data}
"""


class StandupGenerator:
    """Generates standup summaries and sprint review notes using LLM."""

    def __init__(self):
        self.domain_ctx = load_domain_context()
        project_id = os.getenv("GOOGLE_PROJECT_ID")
        self.model_name = os.getenv("VERTEX_AI_MODEL", "gemini-2.0-flash-001")
        self.client = None
        try:
            if project_id:
                self.client = genai.Client(vertexai=True, project=project_id, location=os.getenv("GOOGLE_LOCATION", "us-central1"))
            elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
                self.client = genai.Client()
        except Exception as e:
            logger.warning(f"Could not initialize model client: {e}")
            self.client = None

    async def daily_standup(self, jira_client, bitbucket_client) -> str:
        """Generate a daily standup summary."""
        jira_project = self.domain_ctx.get("jira_project", os.getenv("JIRA_PROJECT", ""))

        # Recent activity
        jql = (
            f"project = {jira_project} AND "
            f"(updated >= -1d OR status changed DURING (startOfDay(-1), now())) "
            f"ORDER BY status, assignee"
        )
        issues_raw = await jira_client.search_issues(jql)
        prs_raw = await bitbucket_client.list_my_prs(role="reviewer", state="OPEN")

        data = json.dumps({"recent_issues": self._parse(issues_raw), "open_prs": self._parse(prs_raw)}, indent=2, default=str)

        prompt = STANDUP_PROMPT.format(
            domain=self.domain_ctx.get("domain", "Unknown"),
            product=self.domain_ctx.get("product", "Unknown"),
            data=data[:30000],
        )
        if self.client is None:
            return "Model client not configured. Set GOOGLE_PROJECT_ID (Vertex AI) or GOOGLE_API_KEY (AI Studio)."
        response = self.client.models.generate_content(model=self.model_name, contents=prompt)
        return response.text

    async def sprint_review(self, jira_client) -> str:
        """Generate sprint review notes."""
        jira_project = self.domain_ctx.get("jira_project", os.getenv("JIRA_PROJECT", ""))
        jql = f"project = {jira_project} AND sprint in openSprints() ORDER BY status, priority DESC"
        issues_raw = await jira_client.search_issues(jql)

        data = json.dumps({"sprint_issues": self._parse(issues_raw)}, indent=2, default=str)

        prompt = SPRINT_REVIEW_PROMPT.format(
            domain=self.domain_ctx.get("domain", "Unknown"),
            product=self.domain_ctx.get("product", "Unknown"),
            data=data[:30000],
        )
        if self.client is None:
            return "Model client not configured. Set GOOGLE_PROJECT_ID (Vertex AI) or GOOGLE_API_KEY (AI Studio)."
        response = self.client.models.generate_content(model=self.model_name, contents=prompt)
        return response.text

    @staticmethod
    def _parse(raw):
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except json.JSONDecodeError:
            return raw
'''
    (src_dir / "standup_generator.py").write_text(content)


# ---------------------------------------------------------------------------
# Domain context loader
# ---------------------------------------------------------------------------

def _generate_domain_loader(src_dir: Path) -> None:
    content = '''"""Load domain context from .domain-context.json and persona skills."""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_domain_context() -> dict:
    """Load .domain-context.json from the project root."""
    ctx_file = PROJECT_ROOT / ".domain-context.json"
    if ctx_file.exists():
        try:
            data = json.loads(ctx_file.read_text())
            logger.info(f"Loaded domain context: {data.get('domain', 'unknown')}")
            return data
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to load domain context: {e}")
    else:
        logger.info("No .domain-context.json found — running without domain context")
    return {}


def load_persona_skill(role: str) -> str:
    """Load a persona skill Markdown file (e.g. SM.md, DOMAIN.md).

    Looks in .skills/domain/<ROLE>.md relative to project root.
    """
    skill_file = PROJECT_ROOT / ".skills" / "domain" / f"{role.upper()}.md"
    if skill_file.exists():
        return skill_file.read_text()
    return ""
'''
    (src_dir / "domain_loader.py").write_text(content)
