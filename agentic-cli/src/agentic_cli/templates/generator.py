"""Template generator for creating project files."""

from pathlib import Path
from typing import Any

from agentic_cli.templates.enums import Framework, UseCase, Tool
from agentic_cli.templates.config import TemplateConfig


class TemplateGenerator:
    """Generates project files from templates based on configuration."""
    
    def __init__(self, config: TemplateConfig):
        self.config = config
    
    def generate(self, target_dir: Path) -> None:
        """Generate the complete project structure."""
        target_dir.mkdir(parents=True, exist_ok=True)
        
        self._create_directories(target_dir)
        self._generate_pyproject(target_dir)
        self._generate_readme(target_dir)
        self._generate_env_example(target_dir)
        self._generate_makefile(target_dir)
        self._generate_gitignore(target_dir)
        self._generate_main(target_dir)
        self._generate_config(target_dir)
        self._generate_agents(target_dir)
        self._generate_tools(target_dir)
        
        if self.config.include_tests:
            self._generate_tests(target_dir)
        
        if self.config.include_examples:
            self._generate_examples(target_dir)
        
        if self.config.include_docker:
            self._generate_docker(target_dir)
        
        if self.config.include_a2a:
            self._generate_a2a(target_dir)
        
        if self.config.include_kg_mcp:
            self._generate_kg_mcp(target_dir)
        
        if self.config.kg_workspace:
            self._generate_kg_workspace(target_dir)
        
        if self.config.use_case == UseCase.PR_REVIEWER:
            self._generate_pr_reviewer(target_dir)
            self._generate_opencode_agent(target_dir)
            self._generate_skill(target_dir)
        
        if self.config.use_case == UseCase.ONBOARD:
            self._generate_onboard(target_dir)
        
        if self.config.use_case == UseCase.SCRUM_MASTER:
            self._generate_scrum_master(target_dir)
    
    def _create_directories(self, target_dir: Path) -> None:
        """Create the project directory structure."""
        dirs = ["src", "src/agents", "src/tools", "src/workflows"]
        
        if self.config.include_tests:
            dirs.append("tests")
        if self.config.include_examples:
            dirs.append("examples")
        
        for d in dirs:
            (target_dir / d).mkdir(parents=True, exist_ok=True)
            if d.startswith("src"):
                (target_dir / d / "__init__.py").write_text('"""Package initialization."""\n')
    
    def _generate_pyproject(self, target_dir: Path) -> None:
        """Generate pyproject.toml."""
        from agentic_cli.templates.files.pyproject import get_pyproject_content
        content = get_pyproject_content(self.config)
        (target_dir / "pyproject.toml").write_text(content)
    
    def _generate_readme(self, target_dir: Path) -> None:
        """Generate README.md."""
        from agentic_cli.templates.files.readme import get_readme_content
        content = get_readme_content(self.config)
        (target_dir / "README.md").write_text(content)
    
    def _generate_env_example(self, target_dir: Path) -> None:
        """Generate .env.example file."""
        from agentic_cli.templates.files.env import get_env_content
        content = get_env_content(self.config)
        (target_dir / ".env.example").write_text(content)
    
    def _generate_makefile(self, target_dir: Path) -> None:
        """Generate Makefile."""
        from agentic_cli.templates.files.makefile import get_makefile_content
        content = get_makefile_content()
        (target_dir / "Makefile").write_text(content)
    
    def _generate_gitignore(self, target_dir: Path) -> None:
        """Generate .gitignore."""
        from agentic_cli.templates.files.gitignore import get_gitignore_content
        content = get_gitignore_content()
        (target_dir / ".gitignore").write_text(content)
    
    def _generate_main(self, target_dir: Path) -> None:
        """Generate main.py entry point."""
        from agentic_cli.templates.files.main import get_main_content
        content = get_main_content(self.config)
        (target_dir / "src" / "main.py").write_text(content)
    
    def _generate_config(self, target_dir: Path) -> None:
        """Generate config.py."""
        from agentic_cli.templates.files.config import get_config_content
        content = get_config_content(self.config)
        (target_dir / "src" / "config.py").write_text(content)
    
    def _generate_agents(self, target_dir: Path) -> None:
        """Generate agent files based on framework and use case."""
        from agentic_cli.templates.files.agents import generate_agent_files
        generate_agent_files(target_dir / "src" / "agents", self.config)
    
    def _generate_tools(self, target_dir: Path) -> None:
        """Generate tool files based on selected tools."""
        from agentic_cli.templates.files.tools import generate_tool_files
        generate_tool_files(target_dir / "src" / "tools", self.config)
    
    def _generate_tests(self, target_dir: Path) -> None:
        """Generate test files."""
        from agentic_cli.templates.files.tests import generate_test_files
        generate_test_files(target_dir / "tests", self.config)
    
    def _generate_examples(self, target_dir: Path) -> None:
        """Generate example files."""
        from agentic_cli.templates.files.examples import generate_example_files
        generate_example_files(target_dir / "examples", self.config)
    
    def _generate_docker(self, target_dir: Path) -> None:
        """Generate Docker files."""
        from agentic_cli.templates.files.docker import generate_docker_files
        generate_docker_files(target_dir, self.config)
    
    def _generate_a2a(self, target_dir: Path) -> None:
        """Generate A2A protocol files for multi-agent projects."""
        from agentic_cli.templates.files.a2a import generate_a2a_files
        generate_a2a_files(target_dir, self.config)
    
    def _generate_kg_mcp(self, target_dir: Path) -> None:
        """Generate KG MCP server files."""
        from agentic_cli.templates.files.kg_mcp import generate_kg_mcp_files
        generate_kg_mcp_files(target_dir, self.config)
    
    def _generate_kg_workspace(self, target_dir: Path) -> None:
        """Generate KG workspace integration files."""
        from agentic_cli.templates.files.kg_mcp import generate_kg_workspace_files
        generate_kg_workspace_files(target_dir, self.config)
    
    def _generate_pr_reviewer(self, target_dir: Path) -> None:
        """Generate PR Reviewer agent files (MCP client, watcher, reviewer, state)."""
        from agentic_cli.templates.files.pr_reviewer import generate_pr_reviewer_files
        generate_pr_reviewer_files(target_dir, self.config)
    
    def _generate_opencode_agent(self, target_dir: Path) -> None:
        """Generate OpenCode agent definition file for IDE integration."""
        from agentic_cli.templates.files.opencode_agent import generate_opencode_agent
        generate_opencode_agent(target_dir, self.config, include_jira=self.config.include_jira_mcp)
    
    def _generate_skill(self, target_dir: Path) -> None:
        """Generate Agent Skills (agentskills.io) format SKILL.md for cross-platform agent discovery."""
        from agentic_cli.templates.files.skill import generate_skill
        generate_skill(target_dir, self.config, include_jira=self.config.include_jira_mcp)
    
    def _generate_onboard(self, target_dir: Path) -> None:
        """Generate onboard agent files (main, config, prompts, eval)."""
        from agentic_cli.templates.files.onboard import generate_onboard_files
        generate_onboard_files(target_dir, self.config)
    
    def _generate_scrum_master(self, target_dir: Path) -> None:
        """Generate Scrum Master agent files (MCP clients, sprint manager, standup generator)."""
        from agentic_cli.templates.files.scrum_master import generate_scrum_master_files
        generate_scrum_master_files(target_dir, self.config)
