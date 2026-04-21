"""Generate pyproject.toml content."""

from dva_agentic_cli.templates.config import TemplateConfig


def get_pyproject_content(config: TemplateConfig) -> str:
    """Generate pyproject.toml content based on configuration."""
    deps = config.dependencies
    deps_str = ",\n    ".join(f'"{d}"' for d in deps)
    
    return f'''[project]
name = "{config.name}"
version = "0.1.0"
description = "Agentic project using {config.framework.display_name}"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    {deps_str},
    "python-dotenv>=1.0.0",
    "pydantic-settings>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.1.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.3.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
'''
