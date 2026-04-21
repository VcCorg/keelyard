"""Generate PR Reviewer agent template files."""

from pathlib import Path
from dva_agentic_cli.templates.config import TemplateConfig


def generate_pr_reviewer_files(target_dir: Path, config: TemplateConfig) -> None:
    """Generate PR Reviewer specific files: MCP client, watcher, reviewer."""
    src_dir = target_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    _generate_mcp_client(src_dir, config)
    _generate_watcher(src_dir, config)
    _generate_reviewer(src_dir, config)
    _generate_pr_state(src_dir)


def _generate_mcp_client(src_dir: Path, config: TemplateConfig) -> None:
    """Generate the MCP SSE client wrapper."""
    content = f'''"""MCP Client wrapper for connecting to Bitbucket and Jira MCP servers via SSE."""

import asyncio
import json
import logging
from typing import Any, Optional

from mcp.client.sse import sse_client
from mcp import ClientSession

logger = logging.getLogger(__name__)


class MCPClient:
    """Connects to an MCP server over SSE and calls tools."""

    def __init__(self, sse_url: str, name: str = "mcp"):
        self.sse_url = sse_url
        self.name = name

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] = None) -> str:
        """Connect to the MCP server, call a tool, and return the text result."""
        arguments = arguments or {{}}
        try:
            async with sse_client(self.sse_url) as streams:
                read_stream, write_stream = streams
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, arguments)
                    if result.content:
                        texts = []
                        for item in result.content:
                            if hasattr(item, "text"):
                                texts.append(item.text)
                        return "\\n".join(texts) if texts else str(result.content)
                    return ""
        except Exception as e:
            logger.error(f"[{{self.name}}] Error calling {{tool_name}}: {{e}}")
            raise

    async def list_tools(self) -> list[dict]:
        """List all available tools on the MCP server."""
        try:
            async with sse_client(self.sse_url) as streams:
                read_stream, write_stream = streams
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return [
                        {{"name": t.name, "description": t.description or ""}}
                        for t in result.tools
                    ]
        except Exception as e:
            logger.error(f"[{{self.name}}] Error listing tools: {{e}}")
            return []


class BitbucketMCP:
    """High-level Bitbucket MCP client with typed helper methods."""

    def __init__(self, sse_url: str = "{config.bitbucket_mcp_url}"):
        self._client = MCPClient(sse_url, name="bitbucket")

    async def list_my_prs(self, role: str = "reviewer", state: str = "OPEN", limit: int = 25) -> str:
        return await self._client.call_tool("list_my_prs", {{
            "role": role, "state": state, "limit": limit,
        }})

    async def get_pr_overview(self, pr_url: str) -> str:
        return await self._client.call_tool("get_pr_overview", {{"pr_url": pr_url}})

    async def get_pr_diff(self, pr_url: str, context_lines: int = 10) -> str:
        return await self._client.call_tool("get_pr_diff", {{
            "pr_url": pr_url, "context_lines": context_lines,
        }})

    async def get_pr_files(self, pr_url: str) -> str:
        return await self._client.call_tool("get_pr_files", {{"pr_url": pr_url}})

    async def review_pr(self, pr_url: str) -> str:
        return await self._client.call_tool("review_pr", {{"pr_url": pr_url}})

    async def add_pr_comment(self, pr_url: str, text: str, severity: str = "NORMAL") -> str:
        return await self._client.call_tool("add_pr_comment", {{
            "pr_url": pr_url, "text": text, "severity": severity,
        }})

    async def approve_pr(self, pr_url: str) -> str:
        return await self._client.call_tool("approve_pr", {{"pr_url": pr_url}})

    async def unapprove_pr(self, pr_url: str) -> str:
        return await self._client.call_tool("unapprove_pr", {{"pr_url": pr_url}})

    async def needs_work_pr(self, pr_url: str) -> str:
        return await self._client.call_tool("needs_work_pr", {{"pr_url": pr_url}})

    async def decline_pr(self, pr_url: str) -> str:
        return await self._client.call_tool("decline_pr", {{"pr_url": pr_url}})

    async def merge_pr(self, pr_url: str) -> str:
        return await self._client.call_tool("merge_pr", {{"pr_url": pr_url}})
'''
    (src_dir / "mcp_client.py").write_text(content)


def _generate_watcher(src_dir: Path, config: TemplateConfig) -> None:
    """Generate the PR polling watcher."""
    jira_import = ""
    jira_init = ""
    jira_enrich_call = ""
    jira_enrich_method = ""
    if config.include_jira_mcp:
        jira_import = """
from mcp_client import MCPClient

"""
        jira_init = f"""
        self.jira = MCPClient("{config.jira_mcp_url}", name="jira") if settings.jira_mcp_url else None
"""
        jira_enrich_call = """
            context = await self._enrich_with_jira(context)
"""
        # NOTE: This string is substituted literally into an f-string via {jira_enrich_method}.
        # The f-string only resolves the {jira_enrich_method} placeholder; contents are NOT re-parsed.
        # So use literal braces here — they appear as-is in the generated file.
        jira_enrich_method = '\n    async def _enrich_with_jira(self, pr_data: dict) -> dict:\n        """Optionally enrich PR context with linked Jira ticket info."""\n        if not self.jira:\n            return pr_data\n        import re\n        match = re.search(r\'[A-Z]+-\\d+\', pr_data.get("overview", "") + " " + pr_data.get("pr_url", ""))\n        if match:\n            jira_key = match.group()\n            try:\n                issue_data = await self.jira.call_tool("get_issue", {"issue_key": jira_key})\n                pr_data["jira_context"] = issue_data\n            except Exception as e:\n                logger.warning(f"Could not fetch Jira issue {jira_key}: {e}")\n        return pr_data\n'

    content = f'''"""PR Watcher - polls Bitbucket for new PRs and triggers review workflows."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Optional

from config import Settings
from mcp_client import BitbucketMCP
from pr_state import PRStateStore
from reviewer import PRReviewer
{jira_import}
logger = logging.getLogger(__name__)


class PRWatcher:
    """Polls Bitbucket MCP for new PRs assigned to the authenticated user and triggers reviews."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.bitbucket = BitbucketMCP(settings.bitbucket_mcp_url)
        self.state = PRStateStore(settings.state_file)
        self.reviewer = PRReviewer(settings)
        self.poll_interval = settings.poll_interval
        self._running = False
{jira_init}
    async def start(self) -> None:
        """Start the polling loop."""
        self._running = True
        logger.info(f"PR Watcher started (polling every {{self.poll_interval}}s)")
        logger.info(f"Bitbucket MCP: {{self.settings.bitbucket_mcp_url}}")
        logger.info(f"Mode: {{self.settings.review_mode}}")

        while self._running:
            try:
                await self._poll_cycle()
            except Exception as e:
                logger.error(f"Poll cycle error: {{e}}", exc_info=True)

            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False
        logger.info("PR Watcher stopping...")

    async def _poll_cycle(self) -> None:
        """Single poll: fetch PRs, detect new ones, process them."""
        raw = await self.bitbucket.list_my_prs(role="reviewer", state="OPEN")
        prs = json.loads(raw) if isinstance(raw, str) else raw

        if not isinstance(prs, list):
            prs = prs.get("values", prs.get("prs", []))

        new_prs = []
        for pr in prs:
            pr_id = str(pr.get("id", pr.get("pr_id", "")))
            pr_url = pr.get("url", pr.get("pr_url", ""))
            if pr_id and not self.state.is_seen(pr_id):
                new_prs.append({{"id": pr_id, "url": pr_url, "title": pr.get("title", ""), "author": pr.get("author", "")}})

        if new_prs:
            logger.info(f"Found {{len(new_prs)}} new PR(s) to review")

        for pr in new_prs:
            await self._process_pr(pr)
            self.state.mark_seen(pr["id"], pr.get("url", ""))

    async def _process_pr(self, pr: dict) -> None:
        """Process a single new PR through the review pipeline."""
        pr_url = pr.get("url", "")
        logger.info(f"Processing PR #{{pr['id']}}: {{pr.get('title', '')}} ({{pr_url}})")

        if not pr_url:
            logger.warning(f"PR #{{pr['id']}} has no URL, skipping")
            return

        try:
            # Fetch full PR context
            overview_raw = await self.bitbucket.get_pr_overview(pr_url)
            diff_raw = await self.bitbucket.get_pr_diff(pr_url, context_lines=5)
            files_raw = await self.bitbucket.get_pr_files(pr_url)

            context = {{
                "pr_url": pr_url,
                "overview": overview_raw,
                "diff": diff_raw,
                "files": files_raw,
            }}
{jira_enrich_call}
            # Run AI review
            review_result = await self.reviewer.review(context)

            # Execute actions based on review mode
            await self._execute_actions(pr_url, review_result)

        except Exception as e:
            logger.error(f"Error processing PR #{{pr['id']}}: {{e}}", exc_info=True)

    async def _execute_actions(self, pr_url: str, review: dict) -> None:
        """Execute actions based on review result and configured mode."""
        mode = self.settings.review_mode
        action = review.get("action", "comment")
        comment = review.get("comment", "")
        summary = review.get("summary", "")

        if mode == "notify":
            logger.info(f"[notify] PR review: action={{action}}, summary={{summary[:100]}}")
            return

        if mode in ("review", "auto-approve"):
            if comment:
                logger.info(f"Posting review comment to {{pr_url}}")
                await self.bitbucket.add_pr_comment(pr_url, comment)

        if mode == "auto-approve" and action == "approve":
            logger.info(f"Auto-approving {{pr_url}}")
            await self.bitbucket.approve_pr(pr_url)
        elif mode == "auto-approve" and action == "needs_work":
            logger.info(f"Marking needs-work on {{pr_url}}")
            await self.bitbucket.needs_work_pr(pr_url)
{jira_enrich_method}'''
    (src_dir / "watcher.py").write_text(content)


def _generate_reviewer(src_dir: Path, config: TemplateConfig) -> None:
    """Generate the AI-powered PR reviewer."""
    content = '''"""AI-powered PR Reviewer using Vertex AI / Gemini."""

import json
import logging
from typing import Any

import google.generativeai as genai

from config import Settings

logger = logging.getLogger(__name__)

REVIEW_SYSTEM_PROMPT = """You are an expert code reviewer. You will receive a pull request with:
- An overview (title, description, author, reviewers)
- The list of changed files
- The unified diff

Your task is to review the code changes and produce a structured review.

Respond ONLY with valid JSON in this format:
{
    "action": "approve" | "needs_work" | "comment",
    "summary": "Brief summary of your review (1-2 sentences)",
    "comment": "Detailed review comment to post on the PR (Markdown formatted)",
    "issues": [
        {"severity": "critical|major|minor|suggestion", "file": "path", "description": "issue description"}
    ]
}

Guidelines:
- "approve" if changes look good with no critical/major issues
- "needs_work" if there are critical or major issues
- "comment" if there are only minor suggestions
- Be constructive and specific in your feedback
- Reference file names and line numbers when possible
"""


class PRReviewer:
    """Performs AI-powered code review on PR diffs."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = None
        self._init_model()

    def _init_model(self) -> None:
        """Initialize the Gemini model."""
        if self.settings.google_project_id:
            genai.configure(
                project=self.settings.google_project_id,
                location=self.settings.google_location,
            )
        self.model = genai.GenerativeModel(
            self.settings.vertex_ai_model,
            system_instruction=REVIEW_SYSTEM_PROMPT,
        )
        logger.info(f"Reviewer initialized with model: {self.settings.vertex_ai_model}")

    async def review(self, context: dict[str, Any]) -> dict[str, Any]:
        """Review a PR and return structured feedback.

        Args:
            context: Dict with keys: pr_url, overview, diff, files, (optional) jira_context

        Returns:
            Dict with keys: action, summary, comment, issues
        """
        prompt = self._build_prompt(context)

        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\\n", 1)[1] if "\\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            if text.startswith("json"):
                text = text[4:]

            result = json.loads(text.strip())
            logger.info(f"Review result: action={result.get('action')}, issues={len(result.get('issues', []))}")
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return {
                "action": "comment",
                "summary": "AI review completed but output was not structured.",
                "comment": response.text if 'response' in dir() else "Review failed.",
                "issues": [],
            }
        except Exception as e:
            logger.error(f"Review failed: {e}", exc_info=True)
            return {
                "action": "comment",
                "summary": f"Review error: {str(e)}",
                "comment": "",
                "issues": [],
            }

    def _build_prompt(self, context: dict[str, Any]) -> str:
        """Build the review prompt from PR context."""
        parts = [
            "## PR Overview",
            str(context.get("overview", "No overview available")),
            "",
            "## Changed Files",
            str(context.get("files", "No file list available")),
            "",
            "## Diff",
            str(context.get("diff", "No diff available"))[:50000],  # Truncate very large diffs
        ]

        if context.get("jira_context"):
            parts.extend([
                "",
                "## Linked Jira Ticket",
                str(context["jira_context"]),
            ])

        return "\\n".join(parts)
'''
    (src_dir / "reviewer.py").write_text(content)


def _generate_pr_state(src_dir: Path) -> None:
    """Generate the PR state tracker (seen/processed PRs)."""
    content = '''"""Persistent state store for tracking which PRs have been processed."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PRStateStore:
    """Tracks which PRs have been seen/processed to avoid re-processing."""

    def __init__(self, state_file: str = "./data/pr_state.json"):
        self.state_file = Path(state_file)
        self._state: dict = self._load()

    def _load(self) -> dict:
        """Load state from disk."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text())
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}")
        return {"seen_prs": {}}

    def _save(self) -> None:
        """Persist state to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(self._state, indent=2))

    def is_seen(self, pr_id: str) -> bool:
        """Check if a PR has already been processed."""
        return pr_id in self._state.get("seen_prs", {})

    def mark_seen(self, pr_id: str, pr_url: str = "") -> None:
        """Mark a PR as seen/processed."""
        self._state.setdefault("seen_prs", {})[pr_id] = {
            "url": pr_url,
            "seen_at": datetime.now().isoformat(),
        }
        self._save()
        logger.debug(f"Marked PR #{pr_id} as seen")

    def get_seen_count(self) -> int:
        """Return how many PRs have been processed."""
        return len(self._state.get("seen_prs", {}))

    def reset(self) -> None:
        """Clear all state (re-process everything on next poll)."""
        self._state = {"seen_prs": {}}
        self._save()
        logger.info("PR state reset")
'''
    (src_dir / "pr_state.py").write_text(content)
