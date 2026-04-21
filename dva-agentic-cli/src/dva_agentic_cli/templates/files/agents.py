"""Generate agent files."""

from pathlib import Path
from dva_agentic_cli.templates.config import TemplateConfig
from dva_agentic_cli.templates.enums import Framework, UseCase


def generate_agent_files(agents_dir: Path, config: TemplateConfig) -> None:
    _generate_base_agent(agents_dir)
    _generate_use_case_agent(agents_dir, config)


def _get_agent_info(use_case: UseCase) -> tuple:
    mapping = {
        UseCase.BASIC: ("basic_agent.py", "BasicAgent"),
        UseCase.RAG: ("rag_agent.py", "RAGAgent"),
        UseCase.KNOWLEDGE_GRAPH: ("kg_agent.py", "KnowledgeGraphAgent"),
        UseCase.MULTI_AGENT: ("orchestrator.py", "OrchestratorAgent"),
        UseCase.CHATBOT: ("chatbot.py", "ChatbotAgent"),
        UseCase.DATA_PIPELINE: ("pipeline_agent.py", "PipelineAgent"),
        UseCase.CODE_ASSISTANT: ("code_agent.py", "CodeAssistantAgent"),
        UseCase.PR_REVIEWER: ("pr_reviewer_agent.py", "PRReviewerAgent"),
    }
    return mapping.get(use_case, ("basic_agent.py", "BasicAgent"))


def _generate_base_agent(agents_dir: Path) -> None:
    content = '''"Base agent class."
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class AgentMessage:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseAgent(ABC):
    def __init__(self, settings: Any = None):
        self.settings = settings
        self.history: List[AgentMessage] = []
        self._initialized = False
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        pass
    
    def add_to_history(self, role: str, content: str, **metadata) -> None:
        self.history.append(AgentMessage(role=role, content=content, metadata=metadata))
    
    def get_history(self, limit: Optional[int] = None) -> List[AgentMessage]:
        return self.history[-limit:] if limit else self.history
    
    async def run_interactive(self) -> None:
        from rich.console import Console
        from rich.prompt import Prompt
        console = Console()
        if not self._initialized:
            await self.initialize()
            self._initialized = True
        console.print("[green]Agent ready! Type quit to exit.[/green]")
        while True:
            try:
                user_input = Prompt.ask("[blue]You[/blue]")
                if user_input.lower() in ["quit", "exit", "q"]:
                    break
                if not user_input.strip():
                    continue
                self.add_to_history("user", user_input)
                response = await self.process({"message": user_input})
                assistant_response = response.get("response", "No response.")
                self.add_to_history("assistant", assistant_response)
                console.print(f"[green]Assistant:[/green] {assistant_response}")
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
'''
    (agents_dir / "base.py").write_text(content)


def _generate_use_case_agent(agents_dir: Path, config: TemplateConfig) -> None:
    if config.use_case == UseCase.PR_REVIEWER:
        _generate_pr_reviewer_agent(agents_dir, config)
        return
    agent_file, agent_class = _get_agent_info(config.use_case)
    content = f'"""Agent for {config.use_case.display_name}."""\n'
    content += f'''from typing import Any, Dict
import google.generativeai as genai
from agents.base import BaseAgent

class {agent_class}(BaseAgent):
    def __init__(self, settings: Any = None):
        super().__init__(settings)
        self.model = None
    
    async def initialize(self) -> None:
        if self.settings and self.settings.google_project_id:
            genai.configure(project=self.settings.google_project_id, location=self.settings.google_location)
        model_name = self.settings.vertex_ai_model if self.settings else "gemini-2.0-flash-001"
        self.model = genai.GenerativeModel(model_name)
        self._initialized = True
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            await self.initialize()
        message = input_data.get("message", "")
        history = "\\n".join(f"{{m.role}}: {{m.content}}" for m in self.get_history(10))
        prompt = f"You are a helpful {config.use_case.display_name}.\\n\\nHistory:\\n{{history}}\\n\\nUser: {{message}}\\n\\nAssistant:"
        try:
            response = self.model.generate_content(prompt)
            return {{"response": response.text, "status": "success"}}
        except Exception as e:
            return {{"response": f"Error: {{str(e)}}", "status": "error"}}
'''
    (agents_dir / agent_file).write_text(content)


def _generate_pr_reviewer_agent(agents_dir: Path, config: TemplateConfig) -> None:
    content = '''"""PR Reviewer Agent - orchestrates the PR watch-review-approve pipeline."""

import asyncio
import logging
from typing import Any, Dict

from agents.base import BaseAgent

logger = logging.getLogger(__name__)


class PRReviewerAgent(BaseAgent):
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
        logger.info("PRReviewerAgent initialized")

    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a command (for interactive mode)."""
        if not self._initialized:
            await self.initialize()

        message = input_data.get("message", "").strip().lower()

        if message in ("start", "watch", "run"):
            await self.watcher._poll_cycle()
            return {"response": "Poll cycle completed.", "status": "success"}

        elif message == "status":
            count = self.watcher.state.get_seen_count()
            return {
                "response": f"Seen {count} PR(s). Mode: {self.settings.review_mode}. "
                            f"Polling: {self.settings.poll_interval}s",
                "status": "success",
            }

        elif message == "reset":
            self.watcher.state.reset()
            return {"response": "PR state reset. All PRs will be re-processed.", "status": "success"}

        else:
            return {
                "response": "Commands: start (run poll), status, reset, quit",
                "status": "success",
            }

    async def run_daemon(self) -> None:
        """Run the watcher as a continuous background daemon."""
        if not self._initialized:
            await self.initialize()
        await self.watcher.start()
'''
    (agents_dir / "pr_reviewer_agent.py").write_text(content)
